"""FastAPI application for API Extractor HTTP server."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_extractor.server.api import router
from api_extractor.server.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description=settings.api_description,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router)

    @app.on_event("startup")
    async def startup_event():
        """Startup event handler."""
        logger.info(f"Starting {settings.api_title} v{settings.api_version}")
        logger.info(f"Server listening on {settings.host}:{settings.port}")
        logger.info(f"API documentation: http://{settings.host}:{settings.port}/docs")

    @app.on_event("shutdown")
    async def shutdown_event():
        """Shutdown event handler."""
        logger.info("Shutting down API Extractor HTTP server")

    return app


# Create app instance
app = create_app()
