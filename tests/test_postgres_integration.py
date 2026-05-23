from __future__ import annotations

import os
from pathlib import Path

import asyncpg
import httpx
import pytest

from finops_token_saver.api.app import create_app
from finops_token_saver.domain.provider import ProviderResponse
from finops_token_saver.infrastructure.postgres_metrics import PostgresMetricsRepository
from finops_token_saver.infrastructure.settings import AppSettings
from tests.fakes import FakeProviderClient

pytestmark = pytest.mark.integration

GATEWAY_TOKEN = "postgres-integration-token"
REQUEST_ID = "postgres-integration-request"
PAYLOAD = {
    "model": "postgres-integration-model",
    "messages": [{"role": "user", "content": "postgres integration prompt"}],
    "temperature": 0,
}


@pytest.mark.anyio
async def test_real_postgres_metric_persistence_by_request_id() -> None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is not configured; skipping real Postgres integration smoke test")

    pool = await _create_pool(database_url)
    try:
        await _ensure_schema(pool)
        await _cleanup_metric(pool, REQUEST_ID)

        provider_client = FakeProviderClient(
            response=ProviderResponse(
                status_code=200,
                body={
                    "id": "postgres-integration-completion",
                    "choices": [],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                },
                provider="fake",
            )
        )
        app = create_app(
            settings=AppSettings.from_env({"GATEWAY_API_KEYS": GATEWAY_TOKEN}),
            provider_client=provider_client,
            metrics_repository=PostgresMetricsRepository(pool),
        )

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GATEWAY_TOKEN}",
                    "X-Request-Id": REQUEST_ID,
                },
                json=PAYLOAD,
            )

        assert response.status_code == 200
        persisted_metric = await pool.fetchrow(
            """
            SELECT request_id, model_name, prompt_tokens, completion_tokens, cache_status
            FROM tb_finops_metrics
            WHERE request_id = $1
            """,
            REQUEST_ID,
        )
        assert persisted_metric is not None
        assert persisted_metric["request_id"] == REQUEST_ID
        assert persisted_metric["model_name"] == "postgres-integration-model"
        assert persisted_metric["prompt_tokens"] == 3
        assert persisted_metric["completion_tokens"] == 2
        assert persisted_metric["cache_status"] == "BYPASS"
    finally:
        await _cleanup_metric(pool, REQUEST_ID)
        await pool.close()


async def _create_pool(database_url: str) -> asyncpg.Pool:
    try:
        return await asyncpg.create_pool(database_url, min_size=1, max_size=1)
    except (asyncpg.PostgresError, OSError) as error:
        pytest.fail(
            f"Postgres integration smoke could not connect to configured DATABASE_URL: "
            f"{type(error).__name__}"
        )


async def _ensure_schema(pool: asyncpg.Pool) -> None:
    migration_sql = Path("migrations/001_create_finops_metrics.sql").read_text()
    try:
        await pool.execute(migration_sql)
    except asyncpg.PostgresError as error:
        pytest.fail(
            "Postgres integration smoke could not apply "
            f"migrations/001_create_finops_metrics.sql: {type(error).__name__}"
        )


async def _cleanup_metric(pool: asyncpg.Pool, request_id: str) -> None:
    try:
        await pool.execute("DELETE FROM tb_finops_metrics WHERE request_id = $1", request_id)
    except asyncpg.UndefinedTableError:
        return
