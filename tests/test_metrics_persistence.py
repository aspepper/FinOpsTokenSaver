import logging
from decimal import Decimal

from fastapi.testclient import TestClient

from finops_token_saver.api.app import create_app
from finops_token_saver.application.metrics import MetricRecorder
from finops_token_saver.domain.finops_metric import FinOpsMetric
from finops_token_saver.domain.pricing import ModelPrice, Money, PricingCatalog, TokenUsage
from finops_token_saver.domain.provider import ProviderResponse
from finops_token_saver.infrastructure.settings import AppSettings
from tests.fakes import FakeProviderClient


class FakeMetricsRepository:
    def __init__(self, should_fail: bool = False) -> None:
        self.saved_metrics: list[FinOpsMetric] = []
        self._should_fail = should_fail

    async def save(self, metric: FinOpsMetric) -> None:
        if self._should_fail:
            raise RuntimeError("database unavailable")
        self.saved_metrics.append(metric)


def test_chat_completion_schedules_metric_persistence_without_changing_response() -> None:
    metrics_repository = FakeMetricsRepository()
    provider_client = FakeProviderClient(
        response=ProviderResponse(
            status_code=200,
            body={
                "id": "completion-1",
                "choices": [],
                "usage": {"prompt_tokens": 1_000, "completion_tokens": 500},
            },
            provider="fake",
        )
    )
    client = TestClient(
        create_app(
            _settings(),
            provider_client=provider_client,
            metrics_repository=metrics_repository,
            pricing_catalog=_pricing_catalog(),
        )
    )

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json={"model": "test-model", "messages": []},
    )

    assert response.status_code == 200
    assert response.headers["x-cache-status"] == "BYPASS"
    assert response.headers["x-request-id"]
    assert response.headers["x-gateway-latency-ms"].isdigit()
    assert response.json()["id"] == "completion-1"
    assert len(metrics_repository.saved_metrics) == 1

    metric = metrics_repository.saved_metrics[0]
    assert metric.request_id == response.headers["x-request-id"]
    assert metric.model_name == "test-model"
    assert metric.token_usage == TokenUsage(prompt_tokens=1_000, completion_tokens=500)
    assert metric.estimated_cost == Money(Decimal("0.00600"))
    assert metric.saved_cost == Money.zero()


def test_metric_persistence_failure_does_not_change_http_response() -> None:
    metrics_repository = FakeMetricsRepository(should_fail=True)
    provider_client = FakeProviderClient(
        response=ProviderResponse(
            status_code=200,
            body={"id": "completion-1", "choices": []},
            provider="fake",
        )
    )
    client = TestClient(
        create_app(
            _settings(),
            provider_client=provider_client,
            metrics_repository=metrics_repository,
            pricing_catalog=_pricing_catalog(),
        )
    )

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json={"model": "test-model", "messages": []},
    )

    assert response.status_code == 200
    assert response.json() == {"id": "completion-1", "choices": []}


def test_metric_recorder_logs_structured_context_when_repository_fails(caplog) -> None:
    metric = FinOpsMetric.from_call(
        request_id="request-1",
        model_name="test-model",
        token_usage=TokenUsage(prompt_tokens=1, completion_tokens=1),
        cache_status="MISS",
        latency_ms=10,
        pricing_catalog=_pricing_catalog(),
    )
    metrics_repository = FakeMetricsRepository(should_fail=True)
    recorder = MetricRecorder(metrics_repository)

    with caplog.at_level(logging.ERROR):
        import anyio

        anyio.run(recorder.record_safely, metric)

    record = caplog.records[0]
    assert record.message == "finops_metric_persistence_failed"
    assert record.request_id == "request-1"
    assert record.cache_status == "MISS"
    assert record.model == "test-model"


def _settings() -> AppSettings:
    return AppSettings.from_env({"GATEWAY_API_KEYS": "valid-token"})


def _pricing_catalog() -> PricingCatalog:
    return PricingCatalog(
        {
            "test-model": ModelPrice(
                prompt_per_million_tokens=Decimal("2.00"),
                completion_per_million_tokens=Decimal("8.00"),
                version="test-prices-v1",
            )
        }
    )
