import json
from typing import Any, Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.deps import build_container
from app.main import create_app


def envelope(result: list | None, *, cost: float | None = 0.01, status_code: int = 20000,
             task_status: int = 20000, task_message: str = "Ok.", task_id: str = "11111111-2222-3333-4444-555555555555"):
    """Respuesta con la estructura de DataForSEO v3: nivel superior + tasks[]."""
    return {
        "version": "0.1.test",
        "status_code": status_code,
        "status_message": "Ok." if status_code == 20000 else "Error.",
        "time": "0.1 sec.",
        "cost": cost,
        "tasks_count": 1,
        "tasks_error": 0 if task_status == 20000 else 1,
        "tasks": [{
            "id": task_id,
            "status_code": task_status,
            "status_message": task_message,
            "time": "0.1 sec.",
            "cost": cost,
            "result_count": len(result or []),
            "path": [],
            "data": {},
            "result": result,
        }],
    }


class FakeDataForSEO:
    """Transporte simulado: responde según la ruta y guarda cada petición."""

    def __init__(self):
        self.routes: dict[str, Callable[[httpx.Request], httpx.Response] | dict] = {}
        self.requests: list[httpx.Request] = []

    def on(self, path: str, body: dict | Callable[[httpx.Request], httpx.Response], status: int = 200):
        self.routes[path] = body if callable(body) else (lambda req, b=body, s=status: httpx.Response(s, json=b))

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        for key, fn in self.routes.items():
            if path == key or (key.endswith("*") and path.startswith(key[:-1])):
                return fn(request)
        return httpx.Response(404, json={"status_code": 40400, "status_message": "Not Found."})

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)

    def last_payload(self) -> Any:
        return json.loads(self.requests[-1].content)


def make_settings(tmp_path, **overrides) -> Settings:
    values = dict(
        dataforseo_login="test-login",
        dataforseo_password="test-password",
        data_dir=tmp_path,
        cost_confirm_threshold=0.5,
        confirm_unknown_cost=False,
        daily_budget=0,
    )
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def fake():
    return FakeDataForSEO()


@pytest.fixture
def make_client(tmp_path, fake):
    """Crea un TestClient de la app con DataForSEO simulado."""

    def _make(**overrides) -> TestClient:
        settings = make_settings(tmp_path, **overrides)
        container = build_container(settings, transport=fake.transport, sleep=lambda _: None)
        return TestClient(create_app(settings=settings, container=container))

    return _make


@pytest.fixture
def client(make_client):
    return make_client()
