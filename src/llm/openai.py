"""
OpenAI LLM Provider
For development with OpenAI models
"""

from typing import Optional, List
import logging

from openai import AsyncOpenAI
import tiktoken

from .base import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider"""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ):
        """
        Initialize OpenAI provider

        Args:
            model: OpenAI model name (e.g., 'gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo')
            api_key: OpenAI API key
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        super().__init__(model, temperature, max_tokens, **kwargs)

        if not api_key:
            raise ValueError("OpenAI API key is required")

        self.client = AsyncOpenAI(api_key=api_key)

        # Initialize tokenizer for token counting
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            # Fallback to cl100k_base for newer models
            self.encoding = tiktoken.get_encoding("cl100k_base")

        logger.info(f"Initialized OpenAI provider: {model}")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using OpenAI"""
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
        """Generate chat response using OpenAI"""
        try:
            # Convert messages to OpenAI format
            openai_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs
            )

            choice = response.choices[0]
            content = choice.message.content or ""

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                finish_reason=choice.finish_reason,
                metadata={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                    "completion_tokens": response.usage.completion_tokens if response.usage else None,
                    "id": response.id,
                }
            )

        except Exception as e:
            logger.error(f"OpenAI completion failed: {e}")
            raise

    def get_token_count(self, text: str) -> int:
        """Get accurate token count using tiktoken"""
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed, using estimate: {e}")
            # Fallback to rough estimate
            return len(text) // 4
