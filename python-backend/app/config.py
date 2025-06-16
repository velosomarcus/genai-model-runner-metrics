"""
Configuration management for the GenAI Model Runner Metrics API.

This module handles loading configuration from environment variables
and provides application settings.
"""

import os
from functools import lru_cache
from .models import ConfigSettings


@lru_cache()
def get_settings() -> ConfigSettings:
    """
    Get application settings from environment variables.
    
    Uses LRU cache to ensure settings are loaded only once.
    
    Returns:
        ConfigSettings: Application configuration
    """
    return ConfigSettings(
        base_url=os.getenv("BASE_URL", ""),
        model=os.getenv("MODEL", ""),
        api_key=os.getenv("API_KEY", ""),
        tracing_enabled=os.getenv("TRACING_ENABLED", "false").lower() == "true",
        otlp_endpoint=os.getenv("OTLP_ENDPOINT", "jaeger:4318"),
        port=int(os.getenv("PORT", "8080")),
        metrics_port=int(os.getenv("METRICS_PORT", "9090"))
    )


def get_env_or_default(key: str, default: str) -> str:
    """
    Get environment variable or return default value.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        str: Environment variable value or default
    """
    return os.getenv(key, default)