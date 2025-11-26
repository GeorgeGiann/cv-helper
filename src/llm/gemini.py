"""
Google Gemini LLM Provider
For Kaggle deployment with free Gemini Flash
"""

from typing import Optional, List
import logging

from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel, Part, Content
import vertexai

from .base import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider (via Vertex AI)"""

    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        project_id: Optional[str] = None,
        location: str = "us-central1",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ):
        """
        Initialize Gemini provider

        Args:
            model: Gemini model name (e.g., 'gemini-1.5-flash', 'gemini-1.5-pro')
            project_id: GCP project ID
            location: GCP region
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        super().__init__(model, temperature, max_tokens, **kwargs)

        self.project_id = project_id
        self.location = location

        # Initialize Vertex AI
        if project_id:
            vertexai.init(project=project_id, location=location)
        else:
            vertexai.init(location=location)

        self.model_instance = GenerativeModel(model)
        logger.info(f"Initialized Gemini provider: {model} in {location}")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using Gemini"""
        messages = []

        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))

        messages.append(LLMMessage(role="user", content=prompt))

        return await self.chat(messages, temperature, max_tokens, **kwargs)

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate chat response using Gemini"""
        try:
            # Convert messages to Gemini format
            gemini_contents = []
            system_instruction = None

            for msg in messages:
                if msg.role == "system":
                    # Gemini uses system_instruction parameter
                    system_instruction = msg.content
                else:
                    # Map roles: 'user' or 'model' (assistant)
                    role = "user" if msg.role == "user" else "model"
                    gemini_contents.append(
                        Content(role=role, parts=[Part.from_text(msg.content)])
                    )

            # Configure generation parameters
            generation_config = {
                "temperature": temperature or self.temperature,
                "max_output_tokens": max_tokens or self.max_tokens,
            }

            # Create chat session or generate
            if len(gemini_contents) == 1:
                # Single turn generation
                if system_instruction:
                    model = GenerativeModel(
                        self.model,
                        system_instruction=[system_instruction]
                    )
                else:
                    model = self.model_instance

                response = await model.generate_content_async(
                    gemini_contents[0].parts,
                    generation_config=generation_config,
                    **kwargs
                )
            else:
                # Multi-turn chat
                if system_instruction:
                    model = GenerativeModel(
                        self.model,
                        system_instruction=[system_instruction]
                    )
                else:
                    model = self.model_instance

                chat = model.start_chat(history=gemini_contents[:-1])
                response = await chat.send_message_async(
                    gemini_contents[-1].parts,
                    generation_config=generation_config,
                    **kwargs
                )

            # Extract text from response
            content = response.text if hasattr(response, "text") else ""

            # Extract token usage if available
            tokens_used = None
            if hasattr(response, "usage_metadata"):
                tokens_used = (
                    response.usage_metadata.prompt_token_count +
                    response.usage_metadata.candidates_token_count
                )

            return LLMResponse(
                content=content,
                model=self.model,
                tokens_used=tokens_used,
                finish_reason="stop",
                metadata={
                    "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, "usage_metadata") else None,
                    "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, "usage_metadata") else None,
                }
            )

        except Exception as e:
            logger.error(f"Gemini completion failed: {e}")
            raise

    def get_token_count(self, text: str) -> int:
        """
        Estimate token count for Gemini
        Gemini uses a similar tokenization approach
        """
        try:
            # Use Gemini's token counting (if available)
            model = GenerativeModel(self.model)
            token_count = model.count_tokens(text)
            return token_count.total_tokens
        except Exception as e:
            logger.warning(f"Token counting failed, using estimate: {e}")
            # Fallback to rough estimate
            return len(text) // 4
