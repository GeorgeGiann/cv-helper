"""
Google Cloud Storage Backend
For production deployment on Kaggle/GCP
"""

from typing import Optional, List, Dict, Any
from datetime import timedelta
import logging

from google.cloud import storage
from google.cloud.exceptions import NotFound

from .base import StorageBackend

logger = logging.getLogger(__name__)


class GCSStorage(StorageBackend):
    """Google Cloud Storage implementation"""

    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        Initialize GCS storage

        Args:
            bucket_name: Name of the GCS bucket
            project_id: GCP project ID (optional, uses default if not provided)
        """
        self.bucket_name = bucket_name
        self.project_id = project_id

        try:
            if project_id:
                self.client = storage.Client(project=project_id)
            else:
                self.client = storage.Client()

            self.bucket = self.client.bucket(bucket_name)
            logger.info(f"Initialized GCS storage: gs://{bucket_name}")

        except Exception as e:
            logger.error(f"Failed to initialize GCS: {e}")
            raise

    def upload_file(
        self,
        local_path: str,
        remote_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Upload file to GCS"""
        try:
            blob = self.bucket.blob(remote_path)

            # Set metadata if provided
            if metadata:
                blob.metadata = metadata

            # Upload file
            blob.upload_from_filename(local_path)

            uri = self.get_uri(remote_path)
            logger.info(f"Uploaded: {local_path} -> {uri}")
            return uri

        except Exception as e:
            logger.error(f"GCS upload failed: {e}")
            raise

    def download_file(self, remote_path: str, local_path: str) -> str:
        """Download file from GCS"""
        try:
            blob = self.bucket.blob(remote_path)

            if not blob.exists():
                raise FileNotFoundError(f"File not found in GCS: {remote_path}")

            blob.download_to_filename(local_path)

            logger.info(f"Downloaded: gs://{self.bucket_name}/{remote_path} -> {local_path}")
            return local_path

        except Exception as e:
            logger.error(f"GCS download failed: {e}")
            raise

    def delete_file(self, remote_path: str) -> bool:
        """Delete file from GCS"""
        try:
            blob = self.bucket.blob(remote_path)

            if blob.exists():
                blob.delete()
                logger.info(f"Deleted: gs://{self.bucket_name}/{remote_path}")
                return True
            return False

        except Exception as e:
            logger.error(f"GCS delete failed: {e}")
            return False

    def list_files(self, prefix: str = "") -> List[str]:
        """List files in GCS with optional prefix"""
        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            files = [blob.name for blob in blobs]
            return sorted(files)

        except Exception as e:
            logger.error(f"GCS list files failed: {e}")
            return []

    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in GCS"""
        try:
            blob = self.bucket.blob(remote_path)
            return blob.exists()
        except Exception:
            return False

    def get_file_metadata(self, remote_path: str) -> Dict[str, Any]:
        """Get file metadata from GCS"""
        try:
            blob = self.bucket.blob(remote_path)

            if not blob.exists():
                raise FileNotFoundError(f"File not found in GCS: {remote_path}")

            # Reload to get latest metadata
            blob.reload()

            metadata = {
                "name": blob.name,
                "path": remote_path,
                "size_bytes": blob.size,
                "created_at": blob.time_created.isoformat() if blob.time_created else None,
                "modified_at": blob.updated.isoformat() if blob.updated else None,
                "mime_type": blob.content_type,
                "md5_hash": blob.md5_hash,
                "etag": blob.etag,
                "generation": blob.generation,
            }

            # Add custom metadata if present
            if blob.metadata:
                metadata.update(blob.metadata)

            return metadata

        except Exception as e:
            logger.error(f"GCS get metadata failed: {e}")
            return {}

    def generate_signed_url(
        self,
        remote_path: str,
        expiration_seconds: int = 3600
    ) -> str:
        """Generate a signed URL for temporary access"""
        try:
            blob = self.bucket.blob(remote_path)

            if not blob.exists():
                raise FileNotFoundError(f"File not found in GCS: {remote_path}")

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration_seconds),
                method="GET"
            )

            logger.info(f"Generated signed URL for: {remote_path}")
            return url

        except Exception as e:
            logger.error(f"GCS generate signed URL failed: {e}")
            raise

    def get_uri(self, remote_path: str) -> str:
        """Get gs:// URI for GCS path"""
        return f"gs://{self.bucket_name}/{remote_path}"

    def copy_file(self, source_path: str, destination_path: str) -> str:
        """
        Copy file within GCS

        Args:
            source_path: Source blob path
            destination_path: Destination blob path

        Returns:
            URI of copied file
        """
        try:
            source_blob = self.bucket.blob(source_path)
            self.bucket.copy_blob(source_blob, self.bucket, destination_path)

            logger.info(f"Copied: {source_path} -> {destination_path}")
            return self.get_uri(destination_path)

        except Exception as e:
            logger.error(f"GCS copy failed: {e}")
            raise

    def set_file_metadata(
        self,
        remote_path: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Update file metadata

        Args:
            remote_path: Path to file
            metadata: Metadata dictionary to set
        """
        try:
            blob = self.bucket.blob(remote_path)

            if not blob.exists():
                raise FileNotFoundError(f"File not found in GCS: {remote_path}")

            blob.metadata = metadata
            blob.patch()

            logger.info(f"Updated metadata for: {remote_path}")

        except Exception as e:
            logger.error(f"GCS set metadata failed: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            total_size = 0
            file_count = 0

            for blob in self.bucket.list_blobs():
                total_size += blob.size or 0
                file_count += 1

            return {
                "backend": "gcs",
                "bucket": self.bucket_name,
                "project": self.project_id,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count
            }

        except Exception as e:
            logger.error(f"Get stats failed: {e}")
            return {
                "backend": "gcs",
                "bucket": self.bucket_name,
                "error": str(e)
            }
