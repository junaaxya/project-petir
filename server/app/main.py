from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ingest.errors import IngestError
from app.ingest.router import router as ingest_router
from app.query.admin import router as admin_router
from app.query.health import router as health_router
from app.query.lightning import router as lightning_router
from app.query.system import router as system_router
from app.query.weather import router as weather_router
from app.settings import settings

def create_app() -> FastAPI:
    app = FastAPI(title="PetirDashboard API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(IngestError)
    async def _ingest_error_handler(_: Request, exc: IngestError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(HTTPException)
    async def _http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            code = str(detail.get("code", "HTTP_ERROR"))
            message = str(detail.get("message", ""))
        else:
            code = "HTTP_ERROR"
            message = str(detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": code, "message": message}},
        )

    app.include_router(ingest_router)
    app.include_router(weather_router)
    app.include_router(lightning_router)
    app.include_router(system_router)
    app.include_router(health_router)
    app.include_router(admin_router)
    return app

app = create_app()
