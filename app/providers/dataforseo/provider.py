"""Implementación de `SEOProvider` sobre la API v3 de DataForSEO."""
import json
import math
import re
import time
from typing import Any

from app.config import Settings
from app.core.db import Database
from app.core.errors import InputError, NotFound, ProviderError
from app.core.validation import (
    clamp_int,
    clean_domain,
    clean_domains,
    clean_keyword,
    clean_keywords,
    clean_language_code,
    clean_location_code,
    clean_url,
)
from app.providers.dataforseo import mappers as m
from app.providers.dataforseo.client import ApiResult, DataForSEOClient, Endpoint

DAY = 86_400

EP = {
    # Keywords
    "search_volume": Endpoint("keywords_data/google_ads/search_volume/live", ttl=30 * DAY),
    "related_keywords": Endpoint("dataforseo_labs/google/related_keywords/live", ttl=30 * DAY),
    "keyword_suggestions": Endpoint("dataforseo_labs/google/keyword_suggestions/live", ttl=30 * DAY),
    "keyword_difficulty": Endpoint("dataforseo_labs/google/bulk_keyword_difficulty/live", ttl=30 * DAY),
    "search_intent": Endpoint("dataforseo_labs/google/search_intent/live", ttl=30 * DAY),
    # Dominios
    "domain_overview": Endpoint("dataforseo_labs/google/domain_rank_overview/live", ttl=7 * DAY),
    "ranked_keywords": Endpoint("dataforseo_labs/google/ranked_keywords/live", ttl=7 * DAY),
    "competitors": Endpoint("dataforseo_labs/google/competitors_domain/live", ttl=7 * DAY),
    "keyword_gap": Endpoint("dataforseo_labs/google/domain_intersection/live", ttl=7 * DAY),
    "top_pages": Endpoint("dataforseo_labs/google/relevant_pages/live", ttl=7 * DAY),
    "rank_history": Endpoint("dataforseo_labs/google/historical_rank_overview/live", ttl=7 * DAY),
    "bulk_traffic": Endpoint("dataforseo_labs/google/bulk_traffic_estimation/live", ttl=7 * DAY),
    # Backlinks
    "backlinks_summary": Endpoint("backlinks/summary/live", ttl=7 * DAY),
    "backlinks": Endpoint("backlinks/backlinks/live", ttl=7 * DAY),
    "referring_domains": Endpoint("backlinks/referring_domains/live", ttl=7 * DAY),
    "anchors": Endpoint("backlinks/anchors/live", ttl=7 * DAY),
    # SERP
    "serp_organic": Endpoint("serp/google/organic/live/advanced", ttl=1 * DAY),
    # On-Page
    "crawl_post": Endpoint("on_page/task_post"),
    "crawl_summary": Endpoint("on_page/summary/{id}", method="GET"),
    "crawl_pages": Endpoint("on_page/pages"),
    "crawl_links": Endpoint("on_page/links"),
    "crawl_resources": Endpoint("on_page/resources"),
    "crawl_duplicate_tags": Endpoint("on_page/duplicate_tags"),
    "crawl_redirect_chains": Endpoint("on_page/redirect_chains"),
    "crawl_non_indexable": Endpoint("on_page/non_indexable"),
    "instant_pages": Endpoint("on_page/instant_pages", ttl=1 * DAY),
    "lighthouse": Endpoint("on_page/lighthouse/live/json", ttl=1 * DAY),
    # Cuenta
    "user_data": Endpoint("appendix/user_data", method="GET"),
}

_TASK_ID = re.compile(r"^[0-9A-Za-z-]{8,64}$")
DUPLICATE_TAG_TYPES = {"duplicate_title", "duplicate_description"}


def _resp(api: ApiResult, data: Any) -> dict:
    return {"data": data, "meta": api.meta()}


class DataForSEOProvider:
    def __init__(self, client: DataForSEOClient, settings: Settings, db: Database):
        self.client = client
        self.s = settings
        self.db = db

    # --- utilidades ---------------------------------------------------------

    def _geo(self, location_code: int | None, language_code: str | None) -> dict:
        return {
            "location_code": clean_location_code(location_code, self.s.default_location_code),
            "language_code": clean_language_code(language_code, self.s.default_language_code),
        }

    def _limit(self, limit: int | None, default: int = 100) -> int:
        return clamp_int("limit", limit, default=min(default, self.s.max_limit), minimum=1, maximum=self.s.max_limit)

    def _offset(self, offset: int | None) -> int:
        return clamp_int("offset", offset, default=0, minimum=0, maximum=2_000_000)

    def _keywords(self, keywords: list[str]) -> list[str]:
        return clean_keywords(keywords, max_count=self.s.max_keywords_per_request)

    @staticmethod
    def _task_id(task_id: str) -> str:
        if not isinstance(task_id, str) or not _TASK_ID.match(task_id):
            raise InputError("Identificador de rastreo no válido.")
        return task_id

    # --- keywords -----------------------------------------------------------

    def search_volume(self, keywords, *, location_code=None, language_code=None, confirm=False):
        kws = self._keywords(keywords)
        payload = {"keywords": kws, **self._geo(location_code, language_code)}
        api = self.client.call(EP["search_volume"], payload, units=len(kws), confirm=confirm)
        return _resp(api, [m.keyword_from_ads(i) for i in api.result if isinstance(i, dict)])

    def related_keywords(self, keyword, *, depth=None, limit=None, location_code=None, language_code=None,
                         confirm=False):
        lim = self._limit(limit)
        payload = {
            "keyword": clean_keyword(keyword),
            **self._geo(location_code, language_code),
            "depth": clamp_int("depth", depth, default=1, minimum=0, maximum=4),
            "limit": lim,
            "include_seed_keyword": True,
        }
        api = self.client.call(EP["related_keywords"], payload, units=lim, confirm=confirm)
        r = api.first
        return _resp(api, {
            "seed": m.keyword_from_labs(r.get("seed_keyword_data")) if r.get("seed_keyword_data") else None,
            "total_count": r.get("total_count"),
            "items": [m.related_item(i) for i in m.items(r)],
        })

    def keyword_suggestions(self, keyword, *, limit=None, exact_match=False, location_code=None,
                            language_code=None, confirm=False):
        lim = self._limit(limit)
        payload = {
            "keyword": clean_keyword(keyword),
            **self._geo(location_code, language_code),
            "limit": lim,
            "exact_match": bool(exact_match),
            "include_seed_keyword": True,
        }
        api = self.client.call(EP["keyword_suggestions"], payload, units=lim, confirm=confirm)
        r = api.first
        return _resp(api, {
            "seed": m.keyword_from_labs(r.get("seed_keyword_data")) if r.get("seed_keyword_data") else None,
            "total_count": r.get("total_count"),
            "items": [m.keyword_from_labs(i) for i in m.items(r)],
        })

    def keyword_difficulty(self, keywords, *, location_code=None, language_code=None, confirm=False):
        kws = self._keywords(keywords)
        payload = {"keywords": kws, **self._geo(location_code, language_code)}
        api = self.client.call(EP["keyword_difficulty"], payload, units=len(kws), confirm=confirm)
        return _resp(api, [m.difficulty_item(i) for i in m.items(api.first)])

    def search_intent(self, keywords, *, confirm=False):
        kws = self._keywords(keywords)
        api = self.client.call(EP["search_intent"], {"keywords": kws}, units=len(kws), confirm=confirm)
        return _resp(api, [m.intent_item(i) for i in m.items(api.first)])

    # --- dominios -----------------------------------------------------------

    def domain_overview(self, target, *, location_code=None, language_code=None, confirm=False):
        payload = {"target": clean_domain(target), **self._geo(location_code, language_code)}
        api = self.client.call(EP["domain_overview"], payload, confirm=confirm)
        return _resp(api, m.domain_overview(api.first))

    def ranked_keywords(self, target, *, limit=None, offset=None, location_code=None, language_code=None,
                        confirm=False):
        lim = self._limit(limit)
        payload = {
            "target": clean_domain(target),
            **self._geo(location_code, language_code),
            "limit": lim,
            "offset": self._offset(offset),
            "order_by": ["keyword_data.keyword_info.search_volume,desc"],
        }
        api = self.client.call(EP["ranked_keywords"], payload, units=lim, confirm=confirm)
        r = api.first
        return _resp(api, {
            "total_count": r.get("total_count"),
            "organic": m.metrics(m.dig(r, "metrics", "organic")),
            "items": [m.ranked_item(i) for i in m.items(r)],
        })

    def competitors(self, target, *, limit=None, location_code=None, language_code=None, confirm=False):
        lim = self._limit(limit, 50)
        payload = {
            "target": clean_domain(target),
            **self._geo(location_code, language_code),
            "limit": lim,
            "exclude_top_domains": True,
        }
        api = self.client.call(EP["competitors"], payload, units=lim, confirm=confirm)
        r = api.first
        return _resp(api, {"total_count": r.get("total_count"), "items": [m.competitor_item(i) for i in m.items(r)]})

    def keyword_gap(self, target_1, target_2, *, intersections=True, limit=None, location_code=None,
                    language_code=None, confirm=False):
        t1, t2 = clean_domain(target_1), clean_domain(target_2)
        if t1 == t2:
            raise InputError("Los dos dominios deben ser distintos.")
        lim = self._limit(limit)
        payload = {
            "target_1": t1,
            "target_2": t2,
            **self._geo(location_code, language_code),
            "intersections": bool(intersections),
            "limit": lim,
            "order_by": ["keyword_data.keyword_info.search_volume,desc"],
        }
        api = self.client.call(EP["keyword_gap"], payload, units=lim, confirm=confirm)
        r = api.first
        return _resp(api, {"total_count": r.get("total_count"), "items": [m.gap_item(i) for i in m.items(r)]})

    def top_pages(self, target, *, limit=None, location_code=None, language_code=None, confirm=False):
        lim = self._limit(limit)
        payload = {
            "target": clean_domain(target),
            **self._geo(location_code, language_code),
            "limit": lim,
            "order_by": ["metrics.organic.etv,desc"],
        }
        api = self.client.call(EP["top_pages"], payload, units=lim, confirm=confirm)
        r = api.first
        return _resp(api, {"total_count": r.get("total_count"), "items": [m.page_item(i) for i in m.items(r)]})

    def rank_history(self, target, *, location_code=None, language_code=None, confirm=False):
        payload = {"target": clean_domain(target), **self._geo(location_code, language_code)}
        api = self.client.call(EP["rank_history"], payload, confirm=confirm)
        return _resp(api, [m.history_item(i) for i in m.items(api.first)])

    def bulk_traffic(self, targets, *, location_code=None, language_code=None, confirm=False):
        doms = clean_domains(targets, max_count=self.s.max_targets_per_request)
        payload = {"targets": doms, **self._geo(location_code, language_code)}
        api = self.client.call(EP["bulk_traffic"], payload, units=len(doms), confirm=confirm)
        return _resp(api, [m.traffic_item(i) for i in m.items(api.first)])

    # --- backlinks ----------------------------------------------------------

    def backlinks_summary(self, target, *, confirm=False):
        payload = {"target": clean_domain(target), "internal_list_limit": 10}
        api = self.client.call(EP["backlinks_summary"], payload, confirm=confirm)
        return _resp(api, m.backlinks_summary(api.first))

    def backlinks(self, target, *, limit=None, mode="one_per_domain", confirm=False):
        if mode not in {"as_is", "one_per_domain", "one_per_anchor"}:
            raise InputError("mode debe ser as_is, one_per_domain u one_per_anchor.")
        lim = self._limit(limit)
        payload = {"target": clean_domain(target), "limit": lim, "mode": mode, "order_by": ["rank,desc"]}
        api = self.client.call(EP["backlinks"], payload, units=lim, confirm=confirm)
        r = api.first
        return _resp(api, {"total_count": r.get("total_count"), "items": [m.backlink_item(i) for i in m.items(r)]})

    def referring_domains(self, target, *, limit=None, confirm=False):
        lim = self._limit(limit)
        payload = {"target": clean_domain(target), "limit": lim, "order_by": ["rank,desc"]}
        api = self.client.call(EP["referring_domains"], payload, units=lim, confirm=confirm)
        r = api.first
        return _resp(api, {"total_count": r.get("total_count"),
                           "items": [m.referring_domain_item(i) for i in m.items(r)]})

    def anchors(self, target, *, limit=None, confirm=False):
        lim = self._limit(limit)
        payload = {"target": clean_domain(target), "limit": lim, "order_by": ["backlinks,desc"]}
        api = self.client.call(EP["anchors"], payload, units=lim, confirm=confirm)
        r = api.first
        return _resp(api, {"total_count": r.get("total_count"), "items": [m.anchor_item(i) for i in m.items(r)]})

    # --- SERP ---------------------------------------------------------------

    def _serp(self, keyword, depth, device, location_code, language_code, confirm):
        if device not in {"desktop", "mobile"}:
            raise InputError("device debe ser desktop o mobile.")
        d = clamp_int("depth", depth, default=10, minimum=10, maximum=self.s.max_serp_depth)
        payload = {
            "keyword": clean_keyword(keyword, max_chars=700, max_words=100),
            **self._geo(location_code, language_code),
            "depth": d,
            "device": device,
        }
        # Se factura por cada SERP de hasta 10 resultados.
        return self.client.call(EP["serp_organic"], payload, units=math.ceil(d / 10), confirm=confirm)

    def serp_organic(self, keyword, *, depth=None, device="desktop", location_code=None, language_code=None,
                     confirm=False):
        api = self._serp(keyword, depth, device, location_code, language_code, confirm)
        return _resp(api, m.serp(api.first))

    def rank_check(self, keyword, domain, *, depth=None, device="desktop", location_code=None,
                   language_code=None, confirm=False):
        target = clean_domain(domain)
        api = self._serp(keyword, depth, device, location_code, language_code, confirm)
        serp = m.serp(api.first)
        matches = [o for o in serp["organic"] if m.domain_matches(o["domain"], target)]
        return _resp(api, {
            "keyword": serp["keyword"],
            "domain": target,
            "found": bool(matches),
            "best_position": matches[0]["rank_group"] if matches else None,
            "matches": matches,
            "checked_results": len(serp["organic"]),
            "features": serp["features"],
        })

    # --- auditoría On-Page --------------------------------------------------

    def start_crawl(self, target, *, max_crawl_pages=None, start_url=None, max_crawl_depth=None,
                    enable_javascript=False, load_resources=False, enable_browser_rendering=False,
                    respect_sitemap=False, allow_subdomains=False, check_spell=False, confirm=False):
        domain = clean_domain(target)
        pages = clamp_int("max_crawl_pages", max_crawl_pages, default=min(100, self.s.max_crawl_pages),
                          minimum=1, maximum=self.s.max_crawl_pages)
        payload: dict[str, Any] = {"target": domain, "max_crawl_pages": pages}
        if start_url:
            payload["start_url"] = clean_url(start_url)
        if max_crawl_depth is not None:
            payload["max_crawl_depth"] = clamp_int("max_crawl_depth", max_crawl_depth, default=0, minimum=0,
                                                   maximum=100)
        for key, value in (("enable_javascript", enable_javascript), ("load_resources", load_resources),
                           ("enable_browser_rendering", enable_browser_rendering),
                           ("respect_sitemap", respect_sitemap), ("allow_subdomains", allow_subdomains)):
            if value:
                payload[key] = True
        if enable_browser_rendering:
            # La documentación indica que el renderizado requiere JavaScript y recursos.
            payload["enable_javascript"] = True
            payload["load_resources"] = True
        if check_spell:
            payload["check_spell"] = True
            payload["check_spell_language"] = self.s.default_language_code

        api = self.client.call(EP["crawl_post"], payload, units=pages, confirm=confirm, use_cache=False)
        task_id = api.task.get("id")
        if not task_id:
            raise ProviderError("DataForSEO no devolvió el identificador del rastreo.")
        options = {k: v for k, v in payload.items() if k not in {"target", "max_crawl_pages"}}
        self.db.execute(
            "INSERT OR REPLACE INTO crawls (task_id, target, max_crawl_pages, options, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (task_id, domain, pages, json.dumps(options), time.time()),
        )
        return _resp(api, {"task_id": task_id, "target": domain, "max_crawl_pages": pages, "options": options})

    def list_crawls(self):
        rows = self.db.execute("SELECT * FROM crawls ORDER BY created_at DESC")
        return {
            "data": [{**dict(r), "options": json.loads(r["options"])} for r in rows],
            "meta": {"endpoint": "local", "cost": 0, "from_cache": False},
        }

    def delete_crawl(self, task_id: str) -> None:
        tid = self._task_id(task_id)
        if not self.db.execute("SELECT 1 FROM crawls WHERE task_id = ?", (tid,)):
            raise NotFound("Rastreo no encontrado.")
        self.db.execute("DELETE FROM crawls WHERE task_id = ?", (tid,))

    def _crawl_list(self, key, task_id, extra, limit, offset, confirm, mapper):
        lim = self._limit(limit)
        payload = {"id": self._task_id(task_id), "limit": lim, "offset": self._offset(offset), **extra}
        api = self.client.call(EP[key], payload, confirm=confirm, use_cache=False)
        r = api.first
        return _resp(api, {
            "crawl_progress": r.get("crawl_progress"),
            "total_count": r.get("total_items_count", r.get("total_pages_count")),
            "items": [mapper(i) for i in m.items(r)],
        })

    def crawl_summary(self, task_id, *, confirm=False):
        api = self.client.call(EP["crawl_summary"], path_params={"id": self._task_id(task_id)},
                               confirm=confirm, use_cache=False)
        return _resp(api, m.crawl_summary(api.first))

    def crawl_pages(self, task_id, *, limit=None, offset=None, only_issues=False, confirm=False):
        extra: dict[str, Any] = {"order_by": ["onpage_score,asc"]}
        if only_issues:
            extra["filters"] = ["onpage_score", "<", 100]
        return self._crawl_list("crawl_pages", task_id, extra, limit, offset, confirm, m.crawl_page)

    def crawl_broken_links(self, task_id, *, limit=None, offset=None, confirm=False):
        extra = {"filters": ["is_broken", "=", True]}
        return self._crawl_list("crawl_links", task_id, extra, limit, offset, confirm, m.crawl_link)

    def crawl_broken_resources(self, task_id, *, limit=None, offset=None, confirm=False):
        extra = {"filters": ["status_code", ">=", 400]}
        return self._crawl_list("crawl_resources", task_id, extra, limit, offset, confirm, m.crawl_resource)

    def crawl_duplicate_tags(self, task_id, tag_type, *, limit=None, offset=None, confirm=False):
        if tag_type not in DUPLICATE_TAG_TYPES:
            raise InputError("type debe ser duplicate_title o duplicate_description.")
        return self._crawl_list("crawl_duplicate_tags", task_id, {"type": tag_type}, limit, offset, confirm,
                                m.duplicate_group)

    def crawl_redirect_chains(self, task_id, *, limit=None, offset=None, confirm=False):
        return self._crawl_list("crawl_redirect_chains", task_id, {}, limit, offset, confirm, m.redirect_chain)

    def crawl_non_indexable(self, task_id, *, limit=None, offset=None, confirm=False):
        return self._crawl_list("crawl_non_indexable", task_id, {}, limit, offset, confirm, m.non_indexable)

    def instant_page(self, url, *, enable_javascript=False, confirm=False):
        payload: dict[str, Any] = {"url": clean_url(url)}
        if enable_javascript:
            payload["enable_javascript"] = True
        api = self.client.call(EP["instant_pages"], payload, confirm=confirm)
        page = m.items(api.first)
        return _resp(api, m.crawl_page(page[0]) if page else None)

    def lighthouse(self, url, *, for_mobile=False, confirm=False):
        payload = {"url": clean_url(url), "for_mobile": bool(for_mobile)}
        api = self.client.call(EP["lighthouse"], payload, confirm=confirm)
        return _resp(api, m.lighthouse(api.first) if api.first else None)

    # --- cuenta -------------------------------------------------------------

    def account(self, *, confirm=False):
        api = self.client.call(EP["user_data"], confirm=confirm, use_cache=False)
        r = api.first
        return _resp(api, {
            "balance": m.dig(r, "money", "balance"),
            "total_deposited": m.dig(r, "money", "total"),
            "timezone": r.get("timezone"),
            "backlinks_subscription_expiry_date": r.get("backlinks_subscription_expiry_date"),
        })
