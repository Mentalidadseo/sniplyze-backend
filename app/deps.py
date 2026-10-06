"""Construcción de dependencias (base de datos, caché, costes, proveedor)."""
import time
from dataclasses import dataclass
from typing import Callable

import httpx
from fastapi import Request

from app.config import Settings
from app.core.cache import ResponseCache
from app.core.costs import CostGuard, CostLedger
from app.core.db import Database
from app.providers.dataforseo.client import DataForSEOClient
from app.providers.dataforseo.provider import DataForSEOProvider


@dataclass
class Container:
    settings: Settings
    db: Database
    cache: ResponseCache
    ledger: CostLedger
    guard: CostGuard
    provider: DataForSEOProvider


def build_container(
    settings: Settings,
    *,
    db_path: str | None = None,
    transport: httpx.BaseTransport | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Container:
    db = Database(db_path or settings.db_path)
    cache = ResponseCache(db, enabled=settings.cache_enabled)
    ledger = CostLedger(db)
    guard = CostGuard(
        ledger,
        threshold=settings.cost_confirm_threshold,
        confirm_unknown=settings.confirm_unknown_cost,
        daily_budget=settings.daily_budget,
    )
    client = DataForSEOClient(
        login=settings.dataforseo_login,
        password=settings.dataforseo_password.get_secret_value(),
        base_url=settings.dataforseo_base_url,
        cache=cache,
        ledger=ledger,
        guard=guard,
        timeout=settings.http_timeout_seconds,
        transport=transport,
        sleep=sleep,
    )
    return Container(settings, db, cache, ledger, guard, DataForSEOProvider(client, settings, db))


def container(request: Request) -> Container:
    return request.app.state.container


def provider(request: Request) -> DataForSEOProvider:
    return request.app.state.container.provider
