"""
CV Section Extractor
Advanced extraction logic for CV sections
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CVSectionExtractor:
    """Extract and parse structured sections from CV text"""

    # Section header patterns (case-insensitive)
    SECTION_PATTERNS = {
        "summary": [r"summary", r"profile", r"objective", r"about\s*me"],
        "experience": [
            r"(work\s*)?experience",
            r"employment\s*(history)?",
            r"professional\s*experience",
            r"career\s*history",
        ],
        "education": [
            r"education",
            r"academic\s*(background)?",
            r"qualifications",
            r"degrees?",
        ],
        "skills": [
            r"skills",
            r"technical\s*skills",
            r"competencies",
            r"expertise",
            r"proficiencies",
        ],
        "projects": [r"projects", r"portfolio", r"personal\s*projects"],
        "certifications": [
            r"certifications?",
            r"certificates?",
            r"licenses?",
            r"professional\s*certifications?",
        ],
        "languages": [r"languages?", r"language\s*proficiency"],
        "interests": [r"interests?", r"hobbies", r"activities"],
        "publications": [r"publications?", r"papers?", r"research"],
        "awards": [r"awards?", r"honors?", r"achievements?"],
    }

    def extract_sections(self, text: str) -> Dict[str, Any]:
        """
        Extract all CV sections from text

        Args:
            text: Full CV text

        Returns:
            Dictionary of extracted and parsed sections
        """
        sections = {}

        # Extract contact information (appears at top of CV)
        sections["contact"] = self._extract_contact(text[:1000])

        # Find section boundaries
        section_boundaries = self._find_section_boundaries(text)

        # Parse each section
        for section_name, (start, end) in section_boundaries.items():
            section_text = text[start:end].strip()

            if section_name == "experience":
                sections["experience"] = self._parse_experience(section_text)
            elif section_name == "education":
                sections["education"] = self._parse_education(section_text)
            elif section_name == "skills":
                sections["skills"] = self._parse_skills(section_text)
            elif section_name == "projects":
                sections["projects"] = self._parse_projects(section_text)
            elif section_name == "certifications":
                sections["certifications"] = self._parse_certifications(section_text)
            else:
                # Default: return as text
                sections[section_name] = section_text

        return sections

    def _extract_contact(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contact information from CV header"""
        contact = {
            "name": None,
            "email": None,
            "phone": None,
            "linkedin": None,
            "github": None,
            "website": None,
            "location": None,
        }

        # Name (typically first line or largest text)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if lines:
            # Assume first substantial line is name
            contact["name"] = lines[0]

        # Email
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        email_match = re.search(email_pattern, text)
        if email_match:
            contact["email"] = email_match.group(0)

        # Phone (various international formats)
        phone_pattern = (
            r"(\+?\d{1,3}[-.\s]?)?(\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}"
        )
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            contact["phone"] = phone_match.group(0).strip()

        # LinkedIn
        linkedin_pattern = r"(?:linkedin\.com/in/|linkedin:?\s*)([\w-]+)"
        linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_match:
            username = linkedin_match.group(1)
            contact["linkedin"] = f"https://linkedin.com/in/{username}"

        # GitHub
        github_pattern = r"(?:github\.com/|github:?\s*)([\w-]+)"
        github_match = re.search(github_pattern, text, re.IGNORECASE)
        if github_match:
            username = github_match.group(1)
            contact["github"] = f"https://github.com/{username}"

        # Website
        website_pattern = r"https?://(?:www\.)?[\w.-]+\.[a-z]{2,}(?:/[\w.-]*)*"
        for match in re.finditer(website_pattern, text, re.IGNORECASE):
            url = match.group(0)
            if "linkedin" not in url.lower() and "github" not in url.lower():
                contact["website"] = url
                break

        # Location (city, state/country)
        location_pattern = r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),\s*([A-Z]{2}|[A-Z][a-z]+)"
        location_match = re.search(location_pattern, text)
        if location_match:
            contact["location"] = location_match.group(0)

        return contact

    def _find_section_boundaries(self, text: str) -> Dict[str, Tuple[int, int]]:
        """Find start and end positions of each section"""
        boundaries = {}
        section_positions = []

        # Find all section headers
        for section_name, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                # Look for section headers (typically on their own line, possibly with decorations)
                matches = re.finditer(
                    rf"^[\s\-=]*{pattern}[\s\-=:]*$",
                    text,
                    re.MULTILINE | re.IGNORECASE,
                )
                for match in matches:
                    section_positions.append((match.start(), section_name))
                    break  # Use first match for this section

        # Sort by position
        section_positions.sort(key=lambda x: x[0])

        # Determine content boundaries
        for i, (start_pos, section_name) in enumerate(section_positions):
            # Find end of header line
            header_end = text.find("\n", start_pos)
            if header_end == -1:
                continue

            content_start = header_end + 1

            # Content ends at next section or end of text
            if i + 1 < len(section_positions):
                content_end = section_positions[i + 1][0]
            else:
                content_end = len(text)

            boundaries[section_name] = (content_start, content_end)

        return boundaries

    def _parse_experience(self, text: str) -> List[Dict[str, Any]]:
        """Parse work experience entries"""
        experiences = []

        # Split into individual job entries (typically separated by blank lines)
        entries = re.split(r"\n\s*\n", text)

        for entry in entries:
            if not entry.strip():
                continue

            lines = [l.strip() for l in entry.split("\n") if l.strip()]
            if not lines:
                continue

            exp = {
                "position": None,
                "company": None,
                "location": None,
                "startDate": None,
                "endDate": None,
                "description": None,
                "highlights": [],
            }

            # First line often contains position and company
            first_line = lines[0]

            # Try to extract position and company
            # Pattern: "Position at Company" or "Position | Company"
            position_company_pattern = r"(.+?)\s+(?:at|@|\|)\s+(.+)"
            match = re.search(position_company_pattern, first_line)
            if match:
                exp["position"] = match.group(1).strip()
                exp["company"] = match.group(2).strip()
            else:
                exp["position"] = first_line

            # Look for dates (various formats)
            date_pattern = r"(\d{4}|\w+\s+\d{4})\s*[-–—]\s*(\d{4}|\w+\s+\d{4}|Present|Current)"
            for line in lines:
                date_match = re.search(date_pattern, line, re.IGNORECASE)
                if date_match:
                    exp["startDate"] = date_match.group(1)
                    exp["endDate"] = (
                        None
                        if date_match.group(2).lower() in ["present", "current"]
                        else date_match.group(2)
                    )
                    break

            # Collect bullet points (achievements/responsibilities)
            bullet_pattern = r"^[\s]*[•\-\*]\s*(.+)"
            for line in lines[1:]:
                bullet_match = re.match(bullet_pattern, line)
                if bullet_match:
                    exp["highlights"].append(bullet_match.group(1).strip())
                elif not re.search(date_pattern, line):
                    # Non-bullet descriptive text
                    if exp["description"]:
                        exp["description"] += " " + line
                    else:
                        exp["description"] = line

            experiences.append(exp)

        return experiences

    def _parse_education(self, text: str) -> List[Dict[str, Any]]:
        """Parse education entries"""
        education = []

        entries = re.split(r"\n\s*\n", text)

        for entry in entries:
            if not entry.strip():
                continue

            lines = [l.strip() for l in entry.split("\n") if l.strip()]
            if not lines:
                continue

            edu = {
                "institution": None,
                "degree": None,
                "field": None,
                "startDate": None,
                "endDate": None,
                "gpa": None,
                "honors": None,
            }

            # First line typically contains degree or institution
            edu["institution"] = lines[0]

            # Look for degree information
            degree_pattern = r"(Bachelor|Master|PhD|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|Doctor)"
            for line in lines:
                degree_match = re.search(degree_pattern, line, re.IGNORECASE)
                if degree_match:
                    edu["degree"] = line
                    break

            # Look for dates
            date_pattern = r"(\d{4})\s*[-–—]\s*(\d{4}|Present|Expected)"
            for line in lines:
                date_match = re.search(date_pattern, line, re.IGNORECASE)
                if date_match:
                    edu["startDate"] = date_match.group(1)
                    edu["endDate"] = date_match.group(2)
                    break

            # Look for GPA
            gpa_pattern = r"GPA:?\s*(\d+\.\d+)"
            for line in lines:
                gpa_match = re.search(gpa_pattern, line, re.IGNORECASE)
                if gpa_match:
                    edu["gpa"] = gpa_match.group(1)
                    break

            education.append(edu)

        return education

    def _parse_skills(self, text: str) -> List[Dict[str, Any]]:
        """Parse skills section"""
        skills = []

        # Look for categorized skills (e.g., "Programming: Python, Java")
        category_pattern = r"([^:\n]+):\s*([^\n]+)"
        matches = re.finditer(category_pattern, text)

        for match in matches:
            category = match.group(1).strip()
            skills_text = match.group(2).strip()

            # Split skills by common delimiters
            skill_items = re.split(r"[,;•|]", skills_text)
            skill_items = [s.strip() for s in skill_items if s.strip()]

            skills.append({"category": category, "items": skill_items})

        # If no categorized skills found, extract flat list
        if not skills:
            items = re.split(r"[,;•|\n]", text)
            items = [s.strip() for s in items if s.strip()]
            if items:
                skills.append({"category": "General", "items": items})

        return skills

    def _parse_projects(self, text: str) -> List[Dict[str, Any]]:
        """Parse project entries"""
        projects = []

        entries = re.split(r"\n\s*\n", text)

        for entry in entries:
            if not entry.strip():
                continue

            lines = [l.strip() for l in entry.split("\n") if l.strip()]
            if not lines:
                continue

            project = {
                "name": lines[0],
                "description": None,
                "technologies": [],
                "url": None,
                "highlights": [],
            }

            # Extract URL if present
            url_pattern = r"https?://[\w.-]+(?:/[\w.-]*)*"
            url_match = re.search(url_pattern, entry)
            if url_match:
                project["url"] = url_match.group(0)

            # Collect description and highlights
            bullet_pattern = r"^[\s]*[•\-\*]\s*(.+)"
            for line in lines[1:]:
                bullet_match = re.match(bullet_pattern, line)
                if bullet_match:
                    project["highlights"].append(bullet_match.group(1).strip())
                elif not url_match or url_match.group(0) not in line:
                    if project["description"]:
                        project["description"] += " " + line
                    else:
                        project["description"] = line

            projects.append(project)

        return projects

    def _parse_certifications(self, text: str) -> List[Dict[str, Any]]:
        """Parse certification entries"""
        certifications = []

        # Certifications are often one per line or separated by bullets
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        for line in lines:
            # Remove bullet points
            line = re.sub(r"^[•\-\*]\s*", "", line)

            cert = {"name": line, "issuer": None, "date": None, "credential": None}

            # Try to extract issuer (often after hyphen or comma)
            parts = re.split(r"\s+[-–—,]\s+", line)
            if len(parts) >= 2:
                cert["name"] = parts[0]
                cert["issuer"] = parts[1]

            # Look for dates
            date_pattern = r"(\w+\s+\d{4}|\d{4})"
            date_match = re.search(date_pattern, line)
            if date_match:
                cert["date"] = date_match.group(1)

            certifications.append(cert)

        return certifications
