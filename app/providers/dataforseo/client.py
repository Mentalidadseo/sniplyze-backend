"""Cliente HTTP mínimo para la API v3 de DataForSEO.

Responsabilidades:
- Autenticación HTTP Basic con las credenciales del entorno.
- Caché local (no se paga dos veces por la misma consulta).
- Control de gasto antes de llamar (umbral, coste desconocido, tope diario).
- Registro del coste real devuelto por la API.
- Comprobación de `status_code` global y de la tarea.
- Reintento único solo cuando la petición no llegó a enviarse o la API pide esperar.
"""
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from app.core.cache import ResponseCache
from app.core.costs import CostEstimate, CostGuard, CostLedger
from app.core.errors import ConfigError, ProviderError

log = logging.getLogger("sniplyze.dataforseo")

RETRYABLE_HTTP = {429, 502, 503, 504}


def is_ok(status_code: Any) -> bool:
    """Los códigos 2xxxx de DataForSEO indican éxito (p. ej. 20000 OK, 20100 tarea creada)."""
    return isinstance(status_code, int) and 20000 <= status_code < 30000


@dataclass(frozen=True)
class Endpoint:
    path: str  # relativo a /v3, puede contener {id}
    method: str = "POST"
    ttl: int = 0  # segundos de caché; 0 = no cachear

    @property
    def name(self) -> str:
        return self.path.split("/{", 1)[0]


@dataclass
class ApiResult:
    endpoint: str
    task: dict
    cost: float | None
    from_cache: bool = False
    cached_at: float | None = None
    estimate: CostEstimate | None = field(default=None, repr=False)

    @property
    def result(self) -> list:
        return self.task.get("result") or []

    @property
    def first(self) -> dict:
        res = self.result
        return res[0] if res and isinstance(res[0], dict) else {}

    def meta(self) -> dict:
        return {
            "endpoint": self.endpoint,
            "cost": self.cost,
            "from_cache": self.from_cache,
            "cached_at": self.cached_at,
            "task_id": self.task.get("id"),
        }


class DataForSEOClient:
    def __init__(
        self,
        *,
        login: str,
        password: str,
        base_url: str,
        cache: ResponseCache,
        ledger: CostLedger,
        guard: CostGuard,
        timeout: float = 120.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._login = login
        self._password = password
        self.base_url = base_url.rstrip("/")
        self.cache = cache
        self.ledger = ledger
        self.guard = guard
        self.timeout = timeout
        self._transport = transport
        self._sleep = sleep

    @property
    def configured(self) -> bool:
        return bool(self._login and self._password)

    def call(
        self,
        endpoint: Endpoint,
        payload: dict | None = None,
        *,
        path_params: dict | None = None,
        units: float = 1,
        confirm: bool = False,
        use_cache: bool = True,
    ) -> ApiResult:
        name = endpoint.name
        path = endpoint.path.format(**(path_params or {}))
        cache_payload = {"path": path, "body": payload}
        cacheable = use_cache and endpoint.ttl > 0

        if cacheable:
            hit = self.cache.get(name, cache_payload)
            if hit is not None:
                self.ledger.record(name, hit.cost, units=units, from_cache=True)
                return ApiResult(name, hit.response, hit.cost, True, hit.created_at)

        if not self.configured:
            raise ConfigError(
                "Faltan las credenciales de DataForSEO. Define DATAFORSEO_LOGIN y DATAFORSEO_PASSWORD en .env."
            )

        estimate = self.guard.check(name, units, confirm)
        body = self._request(endpoint.method, path, payload, name, units)

        cost = body.get("cost")
        tasks = body.get("tasks") or []
        task = tasks[0] if tasks and isinstance(tasks[0], dict) else None
        top_ok = is_ok(body.get("status_code"))
        task_ok = task is not None and is_ok(task.get("status_code"))

        message = None
        if not top_ok:
            message = body.get("status_message")
        elif task is None:
            message = "La respuesta no contiene ninguna tarea."
        elif not task_ok:
            message = task.get("status_message")

        status = (task or {}).get("status_code") if top_ok else body.get("status_code")
        self.ledger.record(name, cost, units=units, status_code=status, ok=message is None, message=message)

        if message is not None:
            raise ProviderError(
                f"DataForSEO devolvió un error: {message}",
                endpoint=name,
                provider_status_code=status,
                cost=cost,
            )

        if cacheable:
            self.cache.set(name, cache_payload, task, cost, endpoint.ttl)
        return ApiResult(name, task, cost, False, None, estimate)

    def _request(self, method: str, path: str, payload: dict | None, name: str, units: float) -> dict:
        url = f"{self.base_url}/v3/{path}"
        kwargs: dict[str, Any] = {}
        if method == "POST":
            kwargs["json"] = [payload or {}]

        attempts = 2
        for attempt in range(1, attempts + 1):
            try:
                with httpx.Client(
                    auth=(self._login, self._password),
                    timeout=self.timeout,
                    transport=self._transport,
                    headers={"Accept": "application/json"},
                ) as http:
                    resp = http.request(method, url, **kwargs)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                # La petición no llegó a enviarse: reintentar no puede cobrar dos veces.
                if attempt < attempts:
                    log.warning("Error de conexión con DataForSEO (%s); reintentando una vez", exc)
                    self._sleep(2)
                    continue
                self.ledger.record(name, None, units=units, ok=False, message=f"conexión: {exc}")
                raise ProviderError("No se pudo conectar con DataForSEO.", endpoint=name) from exc
            except httpx.TimeoutException as exc:
                # La petición pudo procesarse (y cobrarse): no se reintenta.
                self.ledger.record(name, None, units=units, ok=False, message="timeout")
                raise ProviderError(
                    "DataForSEO tardó demasiado en responder. No se reintenta para evitar un doble cobro.",
                    endpoint=name,
                ) from exc

            if resp.status_code in RETRYABLE_HTTP and attempt < attempts:
                log.warning("DataForSEO respondió HTTP %s; reintentando una vez", resp.status_code)
                self._sleep(2)
                continue
            try:
                body = resp.json()
            except (json.JSONDecodeError, ValueError):
                body = None
            if resp.status_code == 401:
                self.ledger.record(name, None, units=units, status_code=401, ok=False, message="no autorizado")
                raise ProviderError("DataForSEO rechazó las credenciales (HTTP 401).", endpoint=name)
            if not isinstance(body, dict):
                self.ledger.record(name, None, units=units, status_code=resp.status_code, ok=False,
                                   message="respuesta no JSON")
                raise ProviderError(
                    f"Respuesta inesperada de DataForSEO (HTTP {resp.status_code}).", endpoint=name
                )
            return body
        raise ProviderError("No se pudo completar la petición a DataForSEO.", endpoint=name)  # pragma: no cover
