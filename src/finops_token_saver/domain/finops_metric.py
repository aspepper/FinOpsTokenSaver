from dataclasses import dataclass
from typing import Optional

from finops_token_saver.domain.cache_status import CACHE_STATUS_HIT
from finops_token_saver.domain.pricing import Money, PricingCatalog, TokenUsage


@dataclass(frozen=True)
class FinOpsMetric:
    request_id: str
    model_name: str
    token_usage: TokenUsage
    cache_status: str
    estimated_cost: Money
    saved_cost: Money
    latency_ms: int
    price_version: Optional[str]
    is_model_priced: bool

    @classmethod
    def from_call(
        cls,
        request_id: str,
        model_name: str,
        token_usage: TokenUsage,
        cache_status: str,
        latency_ms: int,
        pricing_catalog: PricingCatalog,
    ) -> "FinOpsMetric":
        if not request_id.strip():
            raise ValueError("request_id is required")
        if not model_name.strip():
            raise ValueError("model_name is required")
        if latency_ms < 0:
            raise ValueError("latency_ms must not be negative")

        cost_estimate = pricing_catalog.estimate_cost(model_name, token_usage)
        if cache_status == CACHE_STATUS_HIT:
            estimated_cost = Money.zero()
            saved_cost = cost_estimate.total_cost
        else:
            estimated_cost = cost_estimate.total_cost
            saved_cost = Money.zero()

        return cls(
            request_id=request_id,
            model_name=model_name,
            token_usage=token_usage,
            cache_status=cache_status,
            estimated_cost=estimated_cost,
            saved_cost=saved_cost,
            latency_ms=latency_ms,
            price_version=cost_estimate.price_version,
            is_model_priced=cost_estimate.is_model_priced,
        )
