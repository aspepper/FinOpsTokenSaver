from decimal import Decimal
from typing import Protocol

import asyncpg

from finops_token_saver.application.metrics import MetricsRepository
from finops_token_saver.domain.cache_status import CACHE_STATUS_HIT
from finops_token_saver.domain.finops_metric import FinOpsMetric

INSERT_FINOPS_METRIC_SQL = """
INSERT INTO tb_finops_metrics (
    request_id,
    model_name,
    prompt_tokens,
    completion_tokens,
    cache_status,
    is_cache_hit,
    estimated_cost_usd,
    saved_cost_usd,
    latency_ms,
    price_version,
    is_model_priced
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
"""


class AsyncPostgresPool(Protocol):
    async def execute(self, query: str, *args: object) -> object:
        """Execute a SQL statement."""


class LazyAsyncPostgresPool:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._pool: AsyncPostgresPool | None = None

    async def execute(self, query: str, *args: object) -> object:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._database_url)
        return await self._pool.execute(query, *args)


class PostgresMetricsRepository(MetricsRepository):
    def __init__(self, pool: AsyncPostgresPool) -> None:
        self._pool = pool

    @classmethod
    def from_database_url(cls, database_url: str) -> "PostgresMetricsRepository":
        return cls(LazyAsyncPostgresPool(database_url))

    async def save(self, metric: FinOpsMetric) -> None:
        await self._pool.execute(
            INSERT_FINOPS_METRIC_SQL,
            metric.request_id,
            metric.model_name,
            metric.token_usage.prompt_tokens,
            metric.token_usage.completion_tokens,
            metric.cache_status,
            metric.cache_status == CACHE_STATUS_HIT,
            _money_amount(metric.estimated_cost.amount),
            _money_amount(metric.saved_cost.amount),
            metric.latency_ms,
            metric.price_version,
            metric.is_model_priced,
        )


def _money_amount(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.000001"))
