"""
Web Fetcher MCP Tool
Fetch and parse job advertisements from URLs
"""

from typing import Dict, Any, Optional
import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebFetcherTool:
    """MCP tool for fetching web content"""

    def __init__(self, timeout: int = 30):
        """
        Initialize web fetcher

        Args:
            timeout: Request timeout in seconds
        """
        self.name = "web_fetcher"
        self.version = "1.0.0"
        self.timeout = timeout

    def execute(self, url: str, extract_text_only: bool = True) -> Dict[str, Any]:
        """
        Fetch content from URL

        Args:
            url: URL to fetch
            extract_text_only: If True, extract only text content

        Returns:
            Dictionary with success, content, and optional error
        """
        try:
            logger.info(f"Fetching URL: {url}")

            # Fetch page
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": "CV-Enhancer-Bot/1.0"}
            )
            response.raise_for_status()

            if extract_text_only:
                # Parse HTML and extract text
                soup = BeautifulSoup(response.content, "html.parser")

                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Get text
                text = soup.get_text()

                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = "\n".join(chunk for chunk in chunks if chunk)

                return {
                    "success": True,
                    "content": text,
                    "url": url,
                    "status_code": response.status_code,
                    "error": None
                }
            else:
                # Return raw HTML
                return {
                    "success": True,
                    "content": response.text,
                    "url": url,
                    "status_code": response.status_code,
                    "error": None
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Web fetch failed: {e}")
            return {
                "success": False,
                "content": None,
                "url": url,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {
                "success": False,
                "content": None,
                "url": url,
                "error": str(e)
            }
