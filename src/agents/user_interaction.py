"""
User Interaction Agent
Collects missing information through conversational interface
"""

from typing import Dict, Any, Optional, List
import logging
import json
import sys
import os

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


def is_interactive_environment() -> bool:
    """
    Detect if running in an interactive environment

    Returns:
        True if interactive (terminal), False if non-interactive (Kaggle/cloud)
    """
    # Check if running in Jupyter/Colab/Kaggle notebook
    try:
        from IPython import get_ipython
        if get_ipython() is not None:
            return True  # Jupyter is interactive
    except ImportError:
        pass

    # Check if stdin is a terminal
    if hasattr(sys.stdin, 'isatty') and sys.stdin.isatty():
        return True

    # Check environment variables
    if os.getenv('KAGGLE_KERNEL_RUN_TYPE') or os.getenv('CI'):
        return False

    return False


class UserInteractionAgent(BaseAgent):
    """
    ADK Agent for user interaction and information collection

    Responsibilities:
    - Ask clarifying questions based on gap analysis
    - Collect missing information from user
    - Validate and normalize user responses
    - Integrate updates into session memory
    - Handle multi-turn conversations
    """

    def __init__(self, llm_provider=None, storage_backend=None, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name="user_interaction",
            description="Collects missing information through conversational interaction",
            llm_provider=llm_provider,
            storage_backend=storage_backend,
            config=config
        )

        self.conversation_history: List[Dict[str, str]] = []

        # Get interaction mode from config or environment variable
        # Priority: 1. config parameter, 2. env var, 3. default to non-interactive
        if config and "interactive_mode" in config:
            self.interactive_mode = config.get("interactive_mode")
        else:
            # Check environment variable (default: non-interactive for safety)
            env_mode = os.getenv("USER_INTERACTION_MODE", "non-interactive")
            self.interactive_mode = env_mode

        # Validate mode
        if self.interactive_mode not in ["interactive", "non-interactive"]:
            logger.warning(f"[{self.name}] Invalid mode '{self.interactive_mode}', defaulting to non-interactive")
            self.interactive_mode = "non-interactive"

        logger.info(f"[{self.name}] Running in {self.interactive_mode} mode")

    async def collect_info(
        self,
        gaps: List[Dict[str, Any]],
        cv_data: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_questions: int = 5
    ) -> Dict[str, Any]:
        """
        Collect missing information from user based on gaps

        This is a key A2A action called by the orchestrator

        Args:
            gaps: List of gaps from gap analysis
            cv_data: Current CV data
            conversation_history: Previous conversation messages
            max_questions: Maximum number of questions to ask (default: 5)

        Returns:
            Updated CV data with new information
        """
        try:
            logger.info(f"[{self.name}] Starting information collection for {len(gaps)} gaps")
            logger.info(f"[{self.name}] Mode: {self.interactive_mode}")

            if conversation_history:
                self.conversation_history = conversation_history

            updated_cv_data = cv_data.copy()

            # Filter and prioritize gaps
            priority_gaps = sorted(
                [g for g in gaps if g.get("priority") in ["critical", "high"]],
                key=lambda x: 0 if x.get("priority") == "critical" else 1
            )[:max_questions]

            if not priority_gaps:
                logger.info(f"[{self.name}] No high-priority gaps to address")
                return {
                    "updated_cv_data": updated_cv_data,
                    "conversation_history": self.conversation_history,
                    "gaps_addressed": 0,
                    "total_gaps": len(gaps)
                }

            # Choose interaction mode
            if self.interactive_mode == "interactive":
                updated_cv_data = await self._interactive_collection(
                    priority_gaps, cv_data
                )
            else:
                updated_cv_data = await self._non_interactive_collection(
                    priority_gaps, cv_data
                )

            result = {
                "updated_cv_data": updated_cv_data,
                "conversation_history": self.conversation_history,
                "gaps_addressed": len(priority_gaps),
                "total_gaps": len(gaps),
                "mode": self.interactive_mode
            }

            logger.info(f"[{self.name}] Collected information for {result['gaps_addressed']} gaps")

            return result

        except Exception as e:
            logger.error(f"[{self.name}] Information collection failed: {e}")
            raise

    async def _interactive_collection(
        self,
        gaps: List[Dict[str, Any]],
        cv_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Interactive mode: Ask questions via terminal/Jupyter

        Args:
            gaps: Priority gaps to address
            cv_data: Current CV data

        Returns:
            Updated CV data
        """
        updated_cv = cv_data.copy()

        print("\n" + "=" * 70)
        print("📝 CV Enhancement - Additional Information Needed")
        print("=" * 70)
        print("\nI've identified some gaps between your CV and the job requirements.")
        print("Please answer the following questions to enhance your CV:\n")

        for i, gap in enumerate(gaps, 1):
            print(f"\n[Question {i}/{len(gaps)}]")
            print(f"Priority: {gap.get('priority', 'medium').upper()}")
            print(f"Topic: {gap.get('category', 'general')}")
            print(f"\n{gap.get('description', 'No description')}")

            # Show suggestion if available
            suggestion = await self._suggest_response(gap, cv_data)
            if suggestion:
                print(f"\n💡 Suggestion: {suggestion}")

            print("\n➤ Your answer (or press Enter to skip): ")

            try:
                # Get user input
                answer = input().strip()

                if answer:
                    # Record conversation
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": gap.get('description'),
                        "gap_id": gap.get("id"),
                        "priority": gap.get("priority")
                    })

                    self.conversation_history.append({
                        "role": "user",
                        "content": answer,
                        "gap_id": gap.get("id")
                    })

                    # Extract and integrate information
                    extracted = await self._extract_structured_info(answer, gap.get("id"))
                    updated_cv = await self._update_cv_data(updated_cv, extracted)

                    print("✅ Information recorded!")
                else:
                    print("⏭️  Skipped")

            except (EOFError, KeyboardInterrupt):
                print("\n\n⚠️  Input interrupted. Using suggested responses for remaining questions.")
                break

        print("\n" + "=" * 70)
        print("✅ Information collection complete!")
        print("=" * 70 + "\n")

        return updated_cv

    async def _non_interactive_collection(
        self,
        gaps: List[Dict[str, Any]],
        cv_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Non-interactive mode: Use LLM to infer/suggest responses

        Args:
            gaps: Priority gaps to address
            cv_data: Current CV data

        Returns:
            Updated CV data
        """
        updated_cv = cv_data.copy()

        logger.info(f"[{self.name}] Non-interactive mode: Using LLM to infer responses")

        for gap in gaps:
            # Generate suggested response
            suggestion = await self._suggest_response(gap, cv_data)

            # Record conversation
            self.conversation_history.append({
                "role": "assistant",
                "content": f"Question: {gap.get('description')}",
                "gap_id": gap.get("id"),
                "priority": gap.get("priority")
            })

            self.conversation_history.append({
                "role": "system",
                "content": f"Auto-response (inferred): {suggestion}",
                "gap_id": gap.get("id")
            })

            # Extract and integrate if LLM suggested something useful
            if suggestion and not suggestion.startswith("No direct experience"):
                extracted = await self._extract_structured_info(suggestion, gap.get("id"))
                updated_cv = await self._update_cv_data(updated_cv, extracted)

        logger.info(f"[{self.name}] Processed {len(gaps)} gaps in non-interactive mode")

        return updated_cv

    async def ask_question(
        self,
        question: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Ask a single question to the user

        Args:
            question: Question dictionary with id, question text, etc.
            context: Optional context about CV and job

        Returns:
            Formatted question for the user
        """
        question_text = question.get("question", "")
        priority = question.get("priority", "medium")

        # Format question with priority indicator
        if priority == "critical":
            formatted = f"⚠️ IMPORTANT: {question_text}"
        elif priority == "high":
            formatted = f"❗ {question_text}"
        else:
            formatted = question_text

        self.conversation_history.append({
            "role": "assistant",
            "content": formatted,
            "question_id": question.get("id"),
            "gap_id": question.get("gapId")
        })

        logger.info(f"[{self.name}] Asked question: {question.get('id')}")

        return formatted

    async def process_answer(
        self,
        question_id: str,
        answer: str,
        cv_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process user's answer and update CV data

        Args:
            question_id: Question identifier
            answer: User's response
            cv_data: Current CV data

        Returns:
            Updated CV data
        """
        try:
            logger.info(f"[{self.name}] Processing answer for question: {question_id}")

            # Add answer to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": answer,
                "question_id": question_id
            })

            # Use LLM to extract structured information from answer
            extracted_info = await self._extract_structured_info(answer, question_id)

            # Update CV data with extracted information
            updated_cv_data = await self._update_cv_data(cv_data, extracted_info)

            return {
                "updated_cv_data": updated_cv_data,
                "extracted_info": extracted_info,
                "question_id": question_id
            }

        except Exception as e:
            logger.error(f"[{self.name}] Answer processing failed: {e}")
            raise

    async def _suggest_response(
        self,
        gap: Dict[str, Any],
        cv_data: Dict[str, Any]
    ) -> str:
        """
        Use LLM to suggest potential response based on existing CV data

        Args:
            gap: Gap information
            cv_data: Current CV data

        Returns:
            Suggested response
        """
        if not self.llm_provider:
            return f"Please provide information about: {gap.get('description')}"

        prompt = f"""Based on this person's CV background, suggest a possible response to address this gap.

Gap: {gap.get('description')}
Category: {gap.get('category')}
Priority: {gap.get('priority')}

CV Summary:
- Name: {cv_data.get('basics', {}).get('name')}
- Experience: {len(cv_data.get('work', []))} positions
- Education: {len(cv_data.get('education', []))} entries
- Skills: {', '.join([s.get('name', '') for s in cv_data.get('skills', [])[:5]])}

Suggest a brief, realistic response (2-3 sentences) that this person might provide.
If they likely don't have this experience, suggest "No direct experience with [topic], but willing to learn."
"""

        try:
            response = await self.llm_provider.complete(
                prompt=prompt,
                temperature=0.5,
                max_tokens=150
            )

            return response.content.strip()

        except Exception as e:
            logger.error(f"[{self.name}] Suggestion generation failed: {e}")
            return f"Please describe your experience with: {gap.get('description')}"

    async def _extract_structured_info(
        self,
        answer: str,
        question_id: str
    ) -> Dict[str, Any]:
        """
        Extract structured information from user's answer

        Args:
            answer: User's free-text response
            question_id: Question identifier

        Returns:
            Structured information
        """
        if not self.llm_provider:
            return {"raw_answer": answer, "question_id": question_id}

        prompt = f"""Extract structured information from this answer.

Answer: {answer}

Extract in JSON format:
{{
  "category": "skill/experience/project/education/certification",
  "item": {{
    "name": "...",
    "description": "...",
    "keywords": ["..."],
    "dates": {{"start": "...", "end": "..."}},
    "relevance": "high/medium/low"
  }},
  "confidence": 0.9  // 0-1 how confident the extraction is
}}

Return ONLY valid JSON."""

        try:
            response = await self.llm_provider.complete_json(
                prompt=prompt,
                temperature=0.2,
                max_tokens=512
            )

            return response

        except Exception as e:
            logger.error(f"[{self.name}] Info extraction failed: {e}")
            return {"raw_answer": answer, "question_id": question_id}

    async def _integrate_responses(
        self,
        cv_data: Dict[str, Any],
        gaps: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Integrate collected responses into CV data

        Args:
            cv_data: Original CV data
            gaps: List of gaps
            conversation_history: Conversation messages

        Returns:
            Updated CV data
        """
        # For simulation, return original CV data
        # In real implementation, would parse answers and update CV

        updated_cv = cv_data.copy()

        # Extract user answers from conversation
        user_answers = [
            msg for msg in conversation_history
            if msg.get("role") == "user"
        ]

        logger.info(f"[{self.name}] Integrating {len(user_answers)} responses into CV")

        # In a real implementation, this would use LLM to intelligently
        # merge new information into the existing CV structure

        return updated_cv

    async def _update_cv_data(
        self,
        cv_data: Dict[str, Any],
        extracted_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update CV data with extracted information

        Args:
            cv_data: Current CV data
            extracted_info: Extracted structured information

        Returns:
            Updated CV data
        """
        updated_cv = cv_data.copy()

        category = extracted_info.get("category")
        item = extracted_info.get("item", {})

        # Add to appropriate section
        if category == "skill" and item.get("name"):
            if "skills" not in updated_cv:
                updated_cv["skills"] = []

            updated_cv["skills"].append({
                "name": item.get("name"),
                "keywords": item.get("keywords", [])
            })

        elif category == "project" and item.get("name"):
            if "projects" not in updated_cv:
                updated_cv["projects"] = []

            updated_cv["projects"].append({
                "name": item.get("name"),
                "description": item.get("description"),
                "keywords": item.get("keywords", [])
            })

        # Add to other sections as needed...

        return updated_cv

    async def process(self, **kwargs) -> Dict[str, Any]:
        """Main processing entry point"""
        return await self.collect_info(**kwargs)
