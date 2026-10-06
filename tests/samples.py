"""Respuestas de ejemplo con la estructura de la especificación OpenAPI de DataForSEO v3.

Los valores son inventados para tests; algunos campos se omiten a propósito para
comprobar que la app los deja vacíos (None) en lugar de rellenarlos.
"""

MONTHLY = [{"year": 2026, "month": 8, "search_volume": 1300}, {"year": 2026, "month": 9, "search_volume": 1600}]

SEARCH_VOLUME = [
    {"keyword": "zapatillas running", "spell": None, "location_code": 2724, "language_code": "es",
     "search_partners": False, "competition": "HIGH", "competition_index": 100, "search_volume": 14800,
     "low_top_of_page_bid": 0.21, "high_top_of_page_bid": 0.9, "cpc": 0.55, "monthly_searches": MONTHLY},
    # Keyword sin datos en Google Ads: la API devuelve nulos.
    {"keyword": "keyword rara", "competition": None, "competition_index": None, "search_volume": None,
     "cpc": None, "monthly_searches": None},
]


def keyword_data(kw, volume=1000, kd=40, intent="commercial"):
    return {
        "se_type": "google", "keyword": kw, "location_code": 2724, "language_code": "es",
        "keyword_info": {"competition": 0.8, "competition_level": "HIGH", "cpc": 0.4, "search_volume": volume,
                         "monthly_searches": MONTHLY},
        "keyword_properties": {"keyword_difficulty": kd, "core_keyword": None},
        "search_intent_info": {"main_intent": intent, "foreign_intent": None},
        "serp_info": {"se_results_count": 123000},
    }


RELATED = [{
    "se_type": "google", "seed_keyword": "zapatillas running", "seed_keyword_data": keyword_data("zapatillas running"),
    "location_code": 2724, "language_code": "es", "total_count": 2, "items_count": 2,
    "items": [
        {"se_type": "google", "keyword_data": keyword_data("zapatillas running mujer", 2400), "depth": 1,
         "related_keywords": ["a", "b"]},
        {"se_type": "google", "keyword_data": {"keyword": "sin metricas"}, "depth": 2, "related_keywords": None},
    ],
}]

SUGGESTIONS = [{
    "se_type": "google", "seed_keyword": "zapatillas", "seed_keyword_data": None, "total_count": 1, "items_count": 1,
    "offset": 0, "offset_token": "tok", "items": [keyword_data("zapatillas baratas", 5400, 30, "transactional")],
}]

DIFFICULTY = [{"se_type": "google", "total_count": 2, "items_count": 2, "items": [
    {"se_type": "google", "keyword": "a", "keyword_difficulty": 12},
    {"se_type": "google", "keyword": "b", "keyword_difficulty": None},
]}]

INTENT = [{"items_count": 1, "items": [{
    "keyword": "comprar zapatillas",
    "keyword_intent": {"label": "transactional", "probability": 0.9},
    "secondary_keyword_intents": [{"label": "commercial", "probability": 0.4}],
}]}]

METRICS = {"pos_1": 10, "pos_2_3": 20, "pos_4_10": 50, "pos_11_20": 60, "etv": 1234.5, "count": 500,
           "estimated_paid_traffic_cost": 800.0, "is_new": 5, "is_up": 7, "is_down": 3, "is_lost": 2}

DOMAIN_OVERVIEW = [{"se_type": "google", "target": "ejemplo.com", "total_count": 1, "items_count": 1, "items": [
    {"se_type": "google", "location_code": 2724, "language_code": "es", "metrics": {"organic": METRICS, "paid": None}},
]}]


def organic_element(url, rank=3):
    return {"type": "organic", "se_type": "google", "rank_group": rank, "rank_absolute": rank + 1,
            "domain": "www.ejemplo.com", "title": "Título", "url": url, "etv": 12.5}


RANKED = [{"se_type": "google", "target": "ejemplo.com", "total_count": 500, "items_count": 1,
           "metrics": {"organic": METRICS}, "metrics_absolute": None, "items": [
               {"se_type": "google", "keyword_data": keyword_data("zapatillas"),
                "ranked_serp_element": {"se_type": "google", "serp_item": organic_element("https://www.ejemplo.com/z")}},
           ]}]

COMPETITORS = [{"se_type": "google", "target": "ejemplo.com", "total_count": 1, "items_count": 1, "items": [
    {"se_type": "google", "domain": "rival.com", "avg_position": 12.3, "sum_position": 1000, "intersections": 80,
     "full_domain_metrics": {"organic": METRICS}, "metrics": {"organic": {"etv": 100.0, "count": 80}},
     "competitor_metrics": None},
]}]

GAP = [{"se_type": "google", "target_1": "a.com", "target_2": "b.com", "total_count": 1, "items_count": 1, "items": [
    {"se_type": "google", "keyword_data": keyword_data("kw comun"),
     "first_domain_serp_element": organic_element("https://a.com/x", 2),
     "second_domain_serp_element": organic_element("https://b.com/y", 7)},
]}]

TOP_PAGES = [{"se_type": "google", "target": "ejemplo.com", "total_count": 1, "items_count": 1, "items": [
    {"se_type": "google", "page_address": "https://ejemplo.com/", "metrics": {"organic": METRICS}},
]}]

HISTORY = [{"se_type": "google", "target": "ejemplo.com", "total_count": 2, "items_count": 2, "items": [
    {"se_type": "google", "year": 2026, "month": 8, "metrics": {"organic": METRICS}},
    {"se_type": "google", "year": 2026, "month": 9, "metrics": {"organic": {**METRICS, "etv": 1500.0}}},
]}]

TRAFFIC = [{"se_type": "google", "location_code": 2724, "language_code": "es", "total_count": 2, "items_count": 2,
            "items": [
                {"se_type": "google", "target": "a.com",
                 "metrics": {"organic": {"etv": 10.5, "count": 3}, "paid": {"etv": 1.0, "count": 1}}},
                {"se_type": "google", "target": "b.com", "metrics": {"organic": {"etv": 2.0, "count": 1}}},
            ]}]

BACKLINKS_SUMMARY = [{
    "target": "ejemplo.com", "first_seen": "2019-01-01 00:00:00 +00:00", "rank": 350, "backlinks": 12000,
    "backlinks_spam_score": 4, "crawled_pages": 900, "info": {"server": "nginx", "cms": None, "country": "ES"},
    "broken_backlinks": 30, "broken_pages": 5, "referring_domains": 800, "referring_domains_nofollow": 100,
    "referring_main_domains": 700, "referring_ips": 650, "referring_subnets": 500, "referring_pages": 9000,
    "referring_links_tld": {"es": 500, "com": 300}, "referring_links_attributes": {"nofollow": 1200},
    "referring_links_countries": {"ES": 600},
}]

BACKLINKS = [{"target": "ejemplo.com", "mode": "one_per_domain", "total_count": 1, "items_count": 1, "items": [
    {"type": "backlink", "domain_from": "blog.com", "url_from": "https://blog.com/post", "url_to": "https://ejemplo.com/",
     "anchor": "ejemplo", "dofollow": True, "rank": 100, "domain_from_rank": 400, "first_seen": "2025-01-01",
     "is_lost": False, "is_broken": False, "backlink_spam_score": 1},
]}]

REFERRING_DOMAINS = [{"target": "ejemplo.com", "total_count": 1, "items_count": 1, "items": [
    {"type": "backlinks_referring_domain", "domain": "blog.com", "rank": 400, "backlinks": 3,
     "first_seen": "2025-01-01", "lost_date": None, "backlinks_spam_score": 1},
]}]

ANCHORS = [{"target": "ejemplo.com", "total_count": 1, "items_count": 1, "items": [
    {"type": "backlinks_anchor", "anchor": "ejemplo", "backlinks": 40, "referring_domains": 20, "rank": 200},
]}]

SERP = [{
    "keyword": "zapatillas running", "type": "organic", "se_domain": "google.es", "location_code": 2724,
    "language_code": "es", "check_url": "https://www.google.es/search?q=zapatillas+running",
    "datetime": "2026-10-06 10:00:00 +00:00", "item_types": ["organic", "people_also_ask"],
    "se_results_count": 1000000, "items_count": 4,
    "items": [
        {"type": "organic", "rank_group": 1, "rank_absolute": 1, "domain": "www.rival.com", "url": "https://www.rival.com/",
         "title": "Rival", "description": "d"},
        {"type": "people_also_ask", "rank_group": 1, "rank_absolute": 2},
        {"type": "organic", "rank_group": 2, "rank_absolute": 3, "domain": "tienda.ejemplo.com",
         "url": "https://tienda.ejemplo.com/z", "title": "Ejemplo", "description": None},
        {"type": "organic", "rank_group": 3, "rank_absolute": 4, "domain": "noejemplo.com",
         "url": "https://noejemplo.com/", "title": "Falso positivo"},
    ],
}]

TASK_ID = "07131248-1535-0216-1000-17384017ad04"

CRAWL_SUMMARY = [{
    "crawl_progress": "finished",
    "crawl_status": {"max_crawl_pages": 100, "pages_in_queue": 0, "pages_crawled": 87},
    "crawl_stop_reason": "empty_queue",
    "domain_info": {"name": "ejemplo.com", "cms": "WordPress", "ip": "1.2.3.4", "server": "nginx",
                    "total_pages": 87, "checks": {"sitemap": True, "robots_txt": True, "ssl": True},
                    "ssl_info": {"valid_certificate": True}},
    "page_metrics": {"links_external": 120, "links_internal": 900, "duplicate_title": 4, "duplicate_description": 6,
                     "duplicate_content": 1, "broken_links": 3, "broken_resources": 2, "links_relation_conflict": 0,
                     "redirect_loop": 0, "onpage_score": 88.5, "non_indexable": 5,
                     "checks": {"no_h1_tag": 7, "title_too_long": 12, "is_https": 87, "no_image_alt": 0}},
}]

PAGE = {
    "resource_type": "html", "status_code": 200, "url": "https://ejemplo.com/a", "size": 50000,
    "onpage_score": 72.0, "click_depth": 2, "broken_links": False, "duplicate_title": True,
    "meta": {"title": "A", "title_length": 1, "description": None, "htags": {"h1": ["Hola"], "h2": []},
             "internal_links_count": 10, "inbound_links_count": 3, "content": {"plain_text_word_count": 320}},
    "page_timing": {"duration_time": 450},
    "checks": {"no_description": True, "title_too_short": True, "is_https": True, "no_h1_tag": False},
}

CRAWL_PAGES = [{"crawl_progress": "finished", "crawl_status": None, "total_items_count": 87, "items_count": 1,
                "items": [PAGE]}]

CRAWL_LINKS = [{"crawl_progress": "finished", "total_items_count": 1, "items_count": 1, "items": [
    {"type": "anchor", "link_from": "https://ejemplo.com/a", "link_to": "https://ejemplo.com/roto",
     "page_to_status_code": 404, "direction": "internal", "dofollow": True, "is_broken": True, "text": "aquí"},
]}]

CRAWL_DUPLICATES = [{"crawl_progress": "finished", "total_pages_count": 2, "pages_count": 2, "items_count": 1, "items": [
    {"accumulator": "Inicio", "total_count": 2, "pages": [{"url": "https://ejemplo.com/"}, {"url": "https://ejemplo.com/?p=1"}]},
]}]

CRAWL_REDIRECTS = [{"crawl_progress": "finished", "total_items_count": 1, "items_count": 1, "items": [
    {"is_redirect_loop": False, "chain": [
        {"type": "redirect", "link_from": "http://ejemplo.com/", "link_to": "https://ejemplo.com/", "page_to_status_code": 301},
        {"type": "redirect", "link_from": "https://ejemplo.com/", "link_to": "https://ejemplo.com/es/", "page_to_status_code": 302},
    ]},
]}]

CRAWL_NON_INDEXABLE = [{"crawl_progress": "finished", "total_items_count": 1, "items_count": 1, "items": [
    {"reason": "meta_tag", "url": "https://ejemplo.com/privado"},
]}]

INSTANT = [{"crawl_progress": "finished", "crawl_status": None, "items_count": 1, "items": [PAGE]}]

LIGHTHOUSE = [{
    "requestedUrl": "https://ejemplo.com/", "finalUrl": "https://ejemplo.com/", "lighthouseVersion": "12.0.0",
    "categories": {"performance": {"score": 0.73}, "seo": {"score": 1}, "accessibility": {"score": None}},
    "audits": {
        "largest-contentful-paint": {"title": "Largest Contentful Paint", "displayValue": "3.1 s",
                                     "numericValue": 3100, "score": 0.6},
        "render-blocking-resources": {"title": "Eliminate render-blocking resources", "displayValue": "Ahorro 400 ms",
                                      "score": 0.5, "details": {"type": "opportunity"}},
        "uses-text-compression": {"title": "Compresión", "score": 1, "details": {"type": "opportunity"}},
    },
}]

USER_DATA = [{"login": "x", "timezone": "UTC", "money": {"total": 100.0, "balance": 42.5}, "rates": {}, "price": {}}]
