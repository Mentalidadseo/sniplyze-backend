import pytest

from tests import samples as S
from tests.conftest import envelope

V3 = "/v3/"


def test_index_and_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    r = client.get("/")
    assert r.status_code == 200 and "Sniplyze" in r.text


def test_config_never_exposes_credentials(client):
    r = client.get("/api/config").json()
    assert r["credentials_configured"] is True
    assert "test-password" not in str(r) and "test-login" not in str(r)


def test_missing_credentials(make_client, fake):
    c = make_client(dataforseo_login="", dataforseo_password="")
    r = c.post("/api/keywords/volume", json={"keywords": ["a"]})
    assert r.status_code == 503 and r.json()["error"] == "not_configured"
    assert fake.requests == []


def test_invalid_input_rejected_before_spending(client, fake):
    r = client.post("/api/domains/overview", json={"target": "no es dominio"})
    assert r.status_code == 422 and r.json()["error"] == "invalid_input"
    r = client.post("/api/keywords/volume", json={"keywords": [f"kw {i}" for i in range(101)]})
    assert r.status_code == 422
    assert fake.requests == []


def test_confirmation_flow(make_client, fake):
    fake.on(V3 + "keywords_data/google_ads/search_volume/live", envelope(S.SEARCH_VOLUME, cost=0.075))
    c = make_client(confirm_unknown_cost=True)
    r = c.post("/api/keywords/volume", json={"keywords": ["zapatillas running"]})
    assert r.status_code == 402
    body = r.json()
    assert body["error"] == "confirmation_required" and body["estimated_cost"] is None
    assert fake.requests == []
    r = c.post("/api/keywords/volume?confirm=true", json={"keywords": ["zapatillas running"]})
    assert r.status_code == 200 and r.json()["meta"]["cost"] == 0.075
    # Ya se conoce el coste (0,075 por keyword) y está bajo el umbral: no pide confirmar.
    r = c.post("/api/keywords/volume", json={"keywords": ["otra"]})
    assert r.status_code == 200
    # 10 keywords -> 0,75 estimado > 0,50: pide confirmar.
    r = c.post("/api/keywords/volume", json={"keywords": [f"k{i}" for i in range(10)]})
    assert r.status_code == 402 and r.json()["estimated_cost"] == pytest.approx(0.75)


def test_search_volume(client, fake):
    fake.on(V3 + "keywords_data/google_ads/search_volume/live", envelope(S.SEARCH_VOLUME))
    r = client.post("/api/keywords/volume", json={"keywords": [" Zapatillas Running ", "keyword rara"]})
    assert r.status_code == 200
    assert fake.last_payload() == [{"keywords": ["zapatillas running", "keyword rara"],
                                    "location_code": 2724, "language_code": "es"}]
    data = r.json()["data"]
    assert data[0]["search_volume"] == 14800 and data[0]["competition"] == "HIGH"
    assert data[0]["monthly_searches"][1] == {"year": 2026, "month": 9, "search_volume": 1600}
    assert data[1]["search_volume"] is None and data[1]["low_top_of_page_bid"] is None


def test_related_keywords_missing_metrics_are_none(client, fake):
    fake.on(V3 + "dataforseo_labs/google/related_keywords/live", envelope(S.RELATED))
    r = client.post("/api/keywords/related", json={"keyword": "zapatillas running", "depth": 2, "limit": 10,
                                                   "location_code": 2840, "language_code": "en"})
    p = fake.last_payload()[0]
    assert p["depth"] == 2 and p["limit"] == 10 and p["location_code"] == 2840 and p["language_code"] == "en"
    d = r.json()["data"]
    assert d["seed"]["keyword"] == "zapatillas running"
    assert d["items"][0]["search_volume"] == 2400 and d["items"][0]["keyword_difficulty"] == 40
    empty = d["items"][1]
    assert empty["keyword"] == "sin metricas"
    assert all(empty[k] is None for k in ("search_volume", "cpc", "keyword_difficulty", "main_intent"))


def test_related_depth_validated(client, fake):
    assert client.post("/api/keywords/related", json={"keyword": "a", "depth": 5}).status_code == 422
    assert fake.requests == []


def test_suggestions(client, fake):
    fake.on(V3 + "dataforseo_labs/google/keyword_suggestions/live", envelope(S.SUGGESTIONS))
    r = client.post("/api/keywords/suggestions", json={"keyword": "zapatillas", "exact_match": True})
    assert fake.last_payload()[0]["exact_match"] is True
    d = r.json()["data"]
    assert d["seed"] is None
    assert d["items"][0]["main_intent"] == "transactional"


def test_difficulty_and_intent(client, fake):
    fake.on(V3 + "dataforseo_labs/google/bulk_keyword_difficulty/live", envelope(S.DIFFICULTY))
    fake.on(V3 + "dataforseo_labs/google/search_intent/live", envelope(S.INTENT))
    d = client.post("/api/keywords/difficulty", json={"keywords": ["a", "b"]}).json()["data"]
    assert d == [{"keyword": "a", "keyword_difficulty": 12}, {"keyword": "b", "keyword_difficulty": None}]
    d = client.post("/api/keywords/intent", json={"keywords": ["comprar zapatillas"]}).json()["data"]
    assert fake.last_payload() == [{"keywords": ["comprar zapatillas"]}]
    assert d[0]["intent"] == "transactional" and d[0]["secondary"][0]["intent"] == "commercial"


def test_domain_overview(client, fake):
    fake.on(V3 + "dataforseo_labs/google/domain_rank_overview/live", envelope(S.DOMAIN_OVERVIEW))
    d = client.post("/api/domains/overview", json={"target": "https://www.Ejemplo.com/"}).json()["data"]
    assert fake.last_payload()[0]["target"] == "ejemplo.com"
    assert d["organic"]["etv"] == 1234.5 and d["organic"]["pos_21_30"] is None
    assert d["paid"] is None


def test_ranked_keywords(client, fake):
    fake.on(V3 + "dataforseo_labs/google/ranked_keywords/live", envelope(S.RANKED))
    d = client.post("/api/domains/ranked-keywords", json={"target": "ejemplo.com", "limit": 50}).json()["data"]
    p = fake.last_payload()[0]
    assert p["limit"] == 50 and p["order_by"] == ["keyword_data.keyword_info.search_volume,desc"]
    assert d["total_count"] == 500
    assert d["items"][0]["position"]["rank_group"] == 3 and d["items"][0]["position"]["url"].endswith("/z")


def test_competitors_gap_pages_history_traffic(client, fake):
    fake.on(V3 + "dataforseo_labs/google/competitors_domain/live", envelope(S.COMPETITORS))
    fake.on(V3 + "dataforseo_labs/google/domain_intersection/live", envelope(S.GAP))
    fake.on(V3 + "dataforseo_labs/google/relevant_pages/live", envelope(S.TOP_PAGES))
    fake.on(V3 + "dataforseo_labs/google/historical_rank_overview/live", envelope(S.HISTORY))
    fake.on(V3 + "dataforseo_labs/google/bulk_traffic_estimation/live", envelope(S.TRAFFIC))

    d = client.post("/api/domains/competitors", json={"target": "ejemplo.com"}).json()["data"]
    assert d["items"][0]["domain"] == "rival.com" and d["items"][0]["intersection_organic"]["etv"] == 100.0

    d = client.post("/api/domains/keyword-gap", json={"target_1": "a.com", "target_2": "b.com",
                                                      "intersections": False}).json()["data"]
    assert fake.last_payload()[0]["intersections"] is False
    assert d["items"][0]["target_1"]["rank_group"] == 2 and d["items"][0]["target_2"]["rank_group"] == 7
    assert client.post("/api/domains/keyword-gap", json={"target_1": "a.com", "target_2": "www.a.com"}).status_code == 422

    d = client.post("/api/domains/top-pages", json={"target": "ejemplo.com"}).json()["data"]
    assert d["items"][0]["page"] == "https://ejemplo.com/"

    d = client.post("/api/domains/history", json={"target": "ejemplo.com"}).json()["data"]
    assert [x["organic"]["etv"] for x in d] == [1234.5, 1500.0]

    d = client.post("/api/domains/traffic", json={"targets": ["a.com", "https://b.com/x"]}).json()["data"]
    assert fake.last_payload()[0]["targets"] == ["a.com", "b.com"]
    assert d[1]["paid_etv"] is None and d[0]["paid_keywords"] == 1


def test_backlinks(client, fake):
    fake.on(V3 + "backlinks/summary/live", envelope(S.BACKLINKS_SUMMARY))
    fake.on(V3 + "backlinks/backlinks/live", envelope(S.BACKLINKS))
    fake.on(V3 + "backlinks/referring_domains/live", envelope(S.REFERRING_DOMAINS))
    fake.on(V3 + "backlinks/anchors/live", envelope(S.ANCHORS))
    d = client.post("/api/backlinks/summary", json={"target": "ejemplo.com"}).json()["data"]
    assert d["referring_domains"] == 800 and d["info"]["cms"] is None and d["lost_date"] is None
    d = client.post("/api/backlinks/list", json={"target": "ejemplo.com", "mode": "as_is"}).json()["data"]
    assert fake.last_payload()[0]["mode"] == "as_is" and d["items"][0]["dofollow"] is True
    assert client.post("/api/backlinks/list", json={"target": "ejemplo.com", "mode": "x"}).status_code == 422
    d = client.post("/api/backlinks/referring-domains", json={"target": "ejemplo.com"}).json()["data"]
    assert d["items"][0]["domain"] == "blog.com"
    d = client.post("/api/backlinks/anchors", json={"target": "ejemplo.com"}).json()["data"]
    assert d["items"][0]["anchor"] == "ejemplo" and d["items"][0]["first_seen"] is None


def test_serp_and_rank_check(client, fake):
    fake.on(V3 + "serp/google/organic/live/advanced", envelope(S.SERP))
    d = client.post("/api/serp/organic", json={"keyword": "zapatillas running"}).json()["data"]
    assert fake.last_payload()[0]["depth"] == 10 and fake.last_payload()[0]["device"] == "desktop"
    assert [o["rank_group"] for o in d["organic"]] == [1, 2, 3]
    assert d["features"] == {"people_also_ask": 1}
    assert d["organic"][1]["description"] is None

    r = client.post("/api/serp/rank-check", json={"keyword": "zapatillas running", "domain": "ejemplo.com",
                                                  "depth": 30, "device": "mobile"})
    d = r.json()["data"]
    assert fake.last_payload()[0]["depth"] == 30
    # tienda.ejemplo.com coincide; noejemplo.com no.
    assert d["found"] is True and d["best_position"] == 2 and len(d["matches"]) == 1


def test_serp_depth_bounds(client, fake):
    assert client.post("/api/serp/organic", json={"keyword": "a", "depth": 5}).status_code == 422
    assert fake.requests == []


def test_crawl_lifecycle(client, fake):
    fake.on(V3 + "on_page/task_post", envelope(None, cost=0.0125, task_status=20100, task_message="Task Created.",
                                               task_id=S.TASK_ID))
    fake.on(V3 + f"on_page/summary/{S.TASK_ID}", envelope(S.CRAWL_SUMMARY, cost=0))
    fake.on(V3 + "on_page/pages", envelope(S.CRAWL_PAGES, cost=0))
    fake.on(V3 + "on_page/links", envelope(S.CRAWL_LINKS, cost=0))
    fake.on(V3 + "on_page/resources", envelope([{"crawl_progress": "finished", "total_items_count": 0,
                                                  "items_count": 0, "items": None}], cost=0))
    fake.on(V3 + "on_page/duplicate_tags", envelope(S.CRAWL_DUPLICATES, cost=0))
    fake.on(V3 + "on_page/redirect_chains", envelope(S.CRAWL_REDIRECTS, cost=0))
    fake.on(V3 + "on_page/non_indexable", envelope(S.CRAWL_NON_INDEXABLE, cost=0))

    r = client.post("/api/audit/crawls", json={"target": "https://www.ejemplo.com", "max_crawl_pages": 50,
                                               "enable_browser_rendering": True})
    assert r.status_code == 200
    p = fake.last_payload()[0]
    assert p["target"] == "ejemplo.com" and p["max_crawl_pages"] == 50
    assert p["enable_browser_rendering"] is p["enable_javascript"] is p["load_resources"] is True
    assert r.json()["data"]["task_id"] == S.TASK_ID

    crawls = client.get("/api/audit/crawls").json()["data"]
    assert crawls[0]["task_id"] == S.TASK_ID and crawls[0]["target"] == "ejemplo.com"

    s = client.get(f"/api/audit/crawls/{S.TASK_ID}/summary").json()["data"]
    assert fake.requests[-1].method == "GET"
    assert s["page_metrics"]["broken_links"] == 3 and s["crawl_status"]["pages_crawled"] == 87
    issues = [i["check"] for i in s["issues"]]
    assert issues == ["title_too_long", "no_h1_tag", "is_https"]  # problemas primero, sin los de 0 páginas
    assert s["issues"][-1]["informational"] is True

    d = client.get(f"/api/audit/crawls/{S.TASK_ID}/pages?only_issues=true&limit=10").json()["data"]
    assert fake.last_payload()[0] == {"id": S.TASK_ID, "limit": 10, "offset": 0, "order_by": ["onpage_score,asc"],
                                      "filters": ["onpage_score", "<", 100]}
    page = d["items"][0]
    assert page["h1"] == ["Hola"] and page["words_count"] == 320 and page["description"] is None
    assert page["failed_checks"] == ["no_description", "title_too_short"]

    d = client.get(f"/api/audit/crawls/{S.TASK_ID}/broken-links").json()["data"]
    assert fake.last_payload()[0]["filters"] == ["is_broken", "=", True]
    assert d["items"][0]["page_to_status_code"] == 404

    d = client.get(f"/api/audit/crawls/{S.TASK_ID}/broken-resources").json()["data"]
    assert d["items"] == [] and d["total_count"] == 0

    d = client.get(f"/api/audit/crawls/{S.TASK_ID}/duplicates?type=duplicate_description").json()["data"]
    assert fake.last_payload()[0]["type"] == "duplicate_description"
    assert d["items"][0]["pages"] == ["https://ejemplo.com/", "https://ejemplo.com/?p=1"] and d["total_count"] == 2

    d = client.get(f"/api/audit/crawls/{S.TASK_ID}/redirect-chains").json()["data"]
    assert [c["status_code"] for c in d["items"][0]["chain"]] == [301, 302]

    d = client.get(f"/api/audit/crawls/{S.TASK_ID}/non-indexable").json()["data"]
    assert d["items"][0]["reason"] == "meta_tag"

    assert client.delete(f"/api/audit/crawls/{S.TASK_ID}").status_code == 200
    assert client.get("/api/audit/crawls").json()["data"] == []


def test_crawl_ids_and_types_validated(client, fake):
    assert client.get("/api/audit/crawls/bad!id/summary").status_code == 422
    assert client.get(f"/api/audit/crawls/{S.TASK_ID}/duplicates?type=otro").status_code == 422
    assert client.post("/api/audit/crawls", json={"target": "ejemplo.com", "max_crawl_pages": 0}).status_code == 422
    assert fake.requests == []


def test_crawl_cost_estimate_scales_with_pages(make_client, fake):
    fake.on(V3 + "on_page/task_post", envelope(None, cost=0.0125, task_status=20100, task_id=S.TASK_ID))
    c = make_client()
    assert c.post("/api/audit/crawls", json={"target": "ejemplo.com", "max_crawl_pages": 10}).status_code == 200
    # 0,00125 por página -> 1000 páginas = 1,25 > 0,50
    r = c.post("/api/audit/crawls", json={"target": "ejemplo.com", "max_crawl_pages": 1000})
    assert r.status_code == 402 and r.json()["estimated_cost"] == pytest.approx(1.25)


def test_instant_page_and_lighthouse(client, fake):
    fake.on(V3 + "on_page/instant_pages", envelope(S.INSTANT))
    fake.on(V3 + "on_page/lighthouse/live/json", envelope(S.LIGHTHOUSE))
    d = client.post("/api/audit/page", json={"url": "ejemplo.com/a"}).json()["data"]
    assert fake.last_payload()[0]["url"] == "https://ejemplo.com/a"
    assert d["onpage_score"] == 72.0
    d = client.post("/api/audit/lighthouse", json={"url": "https://ejemplo.com/", "for_mobile": True}).json()["data"]
    assert fake.last_payload()[0]["for_mobile"] is True
    assert d["scores"] == {"performance": 73, "seo": 100, "accessibility": None}
    assert d["metrics"]["largest-contentful-paint"]["display_value"] == "3.1 s"
    assert d["metrics"]["speed-index"]["numeric_value"] is None
    assert [o["id"] for o in d["opportunities"]] == ["render-blocking-resources"]


def test_account_and_costs(client, fake):
    fake.on(V3 + "appendix/user_data", envelope(S.USER_DATA, cost=0))
    d = client.get("/api/account").json()["data"]
    assert d["balance"] == 42.5
    costs = client.get("/api/costs").json()
    assert costs["total_calls"] == 1 and costs["by_endpoint"][0]["endpoint"] == "appendix/user_data"


def test_cache_clear(client, fake):
    fake.on(V3 + "dataforseo_labs/google/bulk_keyword_difficulty/live", envelope(S.DIFFICULTY))
    client.post("/api/keywords/difficulty", json={"keywords": ["a"]})
    r = client.post("/api/keywords/difficulty", json={"keywords": ["a"]})
    assert r.json()["meta"]["from_cache"] is True and len(fake.requests) == 1
    assert client.delete("/api/cache").json() == {"deleted": 1}
    client.post("/api/keywords/difficulty", json={"keywords": ["a"]})
    assert len(fake.requests) == 2


def test_provider_error_is_502(client, fake):
    fake.on(V3 + "backlinks/summary/live",
            envelope(None, cost=0, task_status=40204, task_message="Access denied. Visit Plans and Subscriptions."))
    r = client.post("/api/backlinks/summary", json={"target": "ejemplo.com"})
    assert r.status_code == 502 and "Access denied" in r.json()["message"]
