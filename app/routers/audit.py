from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.deps import provider
from app.routers.schemas import CrawlIn, InstantIn, LighthouseIn

router = APIRouter(prefix="/api/audit", tags=["Auditoría técnica"])


@router.post("/crawls", summary="Lanzar un rastreo del sitio (On-Page)")
def start_crawl(body: CrawlIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.start_crawl(**body.model_dump(), confirm=confirm)


@router.get("/crawls", summary="Rastreos lanzados desde Sniplyze")
def list_crawls(p=Depends(provider)):
    return p.list_crawls()


@router.delete("/crawls/{task_id}", summary="Quitar un rastreo de la lista local")
def delete_crawl(task_id: str, p=Depends(provider)):
    p.delete_crawl(task_id)
    return {"deleted": task_id}


@router.get("/crawls/{task_id}/summary", summary="Resumen y progreso del rastreo")
def crawl_summary(task_id: str, confirm: bool = Query(False), p=Depends(provider)):
    return p.crawl_summary(task_id, confirm=confirm)


@router.get("/crawls/{task_id}/pages", summary="Páginas rastreadas (peor puntuación primero)")
def crawl_pages(task_id: str, limit: int | None = None, offset: int | None = None, only_issues: bool = False,
                confirm: bool = Query(False), p=Depends(provider)):
    return p.crawl_pages(task_id, limit=limit, offset=offset, only_issues=only_issues, confirm=confirm)


@router.get("/crawls/{task_id}/broken-links", summary="Enlaces rotos")
def broken_links(task_id: str, limit: int | None = None, offset: int | None = None,
                 confirm: bool = Query(False), p=Depends(provider)):
    return p.crawl_broken_links(task_id, limit=limit, offset=offset, confirm=confirm)


@router.get("/crawls/{task_id}/broken-resources", summary="Recursos con error (imágenes, CSS, JS)")
def broken_resources(task_id: str, limit: int | None = None, offset: int | None = None,
                     confirm: bool = Query(False), p=Depends(provider)):
    return p.crawl_broken_resources(task_id, limit=limit, offset=offset, confirm=confirm)


@router.get("/crawls/{task_id}/duplicates", summary="Titles o descriptions duplicados")
def duplicates(task_id: str, type: Literal["duplicate_title", "duplicate_description"] = "duplicate_title",
               limit: int | None = None, offset: int | None = None, confirm: bool = Query(False),
               p=Depends(provider)):
    return p.crawl_duplicate_tags(task_id, type, limit=limit, offset=offset, confirm=confirm)


@router.get("/crawls/{task_id}/redirect-chains", summary="Cadenas y bucles de redirección")
def redirect_chains(task_id: str, limit: int | None = None, offset: int | None = None,
                    confirm: bool = Query(False), p=Depends(provider)):
    return p.crawl_redirect_chains(task_id, limit=limit, offset=offset, confirm=confirm)


@router.get("/crawls/{task_id}/non-indexable", summary="Páginas no indexables y motivo")
def non_indexable(task_id: str, limit: int | None = None, offset: int | None = None,
                  confirm: bool = Query(False), p=Depends(provider)):
    return p.crawl_non_indexable(task_id, limit=limit, offset=offset, confirm=confirm)


@router.post("/page", summary="Análisis instantáneo de una URL")
def instant_page(body: InstantIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.instant_page(body.url, enable_javascript=body.enable_javascript, confirm=confirm)


@router.post("/lighthouse", summary="Lighthouse: rendimiento, accesibilidad, buenas prácticas y SEO")
def lighthouse(body: LighthouseIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.lighthouse(body.url, for_mobile=body.for_mobile, confirm=confirm)
