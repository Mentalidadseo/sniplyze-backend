"""Registro del coste real de cada llamada y control de gasto antes de llamar.

El coste de una consulta solo se conoce cuando la API responde (campo `cost`).
Para decidir *antes* de llamar se estima a partir del historial: el mayor coste por
unidad observado en ese endpoint multiplicado por las unidades de la nueva consulta
(páginas de SERP, páginas a rastrear, resultados pedidos...). Es una estimación
conservadora. Si un endpoint nunca se ha llamado, su coste es desconocido.
"""
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.db import Database
from app.core.errors import BudgetExceeded, ConfirmationRequired


def _start_of_utc_day(now: float | None = None) -> float:
    dt = datetime.fromtimestamp(now if now is not None else time.time(), tz=timezone.utc)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


@dataclass
class CostEstimate:
    endpoint: str
    units: float
    estimated_cost: float | None  # None = desconocido

    @property
    def known(self) -> bool:
        return self.estimated_cost is not None


class CostLedger:
    def __init__(self, db: Database):
        self.db = db

    def record(
        self,
        endpoint: str,
        cost: float | None,
        *,
        units: float = 1,
        from_cache: bool = False,
        status_code: int | None = None,
        ok: bool = True,
        message: str | None = None,
    ) -> None:
        self.db.execute(
            "INSERT INTO api_calls (ts, endpoint, units, cost, from_cache, status_code, ok, message)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (time.time(), endpoint, units, cost, int(from_cache), status_code, int(ok), message),
        )

    def estimate(self, endpoint: str, units: float = 1) -> CostEstimate:
        rows = self.db.execute(
            "SELECT MAX(cost / units) AS per_unit FROM api_calls"
            " WHERE endpoint = ? AND from_cache = 0 AND cost IS NOT NULL AND units > 0",
            (endpoint,),
        )
        per_unit = rows[0]["per_unit"] if rows else None
        return CostEstimate(endpoint, units, None if per_unit is None else round(per_unit * units, 6))

    def spent_since(self, since: float) -> float:
        rows = self.db.execute(
            "SELECT COALESCE(SUM(cost), 0) AS total FROM api_calls WHERE from_cache = 0 AND ts >= ?",
            (since,),
        )
        return float(rows[0]["total"])

    def spent_today(self) -> float:
        return self.spent_since(_start_of_utc_day())

    def summary(self, recent: int = 50) -> dict:
        totals = self.db.execute(
            "SELECT COUNT(*) AS calls, COALESCE(SUM(cost), 0) AS cost FROM api_calls WHERE from_cache = 0"
        )[0]
        cache = self.db.execute(
            "SELECT COUNT(*) AS hits, COALESCE(SUM(cost), 0) AS saved FROM api_calls WHERE from_cache = 1"
        )[0]
        by_endpoint = self.db.execute(
            "SELECT endpoint, COUNT(*) AS calls, COALESCE(SUM(cost), 0) AS cost,"
            " SUM(CASE WHEN ok = 0 THEN 1 ELSE 0 END) AS errors"
            " FROM api_calls WHERE from_cache = 0 GROUP BY endpoint ORDER BY cost DESC"
        )
        by_day = self.db.execute(
            "SELECT date(ts, 'unixepoch') AS day, COUNT(*) AS calls, COALESCE(SUM(cost), 0) AS cost"
            " FROM api_calls WHERE from_cache = 0 GROUP BY day ORDER BY day DESC LIMIT 31"
        )
        last = self.db.execute(
            "SELECT ts, endpoint, units, cost, from_cache, status_code, ok, message"
            " FROM api_calls ORDER BY id DESC LIMIT ?",
            (recent,),
        )
        return {
            "total_calls": totals["calls"],
            "total_cost": round(totals["cost"], 6),
            "spent_today_utc": round(self.spent_today(), 6),
            "cache_hits": cache["hits"],
            "saved_by_cache": round(cache["saved"], 6),
            "by_endpoint": [dict(r) for r in by_endpoint],
            "by_day": [dict(r) for r in by_day],
            "recent": [dict(r) for r in last],
        }


class CostGuard:
    """Decide si una consulta puede lanzarse sin confirmación del usuario."""

    def __init__(self, ledger: CostLedger, *, threshold: float, confirm_unknown: bool, daily_budget: float):
        self.ledger = ledger
        self.threshold = threshold
        self.confirm_unknown = confirm_unknown
        self.daily_budget = daily_budget

    def check(self, endpoint: str, units: float, confirm: bool) -> CostEstimate:
        est = self.ledger.estimate(endpoint, units)

        if self.daily_budget > 0:
            spent = self.ledger.spent_today()
            projected = spent + (est.estimated_cost or 0)
            if projected > self.daily_budget:
                raise BudgetExceeded(
                    "La consulta superaría el tope de gasto diario.",
                    endpoint=endpoint,
                    spent_today=round(spent, 6),
                    estimated_cost=est.estimated_cost,
                    daily_budget=self.daily_budget,
                )

        if confirm:
            return est
        if not est.known and self.confirm_unknown:
            raise ConfirmationRequired(
                "Todavía no se conoce el coste de este endpoint: confirma para lanzar la primera consulta.",
                endpoint=endpoint,
                estimated_cost=None,
                threshold=self.threshold,
            )
        if est.known and est.estimated_cost > self.threshold:
            raise ConfirmationRequired(
                "El coste estimado supera el umbral configurado.",
                endpoint=endpoint,
                estimated_cost=est.estimated_cost,
                threshold=self.threshold,
            )
        return est
