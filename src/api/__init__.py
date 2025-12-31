"""
API module.

FastAPI-based REST API for natural language analytics.
"""

from src.api.app import create_app, get_app

__all__ = ["create_app", "get_app"]
