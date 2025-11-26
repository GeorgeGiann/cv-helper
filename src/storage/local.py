"""
Local Filesystem Storage Backend
For local development and testing
"""

import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging

from .base import StorageBackend

logger = logging.getLogger(__name__)


class LocalStorage(StorageBackend):
    """Local filesystem storage implementation"""

    def __init__(self, base_dir: str = "./data"):
        """
        Initialize local storage

        Args:
            base_dir: Base directory for all storage operations
        """
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Create standard subdirectories
        (self.base_dir / "uploads").mkdir(exist_ok=True)
        (self.base_dir / "outputs").mkdir(exist_ok=True)
        (self.base_dir / "sessions").mkdir(exist_ok=True)
        (self.base_dir / "temp").mkdir(exist_ok=True)

        logger.info(f"Initialized local storage at: {self.base_dir}")

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Upload file to local storage"""
        try:
            source = Path(local_path)
            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {local_path}")

            destination = self.base_dir / remote_path
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source, destination)

            # Store metadata if provided
            if metadata:
                self._save_metadata(destination, metadata)

            logger.info(f"Uploaded: {local_path} -> {destination}")
            return self.get_uri(remote_path)

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise

    def download_file(self, remote_path: str, local_path: str) -> str:
        """Download file from local storage (essentially a copy)"""
        try:
            source = self.base_dir / remote_path
            if not source.exists():
                raise FileNotFoundError(f"File not found: {remote_path}")

            destination = Path(local_path)
            destination.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(source, destination)

            logger.info(f"Downloaded: {source} -> {local_path}")
            return str(destination)

        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise

    def delete_file(self, remote_path: str) -> bool:
        """Delete file from local storage"""
        try:
            file_path = self.base_dir / remote_path
            if file_path.exists():
                file_path.unlink()

                # Also delete metadata if exists
                metadata_path = self._get_metadata_path(file_path)
                if metadata_path.exists():
                    metadata_path.unlink()

                logger.info(f"Deleted: {file_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        """List files with optional prefix"""
        try:
            search_dir = self.base_dir / prefix if prefix else self.base_dir
            if not search_dir.exists():
                return []

            files = []
            for file_path in search_dir.rglob("*"):
                if file_path.is_file() and not file_path.name.endswith(".metadata.json"):
                    relative_path = file_path.relative_to(self.base_dir)
                    files.append(str(relative_path))

            return sorted(files)

        except Exception as e:
            logger.error(f"List files failed: {e}")
            return []

    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists"""
        file_path = self.base_dir / remote_path
        return file_path.exists() and file_path.is_file()

    def get_file_metadata(self, remote_path: str) -> Dict[str, Any]:
        """Get file metadata"""
        try:
            file_path = self.base_dir / remote_path
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {remote_path}")

            # Load custom metadata if exists
            metadata_path = self._get_metadata_path(file_path)
            custom_metadata = {}
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    custom_metadata = json.load(f)

            # Get file stats
            stats = file_path.stat()

            metadata = {
                "name": file_path.name,
                "path": str(remote_path),
                "size_bytes": stats.st_size,
                "created_at": datetime.fromtimestamp(stats.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "mime_type": self._guess_mime_type(file_path),
                **custom_metadata
            }

            return metadata

        except Exception as e:
            logger.error(f"Get metadata failed: {e}")
            return {}

    def generate_signed_url(
        self,
        remote_path: str,
        expiration_seconds: int = 3600
    ) -> str:
        """
        Generate a 'signed' URL (for local, just returns file:// URI)
        Note: This is a simplified version for local dev
        """
        file_path = self.base_dir / remote_path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {remote_path}")

        return f"file://{file_path.absolute()}"

    def get_uri(self, remote_path: str) -> str:
        """Get file:// URI for local path"""
        file_path = self.base_dir / remote_path
        return f"file://{file_path.absolute()}"

    def _get_metadata_path(self, file_path: Path) -> Path:
        """Get path for metadata file"""
        return file_path.parent / f"{file_path.name}.metadata.json"

    def _save_metadata(self, file_path: Path, metadata: Dict[str, Any]) -> None:
        """Save metadata to companion file"""
        metadata_path = self._get_metadata_path(file_path)
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _guess_mime_type(self, file_path: Path) -> str:
        """Guess MIME type from file extension"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or "application/octet-stream"

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        total_size = 0
        file_count = 0

        for file_path in self.base_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.endswith(".metadata.json"):
                total_size += file_path.stat().st_size
                file_count += 1

        return {
            "backend": "local",
            "base_dir": str(self.base_dir),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_count": file_count
        }
