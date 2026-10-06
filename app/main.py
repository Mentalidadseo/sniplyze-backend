"""Sniplyze: herramienta SEO sobre la API de DataForSEO.

Arranque: `uvicorn app.main:create_app --factory`
"""
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.core.errors import AppError
from app.deps import Container, build_container
from app.routers import audit, backlinks, domains, keywords, serp, system

STATIC_DIR = Path(__file__).parent / "static"


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = settings or get_settings()
    app = FastAPI(
        title="Sniplyze",
        description="Herramienta SEO sobre la API de DataForSEO. Todas las consultas de pago aceptan "
        "`?confirm=true` para autorizar consultas que superan el umbral de coste.",
        version="2.0.0",
    )
    app.state.container = container or build_container(settings)

    # Solo orígenes locales: la interfaz se sirve desde la propia app.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

    for r in (system, keywords, domains, backlinks, serp, audit):
        app.include_router(r.router)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    return app

