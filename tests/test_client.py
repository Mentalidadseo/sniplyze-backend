import base64
import json

import httpx
import pytest

from app.core.cache import ResponseCache
from app.core.costs import CostGuard, CostLedger
from app.core.db import Database
from app.core.errors import ConfigError, ConfirmationRequired, ProviderError
from app.providers.dataforseo.client import DataForSEOClient, Endpoint
from tests.conftest import FakeDataForSEO, envelope

EP = Endpoint("keywords_data/google_ads/search_volume/live", ttl=3600)
PATH = "/v3/keywords_data/google_ads/search_volume/live"


def make(fake: FakeDataForSEO, *, login="user", password="pass", confirm_unknown=False, threshold=0.5):
    db = Database(":memory:")
    ledger = CostLedger(db)
    guard = CostGuard(ledger, threshold=threshold, confirm_unknown=confirm_unknown, daily_budget=0)
    sleeps = []
    client = DataForSEOClient(login=login, password=password, base_url="https://api.dataforseo.com",
                              cache=ResponseCache(db), ledger=ledger, guard=guard,
                              transport=fake.transport, sleep=sleeps.append)
    return client, ledger, sleeps


def test_success_sends_basic_auth_and_task_array_and_records_cost(fake):
    fake.on(PATH, envelope([{"keyword": "a"}], cost=0.05))
    client, ledger, _ = make(fake)
    res = client.call(EP, {"keywords": ["a"]})
    req = fake.requests[0]
    assert req.method == "POST"
    assert req.headers["authorization"] == "Basic " + base64.b64encode(b"user:pass").decode()
    assert json.loads(req.content) == [{"keywords": ["a"]}]
    assert res.cost == 0.05 and res.from_cache is False
    assert res.result == [{"keyword": "a"}]
    assert ledger.summary()["total_cost"] == pytest.approx(0.05)


def test_second_identical_call_comes_from_cache_without_http(fake):
    fake.on(PATH, envelope([{"keyword": "a"}], cost=0.05))
    client, ledger, _ = make(fake)
    client.call(EP, {"keywords": ["a"]})
    res = client.call(EP, {"keywords": ["a"]})
    assert len(fake.requests) == 1
    assert res.from_cache is True and res.cached_at is not None
    s = ledger.summary()
    assert s["total_cost"] == pytest.approx(0.05) and s["saved_by_cache"] == pytest.approx(0.05)


def test_different_payload_is_not_cached(fake):
    fake.on(PATH, envelope([], cost=0.05))
    client, _, _ = make(fake)
    client.call(EP, {"keywords": ["a"]})
    client.call(EP, {"keywords": ["b"]})
    assert len(fake.requests) == 2


def test_missing_credentials_never_calls_api(fake):
    client, _, _ = make(fake, login="", password="")
    with pytest.raises(ConfigError):
        client.call(EP, {"keywords": ["a"]})
    assert fake.requests == []


def test_confirmation_required_never_calls_api(fake):
    client, _, _ = make(fake, confirm_unknown=True)
    with pytest.raises(ConfirmationRequired):
        client.call(EP, {"keywords": ["a"]})
    assert fake.requests == []


def test_task_error_raises_records_and_does_not_cache(fake):
    fake.on(PATH, envelope(None, cost=0, task_status=40501, task_message="Invalid Field: 'keywords'."))
    client, ledger, _ = make(fake)
    with pytest.raises(ProviderError) as exc:
        client.call(EP, {"keywords": ["a"]})
    assert "Invalid Field" in exc.value.message
    assert exc.value.details["provider_status_code"] == 40501
    with pytest.raises(ProviderError):
        client.call(EP, {"keywords": ["a"]})
    assert len(fake.requests) == 2
    assert ledger.summary()["by_endpoint"][0]["errors"] == 2


def test_top_level_error(fake):
    fake.on(PATH, {"status_code": 40200, "status_message": "Payment Required.", "cost": 0, "tasks": []})
    client, _, _ = make(fake)
    with pytest.raises(ProviderError) as exc:
        client.call(EP, {"keywords": ["a"]})
    assert "Payment Required" in exc.value.message


def test_http_401(fake):
    fake.on(PATH, {"status_code": 40100, "status_message": "Not authorized."}, status=401)
    client, _, _ = make(fake)
    with pytest.raises(ProviderError) as exc:
        client.call(EP, {"keywords": ["a"]})
    assert "401" in exc.value.message


def test_connect_error_is_retried_once(fake):
    calls = {"n": 0}

    def flaky(request):
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(200, json=envelope([], cost=0.01))

    fake.on(PATH, flaky)
    client, _, sleeps = make(fake)
    client.call(EP, {"keywords": ["a"]})
    assert calls["n"] == 2 and sleeps == [2]


def test_read_timeout_is_not_retried(fake):
    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    fake.on(PATH, slow)
    client, _, sleeps = make(fake)
    with pytest.raises(ProviderError):
        client.call(EP, {"keywords": ["a"]})
    assert len(fake.requests) == 1 and sleeps == []


def test_http_503_retried_once_then_fails(fake):
    fake.on(PATH, {"status_code": 50000, "status_message": "Internal Error."}, status=503)
    client, _, sleeps = make(fake)
    with pytest.raises(ProviderError):
        client.call(EP, {"keywords": ["a"]})
    assert len(fake.requests) == 2 and sleeps == [2]


def test_get_endpoint_with_path_param(fake):
    fake.on("/v3/on_page/summary/abc-12345678", envelope([{"crawl_progress": "finished"}], cost=0))
    client, _, _ = make(fake)
    res = client.call(Endpoint("on_page/summary/{id}", method="GET"), path_params={"id": "abc-12345678"})
    assert fake.requests[0].method == "GET" and fake.requests[0].content == b""
    assert res.endpoint == "on_page/summary"
    assert res.first == {"crawl_progress": "finished"}
