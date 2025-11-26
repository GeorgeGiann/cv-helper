"""
Orchestrator Agent
Master coordinator for the entire CV enhancement pipeline
"""

from typing import Dict, Any, Optional
import logging
import asyncio
from datetime import datetime
import uuid

from .base_agent import BaseAgent
from .cv_ingestion import CVIngestionAgent
from .job_understanding import JobUnderstandingAgent
from .user_interaction import UserInteractionAgent
from .knowledge_storage import KnowledgeStorageAgent
from .cv_generator import CVGeneratorAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """
    ADK Orchestrator Agent - Master Coordinator

    This agent demonstrates proper A2A (Agent-to-Agent) communication
    as required for the Google/Kaggle Agents Web Seminar.

    Responsibilities:
    - Supervises full workflow from CV upload to final generation
    - Performs Agent-to-Agent (A2A) communication
    - Manages session state and flow control
    - Handles error recovery and retries
    - Coordinates parallel operations when possible
    """

    def __init__(self, llm_provider=None, storage_backend=None, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="orchestrator",
            description="Master coordinator for CV enhancement pipeline with A2A communication",
            llm_provider=llm_provider,
            storage_backend=storage_backend,
            config=config
        )

        # Initialize all sub-agents
        logger.info(f"[{self.name}] Initializing sub-agents...")

        self.cv_ingestion_agent = CVIngestionAgent(
            llm_provider=llm_provider,
            storage_backend=storage_backend,
            config=config
        )

        self.job_understanding_agent = JobUnderstandingAgent(
            llm_provider=llm_provider,
            storage_backend=storage_backend,
            config=config
        )

        self.user_interaction_agent = UserInteractionAgent(
            llm_provider=llm_provider,
            storage_backend=storage_backend,
            config=config
        )

        self.knowledge_storage_agent = KnowledgeStorageAgent(
            llm_provider=llm_provider,
            storage_backend=storage_backend,
            config=config
        )

        self.cv_generator_agent = CVGeneratorAgent(
            llm_provider=llm_provider,
            storage_backend=storage_backend,
            config=config
        )

        # Register agents for A2A communication
        self._register_all_agents()

        logger.info(f"[{self.name}] All sub-agents initialized and registered")

    def _register_all_agents(self):
        """Register all agents with each other for A2A communication"""

        agents = [
            self.cv_ingestion_agent,
            self.job_understanding_agent,
            self.user_interaction_agent,
            self.knowledge_storage_agent,
            self.cv_generator_agent
        ]

        # Register orchestrator with all agents
        for agent in agents:
            self.register_agent(agent.name, agent)
            agent.register_agent(self.name, self)

        # Register agents with each other (full mesh)
        for agent in agents:
            for other_agent in agents:
                if agent != other_agent:
                    agent.register_agent(other_agent.name, other_agent)

        logger.info(f"[{self.name}] Registered {len(agents)} agents for A2A communication")

    async def process_cv_request(
        self,
        cv_file: str,
        job_ad: str,
        user_id: Optional[str] = None,
        job_source_type: str = "text"
    ) -> Dict[str, Any]:
        """
        Main entry point: Process complete CV enhancement pipeline

        This method demonstrates A2A communication across all agents.

        Args:
            cv_file: Path to CV PDF or text file
            job_ad: Job advertisement (text or URL)
            user_id: User identifier
            job_source_type: 'text' or 'url'

        Returns:
            Complete pipeline result with generated DOCX and JSON files
        """
        try:
            # Generate session ID
            session_id = f"session_{uuid.uuid4().hex[:8]}"
            user_id = user_id or f"user_{uuid.uuid4().hex[:8]}"

            logger.info(f"[{self.name}] ========================================")
            logger.info(f"[{self.name}] Starting CV Enhancement Pipeline")
            logger.info(f"[{self.name}] Session ID: {session_id}")
            logger.info(f"[{self.name}] User ID: {user_id}")
            logger.info(f"[{self.name}] ========================================")

            # Initialize session state
            session_state = {
                "session_id": session_id,
                "user_id": user_id,
                "status": "in_progress",
                "created_at": datetime.utcnow().isoformat(),
                "steps_completed": []
            }

            # ==============================================================
            # STEP 1: CV Ingestion (A2A Call)
            # ==============================================================
            logger.info(f"[{self.name}] Step 1: Calling CV Ingestion Agent via A2A...")

            cv_ingestion_result = await self.call_agent(
                agent="cv_ingestion",
                action="parse_cv",
                params={
                    "file_path": cv_file,
                    "user_id": user_id
                }
            )

            if not cv_ingestion_result["success"]:
                raise Exception(f"CV ingestion failed: {cv_ingestion_result['error']}")

            cv_data = cv_ingestion_result["data"]
            session_state["steps_completed"].append("cv_ingestion")
            session_state["cv_data"] = cv_data

            logger.info(f"[{self.name}] ✓ Step 1 Complete: CV parsed successfully")

            # ==============================================================
            # STEP 2: Job Understanding & Gap Analysis (A2A Call)
            # ==============================================================
            logger.info(f"[{self.name}] Step 2: Calling Job Understanding Agent via A2A...")

            gap_analysis_result = await self.call_agent(
                agent="job_understanding",
                action="analyze_gap",
                params={
                    "cv_data": cv_data["cv_data"],
                    "job_ad": job_ad,
                    "source_type": job_source_type
                }
            )

            if not gap_analysis_result["success"]:
                raise Exception(f"Gap analysis failed: {gap_analysis_result['error']}")

            gap_analysis = gap_analysis_result["data"]
            session_state["steps_completed"].append("gap_analysis")
            session_state["gap_analysis"] = gap_analysis

            logger.info(f"[{self.name}] ✓ Step 2 Complete: Found {len(gap_analysis['gaps'])} gaps ({gap_analysis['overallMatch']:.1f}% match)")

            # ==============================================================
            # STEP 3: User Interaction (A2A Call) - If gaps exist
            # ==============================================================
            if gap_analysis["hasGaps"] and len(gap_analysis["gaps"]) > 0:
                logger.info(f"[{self.name}] Step 3: Calling User Interaction Agent via A2A...")

                interaction_result = await self.call_agent(
                    agent="user_interaction",
                    action="collect_info",
                    params={
                        "gaps": gap_analysis["gaps"],
                        "cv_data": cv_data["cv_data"]
                    }
                )

                if interaction_result["success"]:
                    updated_cv_data = interaction_result["data"]["updated_cv_data"]
                    session_state["cv_data"]["cv_data"] = updated_cv_data
                    session_state["steps_completed"].append("user_interaction")

                    logger.info(f"[{self.name}] ✓ Step 3 Complete: Collected additional information")
                else:
                    logger.warning(f"[{self.name}] Step 3: User interaction had issues, continuing...")
            else:
                logger.info(f"[{self.name}] Step 3: Skipped (no gaps to address)")

            # ==============================================================
            # STEP 4: Store Knowledge (A2A Call)
            # ==============================================================
            logger.info(f"[{self.name}] Step 4: Calling Knowledge Storage Agent via A2A...")

            # Store CV profile
            storage_result = await self.call_agent(
                agent="knowledge_storage",
                action="store_cv",
                params={
                    "user_id": user_id,
                    "cv_data": session_state["cv_data"]["cv_data"],
                    "metadata": {
                        "session_id": session_id,
                        "job_match_score": gap_analysis["overallMatch"]
                    }
                }
            )

            if storage_result["success"]:
                profile_id = storage_result["data"]["profile_id"]
                session_state["profile_id"] = profile_id
                session_state["steps_completed"].append("knowledge_storage")

                logger.info(f"[{self.name}] ✓ Step 4 Complete: Stored CV profile: {profile_id}")

            # Store session
            session_storage_result = await self.call_agent(
                agent="knowledge_storage",
                action="store_session",
                params={
                    "session_id": session_id,
                    "session_data": session_state
                }
            )

            # ==============================================================
            # STEP 5: Generate Tailored CV (A2A Call)
            # ==============================================================
            logger.info(f"[{self.name}] Step 5: Calling CV Generator Agent via A2A...")

            generation_result = await self.call_agent(
                agent="cv_generator",
                action="generate",
                params={
                    "cv_data": session_state["cv_data"]["cv_data"],
                    "job_requirements": gap_analysis.get("job_data"),
                    "gap_analysis": gap_analysis,
                    "user_id": user_id
                }
            )

            if not generation_result["success"]:
                raise Exception(f"CV generation failed: {generation_result['error']}")

            generation_data = generation_result["data"]
            session_state["steps_completed"].append("cv_generation")
            session_state["output_files"] = generation_data["output_files"]
            session_state["status"] = "completed"

            logger.info(f"[{self.name}] ✓ Step 5 Complete: Generated CV files (DOCX + JSON)")

            # ==============================================================
            # Pipeline Complete
            # ==============================================================
            logger.info(f"[{self.name}] ========================================")
            logger.info(f"[{self.name}] Pipeline Complete!")
            logger.info(f"[{self.name}] Session ID: {session_id}")
            logger.info(f"[{self.name}] Steps: {' → '.join(session_state['steps_completed'])}")
            logger.info(f"[{self.name}] Match Score: {gap_analysis['overallMatch']:.1f}%")
            logger.info(f"[{self.name}] Output Files: {list(generation_data['output_files'].keys())}")
            logger.info(f"[{self.name}] ========================================")

            return {
                "session_id": session_id,
                "user_id": user_id,
                "status": "completed",
                "cv_data": session_state["cv_data"],
                "gap_analysis": gap_analysis,
                "output_files": generation_data["output_files"],
                "match_score": gap_analysis["overallMatch"],
                "steps_completed": session_state["steps_completed"]
            }

        except Exception as e:
            logger.error(f"[{self.name}] Pipeline failed: {e}", exc_info=True)

            return {
                "session_id": session_id if 'session_id' in locals() else None,
                "status": "failed",
                "error": str(e),
                "steps_completed": session_state.get("steps_completed", []) if 'session_state' in locals() else []
            }

    async def process(self, **kwargs) -> Dict[str, Any]:
        """Main processing entry point"""
        return await self.process_cv_request(**kwargs)
