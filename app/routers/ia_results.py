from fastapi import APIRouter
from typing import Optional
from app.services.analyzer import analizar_perplexity

router = APIRouter()

@router.get("/analizar/")
def analizar(keyword: str, dominio: Optional[str] = None):
    return analizar_perplexity(keyword, dominio)