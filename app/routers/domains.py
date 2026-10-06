from fastapi import APIRouter, Depends, Query

from app.deps import provider
from app.routers.schemas import GapIn, TargetIn, TargetListIn, TargetsIn

router = APIRouter(prefix="/api/domains", tags=["Dominios"])


def _geo(body):
    return {"location_code": body.location_code, "language_code": body.language_code}


@router.post("/overview", summary="Visión general: tráfico estimado, keywords y distribución de posiciones")
def overview(body: TargetIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.domain_overview(body.target, **_geo(body), confirm=confirm)


@router.post("/ranked-keywords", summary="Keywords por las que posiciona un dominio")
def ranked(body: TargetListIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.ranked_keywords(body.target, limit=body.limit, offset=body.offset, **_geo(body), confirm=confirm)


@router.post("/competitors", summary="Competidores orgánicos")
def competitors(body: TargetListIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.competitors(body.target, limit=body.limit, **_geo(body), confirm=confirm)


@router.post("/keyword-gap", summary="Keyword gap entre dos dominios")
def gap(body: GapIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.keyword_gap(body.target_1, body.target_2, intersections=body.intersections, limit=body.limit,
                         **_geo(body), confirm=confirm)


@router.post("/top-pages", summary="Páginas con más tráfico orgánico estimado")
def top_pages(body: TargetListIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.top_pages(body.target, limit=body.limit, **_geo(body), confirm=confirm)


@router.post("/history", summary="Evolución histórica de tráfico y keywords")
def history(body: TargetIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.rank_history(body.target, **_geo(body), confirm=confirm)


@router.post("/traffic", summary="Tráfico estimado de varios dominios a la vez")
def traffic(body: TargetsIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.bulk_traffic(body.targets, **_geo(body), confirm=confirm)
