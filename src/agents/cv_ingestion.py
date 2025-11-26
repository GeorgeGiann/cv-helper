"""
CV Ingestion Agent
Extracts and structures CV data from PDF files
"""

from typing import Dict, Any, Optional
import logging
import json

from .base_agent import BaseAgent
from ..tools.pdf_parser.main import PDFParserTool
from ..tools.pdf_parser.extractor import CVSectionExtractor

logger = logging.getLogger(__name__)


class CVIngestionAgent(BaseAgent):
    """
    ADK Agent for CV ingestion and parsing

    Responsibilities:
    - Parse PDF CVs
    - Extract structured information (contact, education, experience, skills)
    - Convert to canonical JSON Resume schema
    - Validate data completeness
    """

    def __init__(self, llm_provider=None, storage_backend=None, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="cv_ingestion",
            description="Extracts structured data from PDF CVs and converts to JSON Resume format",
            llm_provider=llm_provider,
            storage_backend=storage_backend,
            config=config
        )

        # Initialize PDF parser tool
        self.pdf_parser = PDFParserTool(storage_backend=storage_backend)
        self.section_extractor = CVSectionExtractor()

    async def parse_cv(self, file_path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse a CV file (PDF or text) and extract structured data

        Args:
            file_path: Path to CV file - PDF (.pdf) or text (.txt) (local or remote URI)
            user_id: Optional user identifier

        Returns:
            Dictionary with parsed CV data in JSON Resume format
        """
        try:
            logger.info(f"[{self.name}] Parsing CV: {file_path}")

            # Step 1: Extract text and sections from file
            # Handle both PDF and plain text files
            if file_path.endswith('.txt'):
                # Read plain text file directly
                from pathlib import Path
                raw_text = Path(file_path).read_text(encoding='utf-8')
                raw_data = {
                    "text": raw_text,
                    "sections": self.section_extractor.extract_sections(raw_text),
                    "metadata": {
                        "num_pages": 1,
                        "extraction_method": "plain_text"
                    }
                }
                logger.info(f"[{self.name}] Read {len(raw_text)} characters from text file")
            else:
                # Use PDF parser for PDF files
                parse_result = self.pdf_parser.execute(
                    file_path=file_path,
                    ocr_enabled=self.config.get("ocr_enabled", False)
                )

                if not parse_result["success"]:
                    raise Exception(f"PDF parsing failed: {parse_result['error']}")

                raw_data = parse_result["parsed_data"]
                logger.info(f"[{self.name}] Extracted {len(raw_data['text'])} characters from PDF")

            # Step 2: Use LLM to convert to JSON Resume format
            json_resume = await self._convert_to_json_resume(
                raw_text=raw_data["text"],
                sections=raw_data["sections"]
            )

            # Step 3: Validate completeness
            validation = self._validate_cv_data(json_resume)

            result = {
                "cv_data": json_resume,
                "validation": validation,
                "metadata": {
                    "user_id": user_id,
                    "source_file": file_path,
                    "num_pages": raw_data["metadata"].get("num_pages"),
                    "extraction_method": raw_data["metadata"].get("extraction_method")
                }
            }

            logger.info(f"[{self.name}] Successfully parsed CV with {len(json_resume.get('work', []))} work experiences")

            return result

        except Exception as e:
            logger.error(f"[{self.name}] CV parsing failed: {e}", exc_info=True)
            raise

    async def _convert_to_json_resume(
        self,
        raw_text: str,
        sections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use LLM to convert extracted CV data to JSON Resume format

        Args:
            raw_text: Raw CV text
            sections: Extracted sections

        Returns:
            JSON Resume formatted dictionary
        """
        if not self.llm_provider:
            logger.warning("No LLM provider configured, using extracted sections as-is")
            return self._basic_conversion(sections)

        # Prepare prompt for LLM with strict format specification
        prompt = f"""Convert the following CV information into JSON Resume format with STRICT field name requirements.

CV Text Excerpt:
{raw_text[:2000]}

Extracted Sections:
Contact: {json.dumps(sections.get('contact', {}), indent=2)}
Experience: {len(sections.get('experience', []))} entries
Education: {len(sections.get('education', []))} entries
Skills: {len(sections.get('skills', []))} items
Projects: {len(sections.get('projects', []))} items
Certifications: {len(sections.get('certifications', []))} items

REQUIRED JSON STRUCTURE with EXACT field names:
{{
  "basics": {{
    "name": "...",
    "email": "...",
    "phone": "...",
    "location": {{"address": "full address as single string"}},
    "profiles": [{{"network": "LinkedIn", "url": "https://..."}}]
  }},
  "work": [{{
    "company": "...",
    "position": "...",
    "startDate": "YYYY-MM",
    "endDate": "YYYY-MM" or null,
    "highlights": ["achievement 1", "achievement 2"]
  }}],
  "education": [{{
    "institution": "...",
    "area": "field of study",
    "studyType": "degree type",
    "startDate": "YYYY-MM",
    "endDate": "YYYY-MM"
  }}],
  "skills": [{{
    "name": "category name",
    "keywords": ["skill1", "skill2"]
  }}],
  "projects": [{{
    "name": "project name",
    "description": ["description text", "highlight 1", "highlight 2"]
  }}],
  "certificates": [{{
    "name": "certificate name",
    "details": ["Issuer: ...", "Date: ..."]
  }}]
}}

CRITICAL RULES:
- Skills: Use "name" and "keywords" (NOT "category", "items", "level")
- Projects: Use "name" and "description" array (NOT "highlights", "summary")
- Certificates: Use "name" and "details" array (NOT "issuer", "date" as separate fields)
- Location: Use "address" as single string (NOT "city", "country" separately)

Return ONLY valid JSON matching the exact structure above, no additional text."""

        try:
            response = await self.llm_provider.complete_json(
                prompt=prompt,
                temperature=0.2,  # Lower temperature for structured output
                max_tokens=2048
            )

            logger.info(f"[{self.name}] LLM successfully converted CV to JSON Resume format")
            return response

        except Exception as e:
            logger.error(f"[{self.name}] LLM conversion failed, falling back to basic conversion: {e}", exc_info=True)
            return self._basic_conversion(sections)

    def _basic_conversion(self, sections: Dict[str, Any]) -> Dict[str, Any]:
        """
        Basic conversion from extracted sections to JSON Resume format
        (Fallback when LLM is not available)
        """
        contact = sections.get("contact", {})

        # Ensure contact is a dict, not a string
        if not isinstance(contact, dict):
            logger.warning(f"[{self.name}] Contact is not a dict (type: {type(contact)}), creating empty dict")
            contact = {}

        # Build profiles list, excluding None values
        profiles = []
        if contact.get("linkedin"):
            profiles.append({"network": "LinkedIn", "url": contact.get("linkedin")})
        if contact.get("github"):
            profiles.append({"network": "GitHub", "url": contact.get("github")})

        # Convert skills format from extractor to JSON Resume format
        skills_data = sections.get("skills", [])
        logger.info(f"[{self.name}] Raw skills_data from extractor: {skills_data}")
        json_skills = []
        for skill in skills_data:
            logger.info(f"[{self.name}] Processing skill: {skill} (type: {type(skill)})")
            if isinstance(skill, dict):
                # Extractor returns {"category": "...", "items": [...]}
                # JSON Resume expects {"name": "...", "keywords": [...]}
                category = skill.get("category", "General")
                items = skill.get("items", [])
                logger.info(f"[{self.name}] Dict skill - category: {category}, items: {items}")
                json_skills.append({
                    "name": category,
                    "keywords": items
                })
            elif isinstance(skill, str):
                # Handle string skills
                logger.info(f"[{self.name}] String skill: {skill}")
                json_skills.append({
                    "name": "General",
                    "keywords": [skill]
                })
            else:
                logger.warning(f"[{self.name}] Unknown skill type: {type(skill)} - {skill}")

        # Convert projects format from extractor to profile JSON format
        projects_data = sections.get("projects", [])
        logger.info(f"[{self.name}] Raw projects_data from extractor: {projects_data}")
        json_projects = []
        for project in projects_data:
            logger.info(f"[{self.name}] Processing project: {project} (type: {type(project)})")
            if isinstance(project, dict):
                # Extractor returns {"name": "...", "description": "...", "highlights": [...], ...}
                # Profile format expects {"name": "...", "description": [...]}
                name = project.get("name", "")
                description_text = project.get("description", "")
                highlights = project.get("highlights", [])

                # Combine description and highlights into description array
                description_list = []
                if description_text:
                    description_list.append(description_text)
                description_list.extend(highlights)

                logger.info(f"[{self.name}] Dict project - name: {name}, description items: {len(description_list)}")
                json_projects.append({
                    "name": name,
                    "description": description_list
                })
            elif isinstance(project, str):
                logger.info(f"[{self.name}] String project: {project}")
                json_projects.append({
                    "name": project,
                    "description": []
                })
            else:
                logger.warning(f"[{self.name}] Unknown project type: {type(project)} - {project}")

        # Convert certificates format from extractor to profile JSON format
        certs_data = sections.get("certifications", [])
        logger.info(f"[{self.name}] Raw certificates_data from extractor: {certs_data}")
        json_certificates = []
        for cert in certs_data:
            logger.info(f"[{self.name}] Processing certificate: {cert} (type: {type(cert)})")
            if isinstance(cert, dict):
                # Extractor returns {"name": "...", "issuer": "...", "date": "...", ...}
                # Profile format expects {"name": "...", "details": [...]}
                name = cert.get("name", "")
                issuer = cert.get("issuer")
                date = cert.get("date")

                # Build details array from issuer and date
                details = []
                if issuer:
                    details.append(f"Issuer: {issuer}")
                if date:
                    details.append(f"Date: {date}")

                logger.info(f"[{self.name}] Dict certificate - name: {name}, details: {details}")
                json_certificates.append({
                    "name": name,
                    "details": details
                })
            elif isinstance(cert, str):
                logger.info(f"[{self.name}] String certificate: {cert}")
                json_certificates.append({
                    "name": cert,
                    "details": []
                })
            else:
                logger.warning(f"[{self.name}] Unknown certificate type: {type(cert)} - {cert}")

        return {
            "basics": {
                "name": contact.get("name"),
                "email": contact.get("email"),
                "phone": contact.get("phone"),
                "url": contact.get("website"),
                "location": {
                    "address": contact.get("location")
                },
                "profiles": profiles
            },
            "work": sections.get("experience", []),
            "education": sections.get("education", []),
            "skills": json_skills,
            "projects": json_projects,
            "certificates": json_certificates
        }

    def _validate_cv_data(self, cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate CV data completeness

        Args:
            cv_data: JSON Resume formatted CV

        Returns:
            Validation result with completeness score and missing fields
        """
        missing_fields = []
        score = 0
        total_checks = 10

        # Check basics
        if cv_data.get("basics", {}).get("name"):
            score += 1
        else:
            missing_fields.append("basics.name")

        if cv_data.get("basics", {}).get("email"):
            score += 1
        else:
            missing_fields.append("basics.email")

        # Check work experience
        if cv_data.get("work") and len(cv_data["work"]) > 0:
            score += 2
        else:
            missing_fields.append("work")

        # Check education
        if cv_data.get("education") and len(cv_data["education"]) > 0:
            score += 2
        else:
            missing_fields.append("education")

        # Check skills
        if cv_data.get("skills") and len(cv_data["skills"]) > 0:
            score += 2
        else:
            missing_fields.append("skills")

        # Optional fields
        if cv_data.get("basics", {}).get("phone"):
            score += 1

        if cv_data.get("projects"):
            score += 1

        if cv_data.get("certificates"):
            score += 1

        completeness_score = (score / total_checks) * 100

        return {
            "is_valid": score >= 5,  # At least 50% complete
            "completeness_score": completeness_score,
            "missing_fields": missing_fields,
            "total_checks": total_checks,
            "passed_checks": score
        }

    async def process(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """Main processing entry point"""
        return await self.parse_cv(file_path=file_path, **kwargs)
