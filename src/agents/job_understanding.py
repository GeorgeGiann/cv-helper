"""
Job Understanding Agent
Analyzes job advertisements and identifies skill gaps
"""

from typing import Dict, Any, Optional, List
import logging
import json

from .base_agent import BaseAgent
from ..tools.web_fetcher.main import WebFetcherTool

logger = logging.getLogger(__name__)


class JobUnderstandingAgent(BaseAgent):
    """
    ADK Agent for job advertisement analysis

    Responsibilities:
    - Parse job advertisements (text or URL)
    - Extract requirements, responsibilities, and skills
    - Identify must-have vs nice-to-have qualifications
    - Perform gap analysis against user CV
    - Prioritize missing information by importance
    """

    def __init__(self, llm_provider=None, storage_backend=None, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="job_understanding",
            description="Analyzes job advertisements and identifies skill gaps against CV",
            llm_provider=llm_provider,
            storage_backend=storage_backend,
            config=config
        )

        self.web_fetcher = WebFetcherTool()

    async def analyze_job(
        self,
        job_ad: str,
        source_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Analyze a job advertisement

        Args:
            job_ad: Job ad content (text) or URL
            source_type: 'text' or 'url'

        Returns:
            Structured job analysis
        """
        try:
            logger.info(f"[{self.name}] Analyzing job ad (source: {source_type})")

            # Fetch from URL if needed
            if source_type == "url":
                fetch_result = self.web_fetcher.execute(url=job_ad)
                if not fetch_result["success"]:
                    raise Exception(f"Failed to fetch job ad: {fetch_result['error']}")
                job_text = fetch_result["content"]
            else:
                job_text = job_ad

            # Use LLM to analyze job ad
            job_analysis = await self._extract_job_requirements(job_text)

            logger.info(f"[{self.name}] Extracted {len(job_analysis.get('requirements', {}).get('mustHave', []))} must-have requirements")

            return {
                "job_data": job_analysis,
                "source": job_ad if source_type == "url" else "text_input",
                "source_type": source_type
            }

        except Exception as e:
            logger.error(f"[{self.name}] Job analysis failed: {e}")
            raise

    async def analyze_gap(
        self,
        cv_data: Dict[str, Any],
        job_ad: str,
        source_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Perform gap analysis between CV and job requirements

        This is a key A2A action called by the orchestrator

        Args:
            cv_data: Parsed CV data (from CV Ingestion Agent)
            job_ad: Job advertisement (text or URL)
            source_type: 'text' or 'url'

        Returns:
            Gap analysis with prioritized questions
        """
        try:
            logger.info(f"[{self.name}] Starting gap analysis")

            # Step 1: Analyze job requirements
            job_analysis = await self.analyze_job(job_ad=job_ad, source_type=source_type)
            job_data = job_analysis["job_data"]

            # Step 2: Compare CV against requirements
            gap_analysis = await self._compare_cv_to_job(cv_data, job_data)

            # Step 3: Generate targeted questions
            questions = self._generate_questions(gap_analysis["gaps"])

            result = {
                "hasGaps": len(gap_analysis["gaps"]) > 0,
                "overallMatch": gap_analysis["overallMatch"],
                "gaps": gap_analysis["gaps"],
                "matches": gap_analysis["matches"],
                "recommendations": gap_analysis["recommendations"],
                "questionnaire": {
                    "questions": questions,
                    "estimatedTime": len(questions) * 2  # 2 min per question
                },
                "job_data": job_data
            }

            logger.info(f"[{self.name}] Gap analysis complete: {len(gap_analysis['gaps'])} gaps found, {gap_analysis['overallMatch']:.1f}% match")

            return result

        except Exception as e:
            logger.error(f"[{self.name}] Gap analysis failed: {e}")
            raise

    async def _extract_job_requirements(self, job_text: str) -> Dict[str, Any]:
        """
        Extract structured requirements from job text using LLM

        Args:
            job_text: Raw job advertisement text

        Returns:
            Structured job data following job_ad.json schema
        """
        if not self.llm_provider:
            raise ValueError("LLM provider required for job analysis")

        prompt = f"""Analyze this job advertisement and extract structured information.

Job Advertisement:
{job_text[:3000]}

Extract the following in JSON format:
{{
  "title": "Job title",
  "company": {{"name": "Company name"}},
  "description": "Brief summary",
  "requirements": {{
    "mustHave": [
      {{"category": "skill/experience/education", "description": "...", "keywords": ["..."]}},
    ],
    "niceToHave": [
      {{"category": "skill/experience/education", "description": "...", "keywords": ["..."]}},
    ]
  }},
  "skills": {{
    "technical": [{{"name": "...", "priority": "required/preferred", "level": "..."}}],
    "soft": [{{"name": "...", "priority": "required/preferred"}}]
  }},
  "experience": {{
    "yearsMin": 0,
    "level": "Entry/Junior/Mid/Senior/Lead"
  }},
  "employmentType": "Full-time/Part-time/Contract"
}}

Be thorough and extract ALL requirements mentioned. Categorize as must-have vs nice-to-have.
Return ONLY valid JSON."""

        try:
            response = await self.llm_provider.complete_json(
                prompt=prompt,
                temperature=0.2,
                max_tokens=2048
            )

            return response

        except Exception as e:
            logger.error(f"[{self.name}] LLM job extraction failed: {e}")
            raise

    async def _compare_cv_to_job(
        self,
        cv_data: Dict[str, Any],
        job_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare CV against job requirements using LLM

        Args:
            cv_data: JSON Resume formatted CV
            job_data: Structured job requirements

        Returns:
            Gap analysis with matches and gaps
        """
        if not self.llm_provider:
            raise ValueError("LLM provider required for gap analysis")

        cv_summary = {
            "name": cv_data.get("basics", {}).get("name"),
            "work": [
                {
                    "company": w.get("company") or w.get("name"),
                    "position": w.get("position"),
                    "duration": f"{w.get('startDate')} - {w.get('endDate', 'Present')}"
                }
                for w in cv_data.get("work", [])[:5]  # Last 5 jobs
            ],
            "education": [
                {
                    "institution": e.get("institution"),
                    "degree": e.get("studyType") or e.get("degree"),
                    "field": e.get("area") or e.get("field")
                }
                for e in cv_data.get("education", [])
            ],
            "skills": cv_data.get("skills", [])
        }

        prompt = f"""Compare this CV against job requirements and identify gaps.

CV Summary:
{json.dumps(cv_summary, indent=2)}

Job Requirements:
{json.dumps(job_data.get("requirements", {}), indent=2)}
{json.dumps(job_data.get("skills", {}), indent=2)}

Provide analysis in JSON format:
{{
  "overallMatch": 75,  // Percentage 0-100
  "gaps": [
    {{
      "id": "gap_1",
      "category": "skill/experience/education/certification",
      "priority": "critical/high/medium/low",
      "description": "What is missing",
      "requiredBy": "Which job requirement",
      "addressable": true/false  // Can be addressed with existing experience
    }}
  ],
  "matches": [
    {{
      "category": "skill/experience/education",
      "requirement": "Job requirement text",
      "evidence": "Where in CV this is demonstrated",
      "matchScore": 0.9  // 0-1
    }}
  ],
  "recommendations": [
    {{
      "type": "highlight/reorder/expand/add",
      "description": "What to do",
      "section": "CV section",
      "priority": "high/medium/low"
    }}
  ]
}}

Be honest about gaps but also identify hidden strengths. Return ONLY valid JSON."""

        try:
            response = await self.llm_provider.complete_json(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2048
            )

            return response

        except Exception as e:
            logger.error(f"[{self.name}] Gap comparison failed: {e}")
            raise

    def _generate_questions(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate targeted questions to fill gaps

        Args:
            gaps: List of identified gaps

        Returns:
            List of questions prioritized by importance
        """
        questions = []

        # Sort gaps by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_gaps = sorted(
            gaps,
            key=lambda g: priority_order.get(g.get("priority", "low"), 3)
        )

        for idx, gap in enumerate(sorted_gaps):
            gap_id = gap.get("id", f"gap_{idx}")
            category = gap.get("category", "skill")
            description = gap.get("description", "")

            # Generate question based on category
            if category == "skill":
                question = f"Do you have experience with {description}? If yes, please describe when and how you used it."
            elif category == "experience":
                question = f"Can you provide details about your experience with {description}?"
            elif category == "education":
                question = f"Do you have any education or training related to {description}?"
            elif category == "certification":
                question = f"Do you have certification in {description}? If yes, please provide details."
            else:
                question = f"Can you provide information about: {description}?"

            questions.append({
                "id": f"q_{idx + 1}",
                "question": question,
                "gapId": gap_id,
                "type": "text",
                "priority": gap.get("priority", "medium"),
                "answered": False,
                "answer": None
            })

        return questions

    async def process(self, **kwargs) -> Dict[str, Any]:
        """Main processing entry point"""
        if "cv_data" in kwargs:
            return await self.analyze_gap(**kwargs)
        else:
            return await self.analyze_job(**kwargs)
