from decimal import Decimal

import pytest

from finops_token_saver.domain.cache_status import CACHE_STATUS_HIT, CACHE_STATUS_MISS
from finops_token_saver.domain.finops_metric import FinOpsMetric
from finops_token_saver.domain.pricing import ModelPrice, Money, PricingCatalog, TokenUsage


def test_finops_metric_for_cache_miss_records_estimated_cost_and_no_savings() -> None:
    metric = FinOpsMetric.from_call(
        request_id="request-1",
        model_name="test-model",
        token_usage=TokenUsage(prompt_tokens=1_000, completion_tokens=500),
        cache_status=CACHE_STATUS_MISS,
        latency_ms=120,
        pricing_catalog=_pricing_catalog(),
    )

    assert metric.request_id == "request-1"
    assert metric.model_name == "test-model"
    assert metric.token_usage == TokenUsage(prompt_tokens=1_000, completion_tokens=500)
    assert metric.cache_status == CACHE_STATUS_MISS
    assert metric.estimated_cost == Money(Decimal("0.00600"))
    assert metric.saved_cost == Money.zero()
    assert metric.latency_ms == 120
    assert metric.price_version == "test-prices-v1"
    assert metric.is_model_priced is True


def test_finops_metric_for_cache_hit_records_savings_and_zero_estimated_cost() -> None:
    metric = FinOpsMetric.from_call(
        request_id="request-2",
        model_name="test-model",
        token_usage=TokenUsage(prompt_tokens=1_000, completion_tokens=500),
        cache_status=CACHE_STATUS_HIT,
        latency_ms=12,
        pricing_catalog=_pricing_catalog(),
    )

    assert metric.estimated_cost == Money.zero()
    assert metric.saved_cost == Money(Decimal("0.00600"))
    assert metric.cache_status == CACHE_STATUS_HIT
    assert metric.latency_ms == 12


def test_finops_metric_for_unknown_model_keeps_zero_costs_without_failing() -> None:
    metric = FinOpsMetric.from_call(
        request_id="request-3",
        model_name="unknown-model",
        token_usage=TokenUsage(prompt_tokens=1_000, completion_tokens=500),
        cache_status=CACHE_STATUS_MISS,
        latency_ms=50,
        pricing_catalog=PricingCatalog({}),
    )

    assert metric.estimated_cost == Money.zero()
    assert metric.saved_cost == Money.zero()
    assert metric.price_version is None
    assert metric.is_model_priced is False


def test_finops_metric_requires_request_id_model_name_and_valid_latency() -> None:
    with pytest.raises(ValueError, match="request_id is required"):
        FinOpsMetric.from_call(
            request_id=" ",
            model_name="test-model",
            token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0),
            cache_status=CACHE_STATUS_MISS,
            latency_ms=0,
            pricing_catalog=_pricing_catalog(),
        )

    with pytest.raises(ValueError, match="model_name is required"):
        FinOpsMetric.from_call(
            request_id="request-1",
            model_name=" ",
            token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0),
            cache_status=CACHE_STATUS_MISS,
            latency_ms=0,
            pricing_catalog=_pricing_catalog(),
        )

    with pytest.raises(ValueError, match="latency_ms must not be negative"):
        FinOpsMetric.from_call(
            request_id="request-1",
            model_name="test-model",
            token_usage=TokenUsage(prompt_tokens=0, completion_tokens=0),
            cache_status=CACHE_STATUS_MISS,
            latency_ms=-1,
            pricing_catalog=_pricing_catalog(),
        )


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
