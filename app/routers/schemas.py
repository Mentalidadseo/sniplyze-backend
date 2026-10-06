"""Modelos de entrada de la API. La validación de fondo está en core/validation.py."""
from typing import Literal

from pydantic import BaseModel, Field


class Geo(BaseModel):
    location_code: int | None = Field(None, description="Por defecto 2724 (España)")
    language_code: str | None = Field(None, description="Por defecto 'es'")


class KeywordsIn(Geo):
    keywords: list[str] = Field(..., min_length=1)


class IntentIn(BaseModel):
    keywords: list[str] = Field(..., min_length=1)


class SeedIn(Geo):
    keyword: str
    limit: int | None = None


class RelatedIn(SeedIn):
    depth: int | None = Field(None, description="0–4")


class SuggestionsIn(SeedIn):
    exact_match: bool = False


class TargetIn(Geo):
    target: str


class TargetListIn(TargetIn):
    limit: int | None = None
    offset: int | None = None


class GapIn(Geo):
    target_1: str
    target_2: str
    intersections: bool = Field(True, description="true: keywords comunes; false: las de target_1 que no tiene target_2")
    limit: int | None = None


class TargetsIn(Geo):
    targets: list[str] = Field(..., min_length=1)


class BacklinkTargetIn(BaseModel):
    target: str
    limit: int | None = None


class BacklinksIn(BacklinkTargetIn):
    mode: Literal["as_is", "one_per_domain", "one_per_anchor"] = "one_per_domain"


class SerpIn(Geo):
    keyword: str
    depth: int | None = Field(None, description="Nº de resultados (10–200). Se factura por cada bloque de 10.")
    device: Literal["desktop", "mobile"] = "desktop"


class RankCheckIn(SerpIn):
    domain: str


class CrawlIn(BaseModel):
    target: str
    max_crawl_pages: int | None = Field(None, description="Páginas a rastrear (se factura por página)")
    start_url: str | None = None
    max_crawl_depth: int | None = None
    enable_javascript: bool = False
    load_resources: bool = False
    enable_browser_rendering: bool = False
    respect_sitemap: bool = False
    allow_subdomains: bool = False
    check_spell: bool = False


class UrlIn(BaseModel):
    url: str


class InstantIn(UrlIn):
    enable_javascript: bool = False


class LighthouseIn(UrlIn):
    for_mobile: bool = False
