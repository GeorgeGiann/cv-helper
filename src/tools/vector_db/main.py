"""
Vector Database MCP Tool
Store and search CV embeddings for semantic similarity
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
import json
import pickle

import numpy as np

logger = logging.getLogger(__name__)


class VectorDBTool:
    """MCP tool for vector database operations"""

    def __init__(
        self,
        backend_type: str = "faiss",
        index_path: Optional[str] = None,
        embedding_model: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Vector DB tool

        Args:
            backend_type: 'faiss' for local or 'vertex' for Vertex AI
            index_path: Path to store/load FAISS index
            embedding_model: Model name for embeddings
            **kwargs: Backend-specific arguments
        """
        self.name = "vector_db"
        self.version = "1.0.0"
        self.backend_type = backend_type
        self.index_path = Path(index_path or "./data/embeddings")
        self.embedding_model = embedding_model or "sentence-transformers/all-MiniLM-L6-v2"

        # Initialize backend
        if backend_type == "faiss":
            from .faiss_backend import FAISSBackend
            self.backend = FAISSBackend(
                index_path=str(self.index_path),
                embedding_model=self.embedding_model
            )
        elif backend_type == "vertex":
            from .vertex_backend import VertexBackend
            self.backend = VertexBackend(
                project_id=kwargs.get("project_id"),
                location=kwargs.get("location", "us-central1"),
                index_id=kwargs.get("index_id")
            )
        else:
            raise ValueError(f"Unknown backend type: {backend_type}")

        logger.info(f"Initialized Vector DB: {backend_type}")

    def execute(
        self,
        operation: str,
        text: Optional[str] = None,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        score_threshold: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute vector DB operation

        Args:
            operation: 'store', 'search', 'delete', or 'list'
            text: Text to embed (for store/search)
            document_id: Document identifier (for store/delete)
            metadata: Metadata to store with embedding
            top_k: Number of results for search
            score_threshold: Minimum similarity score

        Returns:
            Dictionary with success, results, and optional error
        """
        try:
            if operation == "store":
                if not text or not document_id:
                    raise ValueError("text and document_id required for store operation")

                self.backend.store(
                    text=text,
                    document_id=document_id,
                    metadata=metadata or {}
                )

                return {
                    "success": True,
                    "results": [{"document_id": document_id, "operation": "stored"}],
                    "error": None
                }

            elif operation == "search":
                if not text:
                    raise ValueError("text required for search operation")

                results = self.backend.search(
                    query=text,
                    top_k=top_k,
                    score_threshold=score_threshold
                )

                return {
                    "success": True,
                    "results": results,
                    "error": None
                }

            elif operation == "delete":
                if not document_id:
                    raise ValueError("document_id required for delete operation")

                self.backend.delete(document_id)

                return {
                    "success": True,
                    "results": [{"document_id": document_id, "operation": "deleted"}],
                    "error": None
                }

            elif operation == "list":
                documents = self.backend.list_documents()

                return {
                    "success": True,
                    "results": documents,
                    "error": None
                }

            else:
                raise ValueError(f"Unknown operation: {operation}")

        except Exception as e:
            logger.error(f"Vector DB operation failed: {e}")
            return {
                "success": False,
                "results": [],
                "error": str(e)
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get vector database statistics"""
        return self.backend.get_stats()
