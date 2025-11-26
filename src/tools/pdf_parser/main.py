"""
PDF Parser MCP Tool
Extracts text and structured data from PDF CVs
"""

import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

import pdfplumber

from .extractor import CVSectionExtractor

logger = logging.getLogger(__name__)


class PDFParserTool:
    """MCP tool for parsing PDF CVs"""

    def __init__(self, storage_backend=None):
        self.name = "pdf_parser"
        self.version = "1.0.0"
        self.section_extractor = CVSectionExtractor()
        self.storage_backend = storage_backend  # Optional storage backend for remote files

    def execute(
        self,
        file_path: str,
        extract_images: bool = False,
        ocr_enabled: bool = False,
        language: str = "eng",
    ) -> Dict[str, Any]:
        """
        Parse a PDF file and extract structured data

        Args:
            file_path: Path to PDF file (local or gs:// URI)
            extract_images: Whether to extract images
            ocr_enabled: Enable OCR for image-based PDFs
            language: OCR language code

        Returns:
            Dictionary with parsed_data, success, and optional error
        """
        try:
            logger.info(f"Starting PDF parsing: {file_path}")

            # Handle GCS URIs
            if file_path.startswith("gs://"):
                file_path = self._download_from_gcs(file_path)

            # Validate file exists
            if not Path(file_path).exists():
                raise FileNotFoundError(f"PDF file not found: {file_path}")

            # Extract text from PDF
            text, metadata = self._extract_text(file_path, ocr_enabled, language)

            # Extract structured sections
            sections = self.section_extractor.extract_sections(text)

            parsed_data = {
                "text": text,
                "sections": sections,
                "metadata": metadata,
            }

            logger.info(f"Successfully parsed PDF: {file_path}")

            return {"parsed_data": parsed_data, "success": True, "error": None}

        except FileNotFoundError as e:
            logger.error(f"File not found: {e}")
            return {"parsed_data": None, "success": False, "error": str(e)}

        except Exception as e:
            logger.error(f"PDF parsing error: {e}", exc_info=True)
            return {
                "parsed_data": None,
                "success": False,
                "error": f"PDF parsing failed: {str(e)}",
            }

    def _extract_text(
        self, file_path: str, ocr_enabled: bool, language: str
    ) -> tuple[str, Dict[str, Any]]:
        """
        Extract text from PDF using pdfplumber

        Args:
            file_path: Local path to PDF
            ocr_enabled: Whether to use OCR
            language: OCR language

        Returns:
            Tuple of (extracted_text, metadata)
        """
        text_content = []
        metadata = {}

        with pdfplumber.open(file_path) as pdf:
            metadata["num_pages"] = len(pdf.pages)
            metadata["file_size_bytes"] = Path(file_path).stat().st_size
            metadata["extraction_method"] = "pdfplumber"

            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    # Try standard text extraction first
                    page_text = page.extract_text()

                    if not page_text and ocr_enabled:
                        # Fall back to OCR if no text found
                        logger.info(f"Using OCR for page {page_num}")
                        page_text = self._ocr_page(page, language)
                        metadata["extraction_method"] = "ocr"

                    if page_text:
                        text_content.append(page_text)

                except Exception as e:
                    logger.warning(f"Error extracting page {page_num}: {e}")
                    continue

        full_text = "\n\n".join(text_content)
        return full_text, metadata

    def _ocr_page(self, page, language: str) -> str:
        """
        Perform OCR on a PDF page

        Args:
            page: pdfplumber page object
            language: OCR language code

        Returns:
            OCR extracted text
        """
        try:
            import pytesseract
            from PIL import Image

            # Convert page to image
            img = page.to_image(resolution=300)
            pil_image = img.original

            # Perform OCR
            text = pytesseract.image_to_string(pil_image, lang=language)
            return text

        except ImportError:
            logger.error("pytesseract not installed. OCR disabled.")
            return ""
        except Exception as e:
            logger.error(f"OCR failed: {e}")
            return ""

    def _download_from_gcs(self, gcs_uri: str) -> str:
        """
        Download file from remote storage

        Args:
            gcs_uri: Storage URI (gs://bucket/path or file://path)

        Returns:
            Local file path
        """
        try:
            if not self.storage_backend:
                raise ValueError("Storage backend not configured for remote file access")

            # Parse URI
            if gcs_uri.startswith("gs://"):
                remote_path = gcs_uri.replace("gs://", "").split("/", 1)[1]
            elif gcs_uri.startswith("file://"):
                # Already local
                return gcs_uri.replace("file://", "")
            else:
                # Assume it's a remote path
                remote_path = gcs_uri

            # Download to temporary location
            local_path = f"/tmp/{Path(remote_path).name}"
            self.storage_backend.download_file(remote_path, local_path)

            logger.info(f"Downloaded from storage: {gcs_uri} -> {local_path}")
            return local_path

        except Exception as e:
            logger.error(f"Storage download failed: {e}")
            raise


class CVSectionExtractor:
    """Extract structured sections from CV text"""

    # Common section headers (case-insensitive patterns)
    SECTION_PATTERNS = {
        "contact": [
            r"contact\s*(information)?",
            r"personal\s*(information|details)",
        ],
        "summary": [r"summary", r"profile", r"objective", r"about\s*me"],
        "experience": [
            r"(work\s*)?experience",
            r"employment\s*(history)?",
            r"professional\s*experience",
        ],
        "education": [r"education", r"academic\s*(background)?", r"qualifications"],
        "skills": [
            r"skills",
            r"technical\s*skills",
            r"competencies",
            r"expertise",
        ],
        "projects": [r"projects", r"portfolio"],
        "certifications": [
            r"certifications?",
            r"certificates?",
            r"licenses?",
        ],
        "languages": [r"languages?"],
        "interests": [r"interests?", r"hobbies"],
    }

    def extract_sections(self, text: str) -> Dict[str, Any]:
        """
        Extract CV sections from text

        Args:
            text: Full CV text

        Returns:
            Dictionary of extracted sections
        """
        sections = {}

        # Extract contact information
        sections["contact"] = self._extract_contact(text)

        # Extract other sections by pattern matching
        section_boundaries = self._find_section_boundaries(text)

        for section_name, (start, end) in section_boundaries.items():
            section_text = text[start:end].strip()
            sections[section_name] = self._parse_section_content(
                section_name, section_text
            )

        return sections

    def _extract_contact(self, text: str) -> Dict[str, Optional[str]]:
        """
        Extract contact information from CV text

        Args:
            text: CV text

        Returns:
            Dictionary with contact fields
        """
        contact = {
            "email": None,
            "phone": None,
            "linkedin": None,
            "github": None,
            "website": None,
            "location": None,
        }

        # Email pattern
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        email_match = re.search(email_pattern, text)
        if email_match:
            contact["email"] = email_match.group(0)

        # Phone pattern (various formats)
        phone_pattern = r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}"
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            contact["phone"] = phone_match.group(0)

        # LinkedIn URL
        linkedin_pattern = r"linkedin\.com/in/[\w-]+"
        linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_match:
            contact["linkedin"] = f"https://{linkedin_match.group(0)}"

        # GitHub URL
        github_pattern = r"github\.com/[\w-]+"
        github_match = re.search(github_pattern, text, re.IGNORECASE)
        if github_match:
            contact["github"] = f"https://{github_match.group(0)}"

        # Website URL
        website_pattern = r"https?://(?:www\.)?[\w.-]+\.[a-z]{2,}"
        website_matches = re.findall(website_pattern, text, re.IGNORECASE)
        if website_matches:
            # Filter out LinkedIn/GitHub URLs
            for url in website_matches:
                if "linkedin" not in url.lower() and "github" not in url.lower():
                    contact["website"] = url
                    break

        return contact

    def _find_section_boundaries(self, text: str) -> Dict[str, tuple[int, int]]:
        """
        Find start and end positions of each section

        Args:
            text: CV text

        Returns:
            Dictionary mapping section names to (start, end) positions
        """
        boundaries = {}
        section_positions = []

        # Find all section headers
        for section_name, patterns in self.SECTION_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(
                    rf"^\s*{pattern}\s*$", text, re.MULTILINE | re.IGNORECASE
                )
                for match in matches:
                    section_positions.append(
                        (match.start(), section_name, match.group(0))
                    )

        # Sort by position
        section_positions.sort(key=lambda x: x[0])

        # Determine boundaries
        for i, (start_pos, section_name, header) in enumerate(section_positions):
            # Section starts after the header line
            content_start = start_pos + len(header)

            # Section ends at the next section header or end of text
            if i + 1 < len(section_positions):
                content_end = section_positions[i + 1][0]
            else:
                content_end = len(text)

            boundaries[section_name] = (content_start, content_end)

        return boundaries

    def _parse_section_content(
        self, section_name: str, section_text: str
    ) -> Any:
        """
        Parse section content based on section type

        Args:
            section_name: Name of the section
            section_text: Section text content

        Returns:
            Parsed section data (structure depends on section type)
        """
        # For now, return as list of paragraphs
        # In production, this would have specific parsers for each section type
        paragraphs = [p.strip() for p in section_text.split("\n\n") if p.strip()]

        if section_name in ["experience", "education", "projects", "certifications"]:
            return paragraphs  # List of entries
        elif section_name == "skills":
            # Try to extract individual skills
            skills = []
            for para in paragraphs:
                # Split by common delimiters
                items = re.split(r"[,;•|]", para)
                skills.extend([s.strip() for s in items if s.strip()])
            return skills
        else:
            return "\n\n".join(paragraphs)  # Single text block
