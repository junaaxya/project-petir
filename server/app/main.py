from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ingest.errors import IngestError
from app.ingest.router import router as ingest_router
from app.query.forecast import router as forecast_router
from app.query.admin import router as admin_router
from app.query.health import router as health_router
from app.query.lightning import router as lightning_router
from app.query.siren import router as siren_router
from app.query.system import router as system_router
from app.query.weather import router as weather_router
from app.settings import settings

def create_app() -> FastAPI:
    docs_enabled = settings.api_docs_enabled
    app = FastAPI(
        title="PetirDashboard API",
        version="1.0.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.exception_handler(IngestError)
    async def _ingest_error_handler(_: Request, exc: IngestError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(HTTPException)
    async def _http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        extra: dict[str, object] = {}
        if isinstance(detail, dict):
            code = str(detail.get("code", "HTTP_ERROR"))
            message = str(detail.get("message", ""))
            extra = {k: v for k, v in detail.items() if k not in {"code", "message"}}
        else:
            code = "HTTP_ERROR"
            message = str(detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message}, **extra},
        )

    app.include_router(ingest_router)
    app.include_router(weather_router)
    app.include_router(lightning_router)
    app.include_router(system_router)
    app.include_router(health_router)
    app.include_router(forecast_router)
    app.include_router(siren_router)
    app.include_router(admin_router)
    return app

app = create_app()
