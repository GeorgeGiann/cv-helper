"""
Base LLM Provider Interface
Defines the contract for all LLM implementations
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """Represents a message in the conversation"""
    role: str  # 'system', 'user', 'assistant'
    content: str


@dataclass
class LLMResponse:
    """Represents a response from the LLM"""
    content: str
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ):
        """
        Initialize LLM provider

        Args:
            model: Model identifier
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            **kwargs: Provider-specific arguments
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.kwargs = kwargs

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a completion for a single prompt

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Override default temperature
            max_tokens: Override default max tokens
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse object
        """
        pass

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response for a conversation

        Args:
            messages: List of conversation messages
            temperature: Override default temperature
            max_tokens: Override default max tokens
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse object
        """
        pass

    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """
        Estimate token count for text

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        pass

    def get_provider_name(self) -> str:
        """Get the name of this provider"""
        return self.__class__.__name__.replace("Provider", "").lower()

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "provider": self.get_provider_name(),
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

    async def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a JSON response

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional arguments

        Returns:
            Parsed JSON dictionary
        """
        import json

        # Add JSON instruction to prompt
        json_prompt = f"{prompt}\n\nProvide your response as valid JSON."

        response = await self.complete(
            prompt=json_prompt,
            system_prompt=system_prompt,
            **kwargs
        )

        try:
            # Try to extract JSON from response
            content = response.content.strip()

            # Handle markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            return json.loads(content.strip())

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {response.content}")
            raise ValueError(f"LLM did not return valid JSON: {e}")
