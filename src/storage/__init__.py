"""
Storage Backend Package
Provides abstraction for local and cloud storage
"""

from .base import StorageBackend
from .local import LocalStorage
from .gcs import GCSStorage

__all__ = ["StorageBackend", "LocalStorage", "GCSStorage"]
