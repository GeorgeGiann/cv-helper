"""
Ollama LLM Provider
For local development with free Ollama models
"""

from typing import Optional, List, Dict, Any
import aiohttp
import logging

from .base import LLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""

    def __init__(
        self,
        model: str = "llama3:8b",
        api_base: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ):
        """
        Initialize Ollama provider

        Args:
            model: Ollama model name (e.g., 'llama3:8b', 'mistral', 'codellama')
            api_base: Ollama API base URL
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
        """
        super().__init__(model, temperature, max_tokens, **kwargs)
        self.api_base = api_base.rstrip("/")
        logger.info(f"Initialized Ollama provider: {model} @ {api_base}")

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion using Ollama"""
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
        """Generate chat response using Ollama"""
        try:
            url = f"{self.api_base}/api/chat"

            # Convert messages to Ollama format
            ollama_messages = [
                {"role": msg.role, "content": msg.content}
                for msg in messages
            ]

            payload = {
                "model": self.model,
                "messages": ollama_messages,
                "stream": False,
                "options": {
                    "temperature": temperature or self.temperature,
                    "num_predict": max_tokens or self.max_tokens,
                }
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error: {error_text}")

                    data = await response.json()

            content = data.get("message", {}).get("content", "")

            return LLMResponse(
                content=content,
                model=self.model,
                tokens_used=None,  # Ollama doesn't return token count
                finish_reason="stop",
                metadata={
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "eval_count": data.get("eval_count"),
                }
            )

        except Exception as e:
            logger.error(f"Ollama completion failed: {e}")
            raise

    def get_token_count(self, text: str) -> int:
        """
        Estimate token count (rough approximation)
        Ollama doesn't provide a tokenizer, so we estimate
        """
        # Rough estimate: ~4 characters per token
        return len(text) // 4

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available Ollama models

        Returns:
            List of model information dictionaries
        """
        try:
            url = f"{self.api_base}/api/tags"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception("Failed to list models")

                    data = await response.json()
                    return data.get("models", [])

        except Exception as e:
            logger.error(f"List models failed: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama library

        Args:
            model_name: Name of model to pull

        Returns:
            True if successful
        """
        try:
            url = f"{self.api_base}/api/pull"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json={"name": model_name, "stream": False}
                ) as response:
                    if response.status != 200:
                        return False

                    logger.info(f"Successfully pulled model: {model_name}")
                    return True

        except Exception as e:
            logger.error(f"Pull model failed: {e}")
            return False
