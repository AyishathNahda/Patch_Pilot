"""Application setup, health check, and safe HTTP error responses."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from app import __version__
from app.config import Settings
from app.logging_config import configure_logging
from app.execution.routes import router as reproduction_router
from app.debugging.routes import router as debugging_router
from app.schemas import ErrorResponse
from app.execution.fixtures import router as fixture_router


class HealthResponse(BaseModel):
    service: str
    status: str
    version: str


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else Settings()
    logger = configure_logging(config.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        logger.info("API started")
        yield
        logger.info("API stopped")

    application = FastAPI(title="PatchPilot API", version=__version__, lifespan=lifespan,
                          responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
    application.add_middleware(
        CORSMiddleware, allow_origins=config.cors_origins, allow_credentials=False,
        allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
    )
    application.state.settings = config
    application.include_router(fixture_router)
    if config.environment == "development":
        application.include_router(reproduction_router)
        application.include_router(debugging_router)

    @application.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        return HealthResponse(service=config.service_name, status="ok", version=__version__)

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "http_error", "message": exc.detail}},
            headers=exc.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Avoid echoing potentially sensitive request input in validation errors.
        return JSONResponse(status_code=422, content={"error": {
            "code": "validation_error", "message": "Request validation failed",
        }})

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled request error", exc_info=(type(exc), exc, exc.__traceback__))
        return JSONResponse(status_code=500, content={"error": {
            "code": "internal_error", "message": "Internal server error",
        }})

    return application


app = create_app()
