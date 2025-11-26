"""
Anthropic Claude LLM Provider
For development with Claude models
"""

from typing import Optional, List
import logging

from anthropic import AsyncAnthropic

from .base import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM provider"""

    def __init__(
        self,
        model: str = "claude-3-5-haiku-20241022",
        api_key: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ):
        """
        Initialize Anthropic provider

        Args:
            model: Claude model name (e.g., 'claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022')
            api_key: Anthropic API key
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        super().__init__(model, temperature, max_tokens, **kwargs)

        if not api_key:
            raise ValueError("Anthropic API key is required")

        self.client = AsyncAnthropic(api_key=api_key)
        logger.info(f"Initialized Anthropic provider: {model}")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using Claude"""
        messages = [LLMMessage(role="user", content=prompt)]
        return await self.chat(
            messages,
            temperature,
            max_tokens,
            system=system_prompt,
            **kwargs
        )

    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate chat response using Claude"""
        try:
            # Convert messages to Anthropic format
            # Anthropic requires alternating user/assistant messages
            anthropic_messages = []
            system_message = None

            for msg in messages:
                if msg.role == "system":
                    # Anthropic uses separate system parameter
                    system_message = msg.content
                else:
                    anthropic_messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })

            # Use provided system or extracted system message
            final_system = system or system_message

            request_params = {
                "model": self.model,
                "messages": anthropic_messages,
                "temperature": temperature or self.temperature,
                "max_tokens": max_tokens or self.max_tokens,
                **kwargs
            }

            if final_system:
                request_params["system"] = final_system

            response = await self.client.messages.create(**request_params)

            # Extract text content from response
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            return LLMResponse(
                content=content,
                model=response.model,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens if response.usage else None,
                finish_reason=response.stop_reason,
                metadata={
                    "input_tokens": response.usage.input_tokens if response.usage else None,
                    "output_tokens": response.usage.output_tokens if response.usage else None,
                    "id": response.id,
                    "stop_sequence": response.stop_sequence,
                }
            )

        except Exception as e:
            logger.error(f"Anthropic completion failed: {e}")
            raise

    def get_token_count(self, text: str) -> int:
        """
        Estimate token count for Claude
        Claude uses a similar tokenization to GPT models
        """
        # Rough estimate: ~4 characters per token
        # For production, use the official Anthropic tokenizer
        return len(text) // 4

    async def count_tokens(self, text: str) -> int:
        """
        Get accurate token count from Anthropic API

        Args:
            text: Text to count tokens for

        Returns:
            Exact token count
        """
        try:
            response = await self.client.messages.count_tokens(
                model=self.model,
                messages=[{"role": "user", "content": text}]
            )
            return response.input_tokens
        except Exception as e:
            logger.warning(f"Token counting failed, using estimate: {e}")
            return self.get_token_count(text)
