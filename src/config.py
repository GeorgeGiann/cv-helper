"""
Configuration Factory
Creates storage and LLM providers based on environment configuration
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
import logging

from .storage import StorageBackend, LocalStorage, GCSStorage
from .llm import LLMProvider, OllamaProvider, OpenAIProvider, AnthropicProvider, GeminiProvider

logger = logging.getLogger(__name__)


class Config:
    """Application configuration"""

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration

        Args:
            env_file: Path to .env file (optional, uses environment variables if not provided)
        """
        if env_file:
            self._load_env_file(env_file)

        self.mode = os.getenv("MODE", "local")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        # Storage configuration
        self.storage_type = os.getenv("STORAGE_TYPE", "local")
        self.data_dir = os.getenv("DATA_DIR", "./data")
        self.gcs_bucket_uploads = os.getenv("GCS_BUCKET_UPLOADS")
        self.gcs_bucket_outputs = os.getenv("GCS_BUCKET_OUTPUTS")

        # LLM configuration
        self.llm_provider = os.getenv("LLM_PROVIDER", "ollama")
        self.llm_model = os.getenv("LLM_MODEL")
        self.llm_api_key = os.getenv("LLM_API_KEY")
        self.llm_api_base = os.getenv("LLM_API_BASE")
        self.llm_temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.llm_max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))

        # GCP configuration
        self.gcp_project_id = os.getenv("GCP_PROJECT_ID")
        self.gcp_region = os.getenv("GCP_REGION", "us-central1")

        # Vector DB configuration
        self.vector_db_type = os.getenv("VECTOR_DB_TYPE", "faiss")
        self.vector_db_path = os.getenv("VECTOR_DB_PATH", "./data/embeddings")

        # Firestore configuration
        self.firestore_database = os.getenv("FIRESTORE_DATABASE", "(default)")

        # ADK configuration
        self.adk_mode = os.getenv("ADK_MODE", "local")
        self.adk_host = os.getenv("ADK_HOST", "localhost")
        self.adk_port = int(os.getenv("ADK_PORT", "8000"))

        logger.info(f"Configuration loaded: mode={self.mode}, llm={self.llm_provider}, storage={self.storage_type}")

    def _load_env_file(self, env_file: str) -> None:
        """Load environment variables from file"""
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            logger.info(f"Loaded environment from: {env_file}")
        except ImportError:
            logger.warning("python-dotenv not installed, skipping .env file")
        except Exception as e:
            logger.error(f"Failed to load env file: {e}")

    def is_local(self) -> bool:
        """Check if running in local mode"""
        return self.mode == "local"

    def is_kaggle(self) -> bool:
        """Check if running in Kaggle mode"""
        return self.mode == "kaggle"

    def is_cloud(self) -> bool:
        """Check if running in cloud mode"""
        return self.mode in ["kaggle", "cloud"]

    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary"""
        return {
            "mode": self.mode,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "storage_type": self.storage_type,
            "vector_db_type": self.vector_db_type,
            "gcp_project_id": self.gcp_project_id,
            "gcp_region": self.gcp_region,
        }


def get_storage_backend(config: Optional[Config] = None) -> StorageBackend:
    """
    Create storage backend based on configuration

    Args:
        config: Configuration object (creates default if not provided)

    Returns:
        StorageBackend instance
    """
    if config is None:
        config = Config()

    if config.storage_type == "local":
        logger.info(f"Creating local storage backend: {config.data_dir}")
        return LocalStorage(base_dir=config.data_dir)

    elif config.storage_type == "gcs":
        if not config.gcs_bucket_uploads:
            raise ValueError("GCS_BUCKET_UPLOADS environment variable required for GCS storage")

        logger.info(f"Creating GCS storage backend: {config.gcs_bucket_uploads}")
        return GCSStorage(
            bucket_name=config.gcs_bucket_uploads,
            project_id=config.gcp_project_id
        )

    else:
        raise ValueError(f"Unknown storage type: {config.storage_type}")


def get_llm_provider(config: Optional[Config] = None) -> LLMProvider:
    """
    Create LLM provider based on configuration

    Args:
        config: Configuration object (creates default if not provided)

    Returns:
        LLMProvider instance
    """
    if config is None:
        config = Config()

    provider = config.llm_provider.lower()

    if provider == "ollama":
        model = config.llm_model or "llama3:8b"
        api_base = config.llm_api_base or "http://localhost:11434"

        logger.info(f"Creating Ollama provider: {model} @ {api_base}")
        return OllamaProvider(
            model=model,
            api_base=api_base,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
        )

    elif provider == "openai":
        if not config.llm_api_key:
            raise ValueError("LLM_API_KEY environment variable required for OpenAI")

        model = config.llm_model or "gpt-4o-mini"

        logger.info(f"Creating OpenAI provider: {model}")
        return OpenAIProvider(
            model=model,
            api_key=config.llm_api_key,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
        )

    elif provider == "anthropic":
        if not config.llm_api_key:
            raise ValueError("LLM_API_KEY environment variable required for Anthropic")

        model = config.llm_model or "claude-3-5-haiku-20241022"

        logger.info(f"Creating Anthropic provider: {model}")
        return AnthropicProvider(
            model=model,
            api_key=config.llm_api_key,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
        )

    elif provider == "gemini":
        model = config.llm_model or "gemini-1.5-flash"

        logger.info(f"Creating Gemini provider: {model}")
        return GeminiProvider(
            model=model,
            project_id=config.gcp_project_id,
            location=config.gcp_region,
            temperature=config.llm_temperature,
            max_tokens=config.llm_max_tokens,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def setup_logging(config: Optional[Config] = None) -> None:
    """
    Configure logging

    Args:
        config: Configuration object (creates default if not provided)
    """
    if config is None:
        config = Config()

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )

    logger.info(f"Logging configured: level={config.log_level}")


# Global configuration instance
_config_instance: Optional[Config] = None


def get_config(env_file: Optional[str] = None, force_reload: bool = False) -> Config:
    """
    Get global configuration instance

    Args:
        env_file: Path to .env file
        force_reload: Force reload configuration

    Returns:
        Config instance
    """
    global _config_instance

    if _config_instance is None or force_reload:
        _config_instance = Config(env_file=env_file)

    return _config_instance
