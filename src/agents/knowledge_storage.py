"""
Knowledge Storage Agent
Manages persistent data storage and retrieval
"""

from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime
from pathlib import Path

from .base_agent import BaseAgent
from ..tools.vector_db.main import VectorDBTool

logger = logging.getLogger(__name__)


class KnowledgeStorageAgent(BaseAgent):
    """
    ADK Agent for knowledge and data persistence

    Responsibilities:
    - Store CV profile JSON (Firestore/SQLite)
    - Generate and store embeddings in Vector DB
    - Manage session metadata and history
    - Provide retrieval capabilities for similar profiles
    - Handle versioning of user profiles
    """

    def __init__(self, llm_provider=None, storage_backend=None, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="knowledge_storage",
            description="Manages persistent storage of CVs, sessions, and embeddings",
            llm_provider=llm_provider,
            storage_backend=storage_backend,
            config=config
        )

        # Initialize vector DB
        vector_db_type = config.get("vector_db_type", "faiss")
        vector_db_path = config.get("vector_db_path", "./data/embeddings")

        self.vector_db = VectorDBTool(
            backend_type=vector_db_type,
            index_path=vector_db_path
        )

        # Session storage (simplified - using JSON files)
        self.sessions_dir = Path(config.get("data_dir", "./data")) / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self.profiles_dir = Path(config.get("data_dir", "./data")) / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    async def store_cv(
        self,
        user_id: str,
        cv_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store CV profile

        Args:
            user_id: User identifier
            cv_data: JSON Resume formatted CV
            metadata: Optional metadata

        Returns:
            Storage result with profile ID and URI
        """
        try:
            logger.info(f"[{self.name}] Storing CV for user: {user_id}")

            # Generate profile ID
            profile_id = f"profile_{user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            # Create profile document
            profile_doc = {
                "profile_id": profile_id,
                "user_id": user_id,
                "cv_data": cv_data,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "version": "1.0"
            }

            # Store in local file system (simulating Firestore)
            profile_file = self.profiles_dir / f"{profile_id}.json"
            with open(profile_file, "w") as f:
                json.dump(profile_doc, f, indent=2)

            # Generate and store embedding for semantic search
            cv_text = self._cv_to_text(cv_data)
            embedding_result = self.vector_db.execute(
                operation="store",
                text=cv_text,
                document_id=profile_id,
                metadata={
                    "user_id": user_id,
                    "name": cv_data.get("basics", {}).get("name"),
                    "profile_id": profile_id
                }
            )

            if not embedding_result["success"]:
                logger.warning(f"[{self.name}] Embedding storage failed: {embedding_result['error']}")

            logger.info(f"[{self.name}] Stored CV profile: {profile_id}")

            return {
                "profile_id": profile_id,
                "user_id": user_id,
                "uri": str(profile_file),
                "embedding_stored": embedding_result["success"]
            }

        except Exception as e:
            logger.error(f"[{self.name}] CV storage failed: {e}")
            raise

    async def retrieve_cv(
        self,
        profile_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve CV profile

        Args:
            profile_id: Specific profile ID
            user_id: User ID (returns latest profile)

        Returns:
            CV profile data
        """
        try:
            if profile_id:
                logger.info(f"[{self.name}] Retrieving CV by profile ID: {profile_id}")
                profile_file = self.profiles_dir / f"{profile_id}.json"

                if not profile_file.exists():
                    raise FileNotFoundError(f"Profile not found: {profile_id}")

                with open(profile_file, "r") as f:
                    profile_doc = json.load(f)

                return profile_doc

            elif user_id:
                logger.info(f"[{self.name}] Retrieving latest CV for user: {user_id}")

                # Find latest profile for user
                user_profiles = list(self.profiles_dir.glob(f"profile_{user_id}_*.json"))

                if not user_profiles:
                    raise FileNotFoundError(f"No profiles found for user: {user_id}")

                # Sort by creation time (filename)
                latest_profile = sorted(user_profiles)[-1]

                with open(latest_profile, "r") as f:
                    profile_doc = json.load(f)

                return profile_doc

            else:
                raise ValueError("Either profile_id or user_id must be provided")

        except Exception as e:
            logger.error(f"[{self.name}] CV retrieval failed: {e}")
            raise

    async def store_session(
        self,
        session_id: str,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store session data

        Args:
            session_id: Session identifier
            session_data: Session state data

        Returns:
            Storage result
        """
        try:
            logger.info(f"[{self.name}] Storing session: {session_id}")

            # Add timestamps
            if "created_at" not in session_data:
                session_data["created_at"] = datetime.utcnow().isoformat()

            session_data["updated_at"] = datetime.utcnow().isoformat()

            # Store session
            session_file = self.sessions_dir / f"{session_id}.json"
            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)

            logger.info(f"[{self.name}] Stored session: {session_id}")

            return {
                "session_id": session_id,
                "uri": str(session_file),
                "success": True
            }

        except Exception as e:
            logger.error(f"[{self.name}] Session storage failed: {e}")
            raise

    async def retrieve_session(self, session_id: str) -> Dict[str, Any]:
        """
        Retrieve session data

        Args:
            session_id: Session identifier

        Returns:
            Session data
        """
        try:
            logger.info(f"[{self.name}] Retrieving session: {session_id}")

            session_file = self.sessions_dir / f"{session_id}.json"

            if not session_file.exists():
                raise FileNotFoundError(f"Session not found: {session_id}")

            with open(session_file, "r") as f:
                session_data = json.load(f)

            return session_data

        except Exception as e:
            logger.error(f"[{self.name}] Session retrieval failed: {e}")
            raise

    async def search_similar_cvs(
        self,
        query_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar CVs using vector similarity

        Args:
            query_text: Query text (e.g., job description)
            top_k: Number of results to return

        Returns:
            List of similar CV profiles
        """
        try:
            logger.info(f"[{self.name}] Searching for similar CVs")

            # Search vector DB
            search_result = self.vector_db.execute(
                operation="search",
                text=query_text,
                top_k=top_k,
                score_threshold=0.6
            )

            if not search_result["success"]:
                raise Exception(f"Vector search failed: {search_result['error']}")

            results = search_result["results"]

            # Retrieve full profiles for top matches
            similar_cvs = []
            for result in results:
                profile_id = result["document_id"]
                try:
                    profile = await self.retrieve_cv(profile_id=profile_id)
                    similar_cvs.append({
                        "profile": profile,
                        "similarity_score": result["score"]
                    })
                except Exception as e:
                    logger.warning(f"[{self.name}] Failed to retrieve profile {profile_id}: {e}")

            logger.info(f"[{self.name}] Found {len(similar_cvs)} similar CVs")

            return similar_cvs

        except Exception as e:
            logger.error(f"[{self.name}] Similarity search failed: {e}")
            raise

    def _cv_to_text(self, cv_data: Dict[str, Any]) -> str:
        """
        Convert CV data to text for embedding

        Args:
            cv_data: JSON Resume formatted CV

        Returns:
            Text representation
        """
        parts = []

        # Basics
        basics = cv_data.get("basics", {})
        if basics.get("name"):
            parts.append(f"Name: {basics['name']}")

        if basics.get("label"):
            parts.append(f"Title: {basics['label']}")

        if basics.get("summary"):
            parts.append(f"Summary: {basics['summary']}")

        # Work experience
        for work in cv_data.get("work", []):
            parts.append(f"Position: {work.get('position')} at {work.get('company') or work.get('name')}")
            if work.get("summary"):
                parts.append(work["summary"])

            for highlight in work.get("highlights", []):
                parts.append(highlight)

        # Education
        for edu in cv_data.get("education", []):
            parts.append(f"Education: {edu.get('studyType')} in {edu.get('area')} from {edu.get('institution')}")

        # Skills
        for skill in cv_data.get("skills", []):
            parts.append(f"Skills: {skill.get('name')}: {', '.join(skill.get('keywords', []))}")

        return "\n".join(parts)

    async def process(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Main processing entry point"""
        if operation == "store_cv":
            return await self.store_cv(**kwargs)
        elif operation == "retrieve_cv":
            return await self.retrieve_cv(**kwargs)
        elif operation == "store_session":
            return await self.store_session(**kwargs)
        elif operation == "retrieve_session":
            return await self.retrieve_session(**kwargs)
        elif operation == "search_similar":
            return await self.search_similar_cvs(**kwargs)
        else:
            raise ValueError(f"Unknown operation: {operation}")
