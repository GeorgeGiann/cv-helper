"""
FAISS Vector Database Backend
For local development with embeddings
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import json
import pickle

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class FAISSBackend:
    """FAISS-based vector database for local use"""

    def __init__(self, index_path: str, embedding_model: str):
        """
        Initialize FAISS backend

        Args:
            index_path: Path to store index and metadata
            embedding_model: Sentence transformers model name
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)

        self.index_file = self.index_path / "faiss.index"
        self.metadata_file = self.index_path / "metadata.json"

        # Load embedding model
        logger.info(f"Loading embedding model: {embedding_model}")
        self.model = SentenceTransformer(embedding_model)
        self.dimension = self.model.get_sentence_embedding_dimension()

        # Load or create index
        if self.index_file.exists():
            self.index = faiss.read_index(str(self.index_file))
            logger.info(f"Loaded FAISS index from: {self.index_file}")
        else:
            # Create new index (using cosine similarity)
            self.index = faiss.IndexFlatIP(self.dimension)
            logger.info(f"Created new FAISS index with dimension: {self.dimension}")

        # Load or create metadata
        if self.metadata_file.exists():
            with open(self.metadata_file, "r") as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "documents": {},  # document_id -> {metadata, index_position}
                "id_to_position": {},  # document_id -> index position
                "position_to_id": {}  # index position -> document_id
            }

    def store(self, text: str, document_id: str, metadata: Dict[str, Any]) -> None:
        """
        Store document embedding

        Args:
            text: Text to embed
            document_id: Unique document identifier
            metadata: Document metadata
        """
        # Generate embedding
        embedding = self.model.encode([text], normalize_embeddings=True)[0]

        # Check if document already exists
        if document_id in self.metadata["documents"]:
            logger.warning(f"Document {document_id} already exists, updating...")
            # For simplicity, we'll delete and re-add
            self.delete(document_id)

        # Add to index
        position = self.index.ntotal
        self.index.add(np.array([embedding], dtype=np.float32))

        # Store metadata
        self.metadata["documents"][document_id] = {
            "metadata": metadata,
            "text_preview": text[:200],  # Store preview for debugging
            "position": position
        }
        self.metadata["id_to_position"][document_id] = position
        self.metadata["position_to_id"][str(position)] = document_id

        # Save to disk
        self._save()

        logger.info(f"Stored document: {document_id} at position {position}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            query: Search query text
            top_k: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            List of results with document_id, score, and metadata
        """
        if self.index.ntotal == 0:
            logger.warning("Index is empty, returning no results")
            return []

        # Generate query embedding
        query_embedding = self.model.encode([query], normalize_embeddings=True)[0]

        # Search
        scores, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32),
            min(top_k, self.index.ntotal)
        )

        # Format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if score < score_threshold:
                continue

            # Get document ID from position
            document_id = self.metadata["position_to_id"].get(str(idx))
            if not document_id:
                logger.warning(f"No document found for position {idx}")
                continue

            doc_metadata = self.metadata["documents"][document_id]["metadata"]

            results.append({
                "document_id": document_id,
                "score": float(score),
                "metadata": doc_metadata
            })

        logger.info(f"Search returned {len(results)} results above threshold {score_threshold}")
        return results

    def delete(self, document_id: str) -> None:
        """
        Delete document from index

        Args:
            document_id: Document identifier
        """
        if document_id not in self.metadata["documents"]:
            logger.warning(f"Document {document_id} not found")
            return

        # Note: FAISS doesn't support deletion, so we mark as deleted
        # and rebuild index if too many deletions accumulate
        position = self.metadata["documents"][document_id]["position"]

        del self.metadata["documents"][document_id]
        del self.metadata["id_to_position"][document_id]
        del self.metadata["position_to_id"][str(position)]

        self._save()

        logger.info(f"Marked document {document_id} as deleted")

        # TODO: Implement index rebuilding if needed

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents in index

        Returns:
            List of document information
        """
        documents = []
        for doc_id, doc_info in self.metadata["documents"].items():
            documents.append({
                "document_id": doc_id,
                "metadata": doc_info["metadata"],
                "position": doc_info["position"]
            })

        return documents

    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "backend": "faiss",
            "dimension": self.dimension,
            "total_vectors": self.index.ntotal,
            "total_documents": len(self.metadata["documents"]),
            "index_path": str(self.index_path),
            "embedding_model": self.model._model_card_data.model_id if hasattr(self.model, "_model_card_data") else "unknown"
        }

    def _save(self) -> None:
        """Save index and metadata to disk"""
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)
