from fastapi import APIRouter, Depends, Query

from app.deps import provider
from app.routers.schemas import IntentIn, KeywordsIn, RelatedIn, SuggestionsIn

router = APIRouter(prefix="/api/keywords", tags=["Keywords"])


@router.post("/volume", summary="Volumen de búsqueda, CPC y competencia (Google Ads)")
def volume(body: KeywordsIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.search_volume(body.keywords, location_code=body.location_code, language_code=body.language_code,
                           confirm=confirm)


@router.post("/related", summary="Keywords relacionadas (búsquedas relacionadas de Google)")
def related(body: RelatedIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.related_keywords(body.keyword, depth=body.depth, limit=body.limit, location_code=body.location_code,
                              language_code=body.language_code, confirm=confirm)


@router.post("/suggestions", summary="Sugerencias que contienen la keyword (long tail)")
def suggestions(body: SuggestionsIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.keyword_suggestions(body.keyword, limit=body.limit, exact_match=body.exact_match,
                                 location_code=body.location_code, language_code=body.language_code,
                                 confirm=confirm)


@router.post("/difficulty", summary="Dificultad de keywords (0–100)")
def difficulty(body: KeywordsIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.keyword_difficulty(body.keywords, location_code=body.location_code,
                                language_code=body.language_code, confirm=confirm)


@router.post("/intent", summary="Intención de búsqueda")
def intent(body: IntentIn, confirm: bool = Query(False), p=Depends(provider)):
    return p.search_intent(body.keywords, confirm=confirm)
