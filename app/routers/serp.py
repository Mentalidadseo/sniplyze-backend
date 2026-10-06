from fastapi import APIRouter, Depends, Query

from app.deps import provider
from app.routers.schemas import RankCheckIn, SerpIn

router = APIRouter(prefix="/api/serp", tags=["SERP"])


@router.post("/organic", summary="Resultados orgánicos de Google en tiempo real")
def organic(body: SerpIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.serp_organic(body.keyword, depth=body.depth, device=body.device, location_code=body.location_code,
                          language_code=body.language_code, confirm=confirm)


@router.post("/rank-check", summary="Posición de un dominio para una keyword")
def rank_check(body: RankCheckIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.rank_check(body.keyword, body.domain, depth=body.depth, device=body.device,
                        location_code=body.location_code, language_code=body.language_code, confirm=confirm)
