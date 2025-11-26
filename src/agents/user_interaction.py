"""
User Interaction Agent
Collects missing information through conversational interface
"""

from typing import Dict, Any, Optional, List
import logging
import json

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


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

    async def collect_info(
        self,
        gaps: List[Dict[str, Any]],
        cv_data: Dict[str, Any],
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Collect missing information from user based on gaps

        This is a key A2A action called by the orchestrator

        Args:
            gaps: List of gaps from gap analysis
            cv_data: Current CV data
            conversation_history: Previous conversation messages

        Returns:
            Updated CV data with new information
        """
        try:
            logger.info(f"[{self.name}] Starting information collection for {len(gaps)} gaps")

            if conversation_history:
                self.conversation_history = conversation_history

            # For now, we'll simulate the interaction process
            # In a real implementation, this would be interactive
            updated_cv_data = cv_data.copy()

            # Process each gap and generate/collect responses
            for gap in gaps:
                if gap.get("priority") in ["critical", "high"]:
                    # In a real system, this would prompt the user
                    # For now, we'll use LLM to suggest potential content
                    suggestion = await self._suggest_response(gap, cv_data)

                    # Add suggestion to conversation history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": f"Question: {gap.get('description')}",
                        "gap_id": gap.get("id")
                    })

                    self.conversation_history.append({
                        "role": "system",
                        "content": f"Suggested response: {suggestion}",
                        "gap_id": gap.get("id")
                    })

            # Integrate collected information
            updated_cv_data = await self._integrate_responses(
                cv_data,
                gaps,
                self.conversation_history
            )

            result = {
                "updated_cv_data": updated_cv_data,
                "conversation_history": self.conversation_history,
                "gaps_addressed": len([g for g in gaps if g.get("priority") in ["critical", "high"]]),
                "total_gaps": len(gaps)
            }

            logger.info(f"[{self.name}] Collected information for {result['gaps_addressed']} gaps")

            return result

        except Exception as e:
            logger.error(f"[{self.name}] Information collection failed: {e}")
            raise

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
