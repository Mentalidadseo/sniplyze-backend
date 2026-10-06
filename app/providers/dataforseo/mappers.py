"""Traducción de respuestas de DataForSEO a estructuras propias de Sniplyze.

Regla: si la API no devuelve un campo, el valor es `None`. Nunca se rellenan huecos.
Los nombres de campo de DataForSEO solo aparecen en este módulo y en provider.py.
"""
from typing import Any


def dig(obj: Any, *path: str | int) -> Any:
    for key in path:
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list) and isinstance(key, int):
            obj = obj[key] if -len(obj) <= key < len(obj) else None
        else:
            return None
        if obj is None:
            return None
    return obj


def items(result: dict) -> list[dict]:
    return [i for i in (result.get("items") or []) if isinstance(i, dict)]


def _monthly(raw: Any) -> list[dict] | None:
    if not isinstance(raw, list):
        return None
    return [
        {"year": m.get("year"), "month": m.get("month"), "search_volume": m.get("search_volume")}
        for m in raw
        if isinstance(m, dict)
    ]


# --- Keywords ---------------------------------------------------------------

def keyword_from_ads(item: dict) -> dict:
    """Elemento de keywords_data/google_ads/search_volume/live."""
    return {
        "keyword": item.get("keyword"),
        "search_volume": item.get("search_volume"),
        "cpc": item.get("cpc"),
        "competition": item.get("competition"),  # texto: LOW / MEDIUM / HIGH
        "competition_index": item.get("competition_index"),
        "low_top_of_page_bid": item.get("low_top_of_page_bid"),
        "high_top_of_page_bid": item.get("high_top_of_page_bid"),
        "monthly_searches": _monthly(item.get("monthly_searches")),
    }


def keyword_from_labs(kd: dict | None) -> dict:
    """Objeto `keyword_data` de DataForSEO Labs."""
    kd = kd or {}
    return {
        "keyword": kd.get("keyword"),
        "search_volume": dig(kd, "keyword_info", "search_volume"),
        "cpc": dig(kd, "keyword_info", "cpc"),
        "competition": dig(kd, "keyword_info", "competition"),  # número 0–1
        "competition_level": dig(kd, "keyword_info", "competition_level"),
        "keyword_difficulty": dig(kd, "keyword_properties", "keyword_difficulty"),
        "main_intent": dig(kd, "search_intent_info", "main_intent"),
        "se_results_count": dig(kd, "serp_info", "se_results_count"),
        "monthly_searches": _monthly(dig(kd, "keyword_info", "monthly_searches")),
    }


def related_item(item: dict) -> dict:
    return {**keyword_from_labs(item.get("keyword_data")), "depth": item.get("depth")}


def difficulty_item(item: dict) -> dict:
    return {"keyword": item.get("keyword"), "keyword_difficulty": item.get("keyword_difficulty")}


def intent_item(item: dict) -> dict:
    secondary = item.get("secondary_keyword_intents")
    return {
        "keyword": item.get("keyword"),
        "intent": dig(item, "keyword_intent", "label"),
        "probability": dig(item, "keyword_intent", "probability"),
        "secondary": [
            {"intent": s.get("label"), "probability": s.get("probability")}
            for s in secondary
            if isinstance(s, dict)
        ]
        if isinstance(secondary, list)
        else None,
    }


# --- Dominios ---------------------------------------------------------------

METRIC_KEYS = (
    "etv", "count", "estimated_paid_traffic_cost",
    "pos_1", "pos_2_3", "pos_4_10", "pos_11_20", "pos_21_30", "pos_31_40", "pos_41_50",
    "pos_51_60", "pos_61_70", "pos_71_80", "pos_81_90", "pos_91_100",
    "is_new", "is_up", "is_down", "is_lost",
)


def metrics(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    return {k: raw.get(k) for k in METRIC_KEYS}


def domain_overview(result: dict) -> dict:
    first = items(result)[0] if items(result) else {}
    return {
        "target": result.get("target"),
        "organic": metrics(dig(first, "metrics", "organic")),
        "paid": metrics(dig(first, "metrics", "paid")),
    }


def serp_position(element: dict | None) -> dict:
    element = element or {}
    return {
        "type": element.get("type"),
        "rank_group": element.get("rank_group"),
        "rank_absolute": element.get("rank_absolute"),
        "url": element.get("url"),
        "title": element.get("title"),
        "etv": element.get("etv"),
    }


def ranked_item(item: dict) -> dict:
    return {
        **keyword_from_labs(item.get("keyword_data")),
        "position": serp_position(dig(item, "ranked_serp_element", "serp_item")),
    }


def competitor_item(item: dict) -> dict:
    return {
        "domain": item.get("domain"),
        "avg_position": item.get("avg_position"),
        "sum_position": item.get("sum_position"),
        "intersections": item.get("intersections"),
        "intersection_organic": metrics(dig(item, "metrics", "organic")),
        "full_organic": metrics(dig(item, "full_domain_metrics", "organic")),
    }


def gap_item(item: dict) -> dict:
    return {
        **keyword_from_labs(item.get("keyword_data")),
        "target_1": serp_position(item.get("first_domain_serp_element")),
        "target_2": serp_position(item.get("second_domain_serp_element")),
    }


def page_item(item: dict) -> dict:
    return {"page": item.get("page_address"), "organic": metrics(dig(item, "metrics", "organic"))}


def history_item(item: dict) -> dict:
    return {
        "year": item.get("year"),
        "month": item.get("month"),
        "organic": metrics(dig(item, "metrics", "organic")),
        "paid": metrics(dig(item, "metrics", "paid")),
    }


def traffic_item(item: dict) -> dict:
    return {
        "target": item.get("target"),
        "organic_etv": dig(item, "metrics", "organic", "etv"),
        "organic_keywords": dig(item, "metrics", "organic", "count"),
        "paid_etv": dig(item, "metrics", "paid", "etv"),
        "paid_keywords": dig(item, "metrics", "paid", "count"),
        "featured_snippet_etv": dig(item, "metrics", "featured_snippet", "etv"),
        "local_pack_etv": dig(item, "metrics", "local_pack", "etv"),
    }


# --- Backlinks --------------------------------------------------------------

BACKLINK_SUMMARY_KEYS = (
    "target", "rank", "backlinks", "backlinks_spam_score", "crawled_pages", "first_seen", "lost_date",
    "internal_links_count", "external_links_count", "broken_backlinks", "broken_pages",
    "referring_domains", "referring_domains_nofollow", "referring_main_domains",
    "referring_main_domains_nofollow", "referring_ips", "referring_subnets",
    "referring_pages", "referring_pages_nofollow",
    "referring_links_tld", "referring_links_types", "referring_links_attributes",
    "referring_links_platform_types", "referring_links_semantic_locations", "referring_links_countries",
)


def backlinks_summary(result: dict) -> dict:
    out = {k: result.get(k) for k in BACKLINK_SUMMARY_KEYS}
    info = result.get("info") if isinstance(result.get("info"), dict) else {}
    out["info"] = {k: info.get(k) for k in ("server", "cms", "platform_type", "ip_address", "country",
                                            "target_spam_score")}
    return out


def backlink_item(item: dict) -> dict:
    keys = ("url_from", "domain_from", "url_to", "anchor", "dofollow", "item_type", "rank",
            "page_from_rank", "domain_from_rank", "page_from_title", "backlink_spam_score",
            "first_seen", "last_seen", "is_new", "is_lost", "is_broken", "url_to_status_code")
    return {k: item.get(k) for k in keys}


def referring_domain_item(item: dict) -> dict:
    keys = ("domain", "rank", "backlinks", "referring_pages", "backlinks_spam_score",
            "broken_backlinks", "first_seen", "lost_date")
    return {k: item.get(k) for k in keys}


def anchor_item(item: dict) -> dict:
    keys = ("anchor", "backlinks", "referring_domains", "referring_main_domains", "rank",
            "backlinks_spam_score", "first_seen", "lost_date")
    return {k: item.get(k) for k in keys}


# --- SERP -------------------------------------------------------------------

def serp(result: dict) -> dict:
    all_items = items(result)
    organic = [
        {
            "rank_group": i.get("rank_group"),
            "rank_absolute": i.get("rank_absolute"),
            "domain": i.get("domain"),
            "url": i.get("url"),
            "title": i.get("title"),
            "description": i.get("description"),
            "is_featured_snippet": i.get("is_featured_snippet"),
        }
        for i in all_items
        if i.get("type") == "organic"
    ]
    features: dict[str, int] = {}
    for i in all_items:
        t = i.get("type")
        if t and t != "organic":
            features[t] = features.get(t, 0) + 1
    return {
        "keyword": result.get("keyword"),
        "check_url": result.get("check_url"),
        "datetime": result.get("datetime"),
        "se_results_count": result.get("se_results_count"),
        "item_types": result.get("item_types"),
        "features": features,
        "organic": organic,
    }


def domain_matches(serp_domain: str | None, target: str) -> bool:
    if not serp_domain:
        return False
    d = serp_domain.lower().strip(".")
    if d.startswith("www."):
        d = d[4:]
    return d == target or d.endswith("." + target)


# --- Auditoría On-Page ------------------------------------------------------

# Traducciones orientativas de las comprobaciones On-Page. La clave original de
# DataForSEO se muestra siempre; si una clave no está aquí, se muestra tal cual.
CHECK_LABELS = {
    "is_4xx_code": "Error 4xx",
    "is_5xx_code": "Error 5xx",
    "is_broken": "Página rota",
    "is_redirect": "Redirección",
    "redirect_chain": "Cadena de redirecciones",
    "no_title": "Sin title",
    "title_too_long": "Title demasiado largo",
    "title_too_short": "Title demasiado corto",
    "duplicate_title_tag": "Varias etiquetas title",
    "no_description": "Sin meta description",
    "no_h1_tag": "Sin H1",
    "no_image_alt": "Imágenes sin alt",
    "no_image_title": "Imágenes sin title",
    "no_favicon": "Sin favicon",
    "no_doctype": "Sin doctype",
    "no_encoding_meta_tag": "Sin meta de codificación",
    "no_content_encoding": "Sin compresión",
    "high_loading_time": "Carga lenta",
    "high_waiting_time": "Tiempo de espera alto",
    "large_page_size": "Página pesada",
    "size_greater_than_3mb": "Página > 3 MB",
    "low_content_rate": "Poco contenido respecto al código",
    "low_character_count": "Poco texto",
    "low_readability_rate": "Legibilidad baja",
    "irrelevant_title": "Title poco relevante",
    "irrelevant_description": "Description poco relevante",
    "deprecated_html_tags": "Etiquetas HTML obsoletas",
    "duplicate_meta_tags": "Meta etiquetas duplicadas",
    "https_to_http_links": "Enlaces de HTTPS a HTTP",
    "is_http": "Página en HTTP",
    "has_render_blocking_resources": "Recursos que bloquean el renderizado",
    "has_meta_refresh_redirect": "Redirección por meta refresh",
    "is_orphan_page": "Página huérfana",
    "has_links_to_redirects": "Enlaces a redirecciones",
    "is_link_relation_conflict": "Conflicto de rel en enlaces",
    "recursive_canonical": "Canonical recursivo",
    "canonical_chain": "Cadena de canonicals",
    "canonical_to_redirect": "Canonical a redirección",
    "canonical_to_broken": "Canonical a página rota",
    "has_misspelling": "Faltas de ortografía",
    "lorem_ipsum": "Texto lorem ipsum",
    "frame": "Usa frames",
    "flash": "Usa Flash",
    # Comprobaciones informativas (true suele ser bueno):
    "is_https": "Página en HTTPS",
    "has_html_doctype": "Tiene doctype",
    "canonical": "Tiene canonical",
    "seo_friendly_url": "URL amigable",
    "is_www": "Usa www",
}

INFORMATIONAL_CHECKS = {
    "is_https", "has_html_doctype", "canonical", "is_www", "meta_charset_consistency",
    "seo_friendly_url", "seo_friendly_url_characters_check", "seo_friendly_url_dynamic_check",
    "seo_friendly_url_keywords_check", "seo_friendly_url_relative_length_check",
}


def check_entry(key: str, value: Any) -> dict:
    return {
        "check": key,
        "label": CHECK_LABELS.get(key),
        "informational": key in INFORMATIONAL_CHECKS,
        "value": value,
    }


def checks_counts(raw: Any) -> list[dict]:
    """`page_metrics.checks` (resumen): nº de páginas por comprobación, de mayor a menor."""
    if not isinstance(raw, dict):
        return []
    rows = [check_entry(k, v) for k, v in raw.items() if isinstance(v, (int, float)) and v > 0]
    return sorted(rows, key=lambda r: (r["informational"], -r["value"]))


def failed_checks(raw: Any) -> list[str]:
    """`checks` de una página: claves a true que no son informativas."""
    if not isinstance(raw, dict):
        return []
    return [k for k, v in raw.items() if v is True and k not in INFORMATIONAL_CHECKS]


def crawl_summary(result: dict) -> dict:
    page_metrics = result.get("page_metrics") if isinstance(result.get("page_metrics"), dict) else {}
    domain_info = result.get("domain_info") if isinstance(result.get("domain_info"), dict) else {}
    pm_keys = ("onpage_score", "links_internal", "links_external", "duplicate_title", "duplicate_description",
               "duplicate_content", "broken_links", "broken_resources", "links_relation_conflict",
               "redirect_loop", "non_indexable")
    di_keys = ("name", "cms", "ip", "server", "crawl_start", "crawl_end", "total_pages", "main_domain",
               "page_not_found_status_code", "canonicalization_status_code", "www_redirect_status_code")
    return {
        "crawl_progress": result.get("crawl_progress"),
        "crawl_status": result.get("crawl_status"),
        "crawl_stop_reason": result.get("crawl_stop_reason"),
        "domain_info": {k: domain_info.get(k) for k in di_keys},
        "ssl_info": domain_info.get("ssl_info"),
        "site_checks": [check_entry(k, v) for k, v in (domain_info.get("checks") or {}).items()],
        "page_metrics": {k: page_metrics.get(k) for k in pm_keys},
        "issues": checks_counts(page_metrics.get("checks")),
    }


def crawl_page(item: dict) -> dict:
    meta = item.get("meta") if isinstance(item.get("meta"), dict) else {}
    h1 = dig(meta, "htags", "h1")
    return {
        "url": item.get("url"),
        "status_code": item.get("status_code"),
        "resource_type": item.get("resource_type"),
        "onpage_score": item.get("onpage_score"),
        "click_depth": item.get("click_depth"),
        "title": meta.get("title"),
        "title_length": meta.get("title_length"),
        "description": meta.get("description"),
        "description_length": meta.get("description_length"),
        "h1": h1 if isinstance(h1, list) else None,
        "canonical": meta.get("canonical"),
        "internal_links_count": meta.get("internal_links_count"),
        "external_links_count": meta.get("external_links_count"),
        "inbound_links_count": meta.get("inbound_links_count"),
        "images_count": meta.get("images_count"),
        "words_count": dig(meta, "content", "plain_text_word_count"),
        "size": item.get("size"),
        "duration_time": dig(item, "page_timing", "duration_time"),
        "largest_contentful_paint": dig(item, "page_timing", "largest_contentful_paint"),
        "broken_links": item.get("broken_links"),
        "broken_resources": item.get("broken_resources"),
        "duplicate_title": item.get("duplicate_title"),
        "duplicate_description": item.get("duplicate_description"),
        "duplicate_content": item.get("duplicate_content"),
        "failed_checks": failed_checks(item.get("checks")),
        "checks": item.get("checks"),
    }


def crawl_link(item: dict) -> dict:
    keys = ("type", "link_from", "link_to", "page_to_status_code", "direction", "dofollow", "is_broken", "text")
    return {k: item.get(k) for k in keys}


def crawl_resource(item: dict) -> dict:
    keys = ("url", "resource_type", "status_code", "size", "fetch_time")
    return {k: item.get(k) for k in keys}


def duplicate_group(item: dict) -> dict:
    pages = item.get("pages") if isinstance(item.get("pages"), list) else []
    return {
        "value": item.get("accumulator"),
        "total_count": item.get("total_count"),
        "pages": [p.get("url") for p in pages if isinstance(p, dict)],
    }


def redirect_chain(item: dict) -> dict:
    chain = item.get("chain") if isinstance(item.get("chain"), list) else []
    return {
        "is_redirect_loop": item.get("is_redirect_loop"),
        "chain": [
            {"from": c.get("link_from"), "to": c.get("link_to"), "status_code": c.get("page_to_status_code")}
            for c in chain
            if isinstance(c, dict)
        ],
    }


def non_indexable(item: dict) -> dict:
    return {"url": item.get("url"), "reason": item.get("reason")}


LIGHTHOUSE_AUDITS = (
    "first-contentful-paint", "largest-contentful-paint", "total-blocking-time",
    "cumulative-layout-shift", "speed-index", "interactive",
)


def lighthouse(result: dict) -> dict:
    """Resultado de Lighthouse (formato estándar de Lighthouse)."""
    cats = result.get("categories") if isinstance(result.get("categories"), dict) else {}
    audits = result.get("audits") if isinstance(result.get("audits"), dict) else {}
    scores = {}
    for key, cat in cats.items():
        score = cat.get("score") if isinstance(cat, dict) else None
        scores[key] = round(score * 100) if isinstance(score, (int, float)) else None
    metrics_out = {}
    for key in LIGHTHOUSE_AUDITS:
        a = audits.get(key) if isinstance(audits.get(key), dict) else {}
        metrics_out[key] = {
            "title": a.get("title"),
            "display_value": a.get("displayValue"),
            "numeric_value": a.get("numericValue"),
            "score": a.get("score"),
        }
    opportunities = [
        {"id": k, "title": a.get("title"), "display_value": a.get("displayValue"), "score": a.get("score")}
        for k, a in audits.items()
        if isinstance(a, dict) and dig(a, "details", "type") == "opportunity"
        and isinstance(a.get("score"), (int, float)) and a["score"] < 0.9
    ]
    return {
        "requested_url": result.get("requestedUrl"),
        "final_url": result.get("finalUrl"),
        "lighthouse_version": result.get("lighthouseVersion"),
        "scores": scores,
        "metrics": metrics_out,
        "opportunities": opportunities,
    }
