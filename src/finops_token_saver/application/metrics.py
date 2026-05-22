import logging
from typing import Optional, Protocol

from finops_token_saver.application.chat_completion import ChatCompletionResult
from finops_token_saver.domain.finops_metric import FinOpsMetric
from finops_token_saver.domain.pricing import PricingCatalog, TokenUsage


class MetricsRepository(Protocol):
    async def save(self, metric: FinOpsMetric) -> None:
        """Persist a FinOps metric."""


class MetricRecorder:
    def __init__(
        self,
        metrics_repository: MetricsRepository,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._metrics_repository = metrics_repository
        self._logger = logger or logging.getLogger(__name__)

    async def record_safely(self, metric: FinOpsMetric) -> None:
        try:
            await self._metrics_repository.save(metric)
        except Exception:
            self._logger.exception(
                "finops_metric_persistence_failed",
                extra={
                    "request_id": metric.request_id,
                    "cache_status": metric.cache_status,
                    "model": metric.model_name,
                },
            )


def build_finops_metric(
    request_id: str,
    payload: dict,
    result: ChatCompletionResult,
    latency_ms: int,
    pricing_catalog: PricingCatalog,
) -> FinOpsMetric:
    usage = _extract_token_usage(result.provider_response.body)
    return FinOpsMetric.from_call(
        request_id=request_id,
        model_name=str(payload.get("model", "unknown")),
        token_usage=usage,
        cache_status=result.cache_status,
        latency_ms=latency_ms,
        pricing_catalog=pricing_catalog,
    )


def _extract_token_usage(response_body: dict) -> TokenUsage:
    raw_usage = response_body.get("usage", {})
    return TokenUsage(
        prompt_tokens=_read_token_count(raw_usage, "prompt_tokens"),
        completion_tokens=_read_token_count(raw_usage, "completion_tokens"),
    )


def _read_token_count(raw_usage: object, field_name: str) -> int:
    if not isinstance(raw_usage, dict):
        return 0

    value = raw_usage.get(field_name, 0)
    if isinstance(value, int) and value >= 0:
        return value
    return 0
