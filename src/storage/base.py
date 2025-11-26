"""
Base Storage Backend Interface
Defines the contract for all storage implementations (local, GCS)
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends"""

    @abstractmethod
    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Upload a file to storage

        Args:
            local_path: Path to local file
            remote_path: Destination path in storage
            metadata: Optional metadata to store with file

        Returns:
            Storage URI of uploaded file
        """
        pass

    @abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> str:
        """
        Download a file from storage

        Args:
            remote_path: Path in storage
            local_path: Local destination path

        Returns:
            Local file path
        """
        pass

    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete a file from storage

        Args:
            remote_path: Path in storage

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    def list_files(self, prefix: str = "") -> List[str]:
        """
        List files in storage with optional prefix filter

        Args:
            prefix: Path prefix to filter by

        Returns:
            List of file paths
        """
        pass

    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if file exists in storage

        Args:
            remote_path: Path in storage

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    def get_file_metadata(self, remote_path: str) -> Dict[str, Any]:
        """
        Get metadata for a file

        Args:
            remote_path: Path in storage

        Returns:
            Dictionary of metadata
        """
        pass

    @abstractmethod
    def generate_signed_url(
        self,
        remote_path: str,
        expiration_seconds: int = 3600
    ) -> str:
        """
        Generate a temporary signed URL for file access

        Args:
            remote_path: Path in storage
            expiration_seconds: URL expiration time

        Returns:
            Signed URL string
        """
        pass

    def get_uri(self, remote_path: str) -> str:
        """
        Get the full URI for a remote path

        Args:
            remote_path: Path in storage

        Returns:
            Full URI (e.g., 'gs://bucket/path' or 'file:///path')
        """
        pass
