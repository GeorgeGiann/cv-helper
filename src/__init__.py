"""
CV-Enhancer Multi-Agent System
Google/Kaggle Agents Web Seminar Project
"""

__version__ = "1.0.0"

from .config import Config, get_config, get_storage_backend, get_llm_provider, setup_logging

__all__ = [
    "Config",
    "get_config",
    "get_storage_backend",
    "get_llm_provider",
    "setup_logging",
]
