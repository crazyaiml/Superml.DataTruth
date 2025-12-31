"""Configuration module."""

from src.config.settings import Settings, get_settings

# For backward compatibility, but prefer using get_settings()
settings = get_settings()

__all__ = ["Settings", "settings", "get_settings"]
