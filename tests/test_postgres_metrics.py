from decimal import Decimal

import pytest

from finops_token_saver.domain.cache_status import CACHE_STATUS_HIT
from finops_token_saver.domain.finops_metric import FinOpsMetric
from finops_token_saver.domain.pricing import ModelPrice, PricingCatalog, TokenUsage
from finops_token_saver.infrastructure.postgres_metrics import (
    INSERT_FINOPS_METRIC_SQL,
    PostgresMetricsRepository,
)


class FakePostgresPool:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    async def execute(self, query: str, *args: object) -> None:
        self.calls.append((query, args))


@pytest.mark.anyio
async def test_postgres_metrics_repository_persists_metric_fields() -> None:
    pool = FakePostgresPool()
    repository = PostgresMetricsRepository(pool)
    metric = FinOpsMetric.from_call(
        request_id="request-1",
        model_name="test-model",
        token_usage=TokenUsage(prompt_tokens=1_000, completion_tokens=500),
        cache_status=CACHE_STATUS_HIT,
        latency_ms=42,
        pricing_catalog=PricingCatalog(
            {
                "test-model": ModelPrice(
                    prompt_per_million_tokens=Decimal("2.00"),
                    completion_per_million_tokens=Decimal("8.00"),
                    version="test-prices-v1",
                )
            }
        ),
    )

    await repository.save(metric)

    assert pool.calls == [
        (
            INSERT_FINOPS_METRIC_SQL,
            (
                "request-1",
                "test-model",
                1_000,
                500,
                "HIT",
                True,
                Decimal("0.000000"),
                Decimal("0.006000"),
                42,
                "test-prices-v1",
                True,
            ),
        )
    ]
