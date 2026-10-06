from fastapi import APIRouter, Depends, Query

from app.deps import Container, container, provider

router = APIRouter(prefix="/api", tags=["Sistema"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/config", summary="Configuración visible (sin secretos)")
def config(c: Container = Depends(container)):
    s = c.settings
    return {
        "credentials_configured": s.has_credentials,
        "default_location_code": s.default_location_code,
        "default_language_code": s.default_language_code,
        "cost_confirm_threshold": s.cost_confirm_threshold,
        "confirm_unknown_cost": s.confirm_unknown_cost,
        "daily_budget": s.daily_budget,
        "max_keywords_per_request": s.max_keywords_per_request,
        "max_targets_per_request": s.max_targets_per_request,
        "max_crawl_pages": s.max_crawl_pages,
        "cache_enabled": s.cache_enabled,
    }


@router.get("/costs", summary="Gasto real registrado y ahorro por caché")
def costs(c: Container = Depends(container)):
    return c.ledger.summary()


@router.delete("/cache", summary="Vaciar la caché local")
def clear_cache(c: Container = Depends(container)):
    return {"deleted": c.cache.clear()}


@router.get("/account", summary="Saldo de la cuenta de DataForSEO")
def account(confirm: bool = Query(False), p=Depends(provider)):
    return p.account(confirm=confirm)
