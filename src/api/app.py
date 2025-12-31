"""
FastAPI Application

Main FastAPI application with middleware and configuration.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.rate_limit import RateLimitMiddleware

# Load configuration from database BEFORE any other imports that use settings
from src.config.loader import initialize_config
initialize_config()

# Now we can import modules that depend on settings
from src.api.routes import router
from src.api.vector_routes import router as vector_router
from src.api.setup import router as setup_router, is_setup_complete
from src.user.rls_config_api import router as rls_router
from src.api.rls_query_example import router as rls_query_router
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Initialize settings after config loaded from DB
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting DataTruth API...")
    yield
    # Shutdown
    logger.info("Shutting down DataTruth API...")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="DataTruth API",
        description="Natural language analytics over PostgreSQL",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production: specify allowed origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate Limiting Middleware
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=220,
        burst=250,
    )

    # Include routes
    app.include_router(setup_router, prefix="/api/setup", tags=["Setup"])
    app.include_router(router, prefix="/api/v1")
    app.include_router(vector_router)  # Already has /api/v1/vector prefix
    app.include_router(rls_router)  # RLS configuration endpoints
    app.include_router(rls_query_router)  # RLS query example endpoints

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "DataTruth API",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# Global app instance
_app: FastAPI = None


def get_app() -> FastAPI:
    """
    Get or create global FastAPI app instance.

    Returns:
        FastAPI app
    """
    global _app
    if _app is None:
        _app = create_app()
    return _app


# Create app for uvicorn
app = get_app()
