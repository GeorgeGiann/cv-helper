"""
Unit tests for PDF Parser tool
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import PDFParserTool
from extractor import CVSectionExtractor


class TestPDFParserTool:
    """Tests for PDFParserTool class"""

    @pytest.fixture
    def parser_tool(self):
        return PDFParserTool()

    @pytest.fixture
    def sample_cv_text(self):
        return """
        John Doe
        john.doe@example.com | +1-555-123-4567
        San Francisco, CA | linkedin.com/in/johndoe

        SUMMARY
        Experienced software engineer with 5+ years in full-stack development.

        EXPERIENCE

        Senior Software Engineer at Tech Corp
        January 2020 - Present
        • Led development of microservices architecture
        • Reduced API latency by 50%
        • Mentored 3 junior developers

        Software Engineer at StartupXYZ
        June 2018 - December 2019
        • Built React-based dashboard
        • Implemented CI/CD pipeline

        EDUCATION

        Bachelor of Science in Computer Science
        University of California, Berkeley
        2014 - 2018
        GPA: 3.8

        SKILLS

        Programming: Python, JavaScript, Go, TypeScript
        Frameworks: React, Django, Flask, Node.js
        Tools: Docker, Kubernetes, AWS, Git
        """

    def test_tool_initialization(self, parser_tool):
        """Test tool initializes correctly"""
        assert parser_tool.name == "pdf_parser"
        assert parser_tool.version == "1.0.0"
        assert isinstance(parser_tool.section_extractor, CVSectionExtractor)

    @patch("main.pdfplumber.open")
    def test_extract_text_success(self, mock_pdf, parser_tool, tmp_path):
        """Test successful text extraction from PDF"""
        # Create a temporary PDF file
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        # Mock pdfplumber
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample CV text"
        mock_pdf_obj = Mock()
        mock_pdf_obj.pages = [mock_page]
        mock_pdf_obj.__enter__ = Mock(return_value=mock_pdf_obj)
        mock_pdf_obj.__exit__ = Mock(return_value=None)
        mock_pdf.return_value = mock_pdf_obj

        result = parser_tool.execute(str(test_file))

        assert result["success"] is True
        assert result["error"] is None
        assert "parsed_data" in result
        assert result["parsed_data"]["text"] == "Sample CV text"

    def test_execute_file_not_found(self, parser_tool):
        """Test handling of non-existent file"""
        result = parser_tool.execute("/nonexistent/file.pdf")

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["parsed_data"] is None

    @patch("main.storage.Client")
    def test_download_from_gcs(self, mock_storage, parser_tool, tmp_path):
        """Test downloading file from GCS"""
        # Mock GCS client
        mock_blob = Mock()
        mock_bucket = Mock()
        mock_bucket.blob.return_value = mock_blob
        mock_client = Mock()
        mock_client.bucket.return_value = mock_bucket
        mock_storage.return_value = mock_client

        gcs_uri = "gs://test-bucket/path/to/cv.pdf"
        local_path = parser_tool._download_from_gcs(gcs_uri)

        assert local_path == "/tmp/cv.pdf"
        mock_client.bucket.assert_called_once_with("test-bucket")
        mock_bucket.blob.assert_called_once_with("path/to/cv.pdf")
        mock_blob.download_to_filename.assert_called_once()


class TestCVSectionExtractor:
    """Tests for CVSectionExtractor class"""

    @pytest.fixture
    def extractor(self):
        return CVSectionExtractor()

    def test_extract_contact_email(self, extractor):
        """Test email extraction"""
        text = "John Doe\njohn.doe@example.com\n+1-555-1234"
        contact = extractor._extract_contact(text)

        assert contact["email"] == "john.doe@example.com"
        assert contact["name"] == "John Doe"

    def test_extract_contact_phone(self, extractor):
        """Test phone number extraction"""
        text = "Contact: +1-555-123-4567"
        contact = extractor._extract_contact(text)

        assert contact["phone"] is not None
        assert "555" in contact["phone"]

    def test_extract_contact_linkedin(self, extractor):
        """Test LinkedIn extraction"""
        text = "linkedin.com/in/johndoe"
        contact = extractor._extract_contact(text)

        assert contact["linkedin"] == "https://linkedin.com/in/johndoe"

    def test_extract_contact_github(self, extractor):
        """Test GitHub extraction"""
        text = "github.com/johndoe"
        contact = extractor._extract_contact(text)

        assert contact["github"] == "https://github.com/johndoe"

    def test_parse_experience(self, extractor):
        """Test work experience parsing"""
        text = """
        Senior Software Engineer at Tech Corp
        January 2020 - Present
        • Led development of microservices
        • Reduced latency by 50%

        Software Engineer at StartupXYZ
        June 2018 - December 2019
        • Built React dashboard
        """
        experiences = extractor._parse_experience(text)

        assert len(experiences) == 2
        assert experiences[0]["position"] == "Senior Software Engineer"
        assert experiences[0]["company"] == "Tech Corp"
        assert experiences[0]["startDate"] == "January 2020"
        assert experiences[0]["endDate"] is None  # Present
        assert len(experiences[0]["highlights"]) == 2

    def test_parse_education(self, extractor):
        """Test education parsing"""
        text = """
        Bachelor of Science in Computer Science
        University of California, Berkeley
        2014 - 2018
        GPA: 3.8
        """
        education = extractor._parse_education(text)

        assert len(education) >= 1
        assert "Berkeley" in education[0]["institution"]
        assert education[0]["startDate"] == "2014"
        assert education[0]["endDate"] == "2018"
        assert education[0]["gpa"] == "3.8"

    def test_parse_skills_categorized(self, extractor):
        """Test skills parsing with categories"""
        text = """
        Programming: Python, JavaScript, Go
        Frameworks: React, Django, Flask
        Tools: Docker, Kubernetes, AWS
        """
        skills = extractor._parse_skills(text)

        assert len(skills) == 3
        assert any(s["category"] == "Programming" for s in skills)
        prog_skills = next(s for s in skills if s["category"] == "Programming")
        assert "Python" in prog_skills["items"]
        assert "JavaScript" in prog_skills["items"]

    def test_parse_skills_flat_list(self, extractor):
        """Test skills parsing without categories"""
        text = "Python, JavaScript, React, Docker, AWS"
        skills = extractor._parse_skills(text)

        assert len(skills) >= 1
        assert "Python" in skills[0]["items"]

    def test_find_section_boundaries(self, extractor):
        """Test section boundary detection"""
        text = """
        SUMMARY
        Experienced software engineer

        EXPERIENCE
        Senior Engineer at Company

        EDUCATION
        BS in Computer Science
        """
        boundaries = extractor._find_section_boundaries(text)

        assert "summary" in boundaries
        assert "experience" in boundaries
        assert "education" in boundaries

        # Summary should come before experience
        assert boundaries["summary"][0] < boundaries["experience"][0]

    def test_parse_projects(self, extractor):
        """Test project parsing"""
        text = """
        E-commerce Platform
        https://github.com/user/project
        • Built with React and Node.js
        • Integrated payment processing

        Data Analytics Tool
        Python-based analytics dashboard
        """
        projects = extractor._parse_projects(text)

        assert len(projects) == 2
        assert projects[0]["name"] == "E-commerce Platform"
        assert projects[0]["url"] == "https://github.com/user/project"
        assert len(projects[0]["highlights"]) == 2

    def test_parse_certifications(self, extractor):
        """Test certification parsing"""
        text = """
        • AWS Certified Solutions Architect - Amazon Web Services, 2022
        • Kubernetes Administrator (CKA) - CNCF, 2021
        """
        certifications = extractor._parse_certifications(text)

        assert len(certifications) == 2
        assert "AWS" in certifications[0]["name"]
        assert certifications[0]["date"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
