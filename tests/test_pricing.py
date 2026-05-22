from decimal import Decimal

import pytest

from finops_token_saver.domain.pricing import (
    ModelPrice,
    Money,
    PricingCatalog,
    TokenUsage,
)


def test_pricing_catalog_calculates_prompt_completion_and_total_cost() -> None:
    catalog = PricingCatalog(
        {
            "test-model": ModelPrice(
                prompt_per_million_tokens=Decimal("2.00"),
                completion_per_million_tokens=Decimal("8.00"),
                version="test-prices-v1",
            )
        }
    )
    usage = TokenUsage(prompt_tokens=1_000, completion_tokens=500)

    estimate = catalog.estimate_cost("test-model", usage)

    assert estimate.prompt_cost == Money(Decimal("0.00200"))
    assert estimate.completion_cost == Money(Decimal("0.00400"))
    assert estimate.total_cost == Money(Decimal("0.00600"))
    assert estimate.price_version == "test-prices-v1"
    assert estimate.is_model_priced is True


def test_unknown_model_returns_zero_cost_without_failing() -> None:
    catalog = PricingCatalog({})

    estimate = catalog.estimate_cost(
        "unknown-model",
        TokenUsage(prompt_tokens=1_000, completion_tokens=1_000),
    )

    assert estimate.prompt_cost == Money.zero()
    assert estimate.completion_cost == Money.zero()
    assert estimate.total_cost == Money.zero()
    assert estimate.model_name == "unknown-model"
    assert estimate.price_version is None
    assert estimate.is_model_priced is False


def test_default_catalog_has_versioned_initial_prices() -> None:
    catalog = PricingCatalog()

    estimate = catalog.estimate_cost(
        "gpt-4o-mini",
        TokenUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000),
    )

    assert estimate.prompt_cost == Money(Decimal("0.15"))
    assert estimate.completion_cost == Money(Decimal("0.60"))
    assert estimate.total_cost == Money(Decimal("0.75"))
    assert estimate.price_version == "openai-2024-07-18"


def test_token_usage_rejects_negative_values() -> None:
    with pytest.raises(ValueError, match="prompt_tokens must not be negative"):
        TokenUsage(prompt_tokens=-1, completion_tokens=0)


def test_money_rejects_adding_different_currencies() -> None:
    with pytest.raises(ValueError, match="different currencies"):
        Money(Decimal("1.00"), currency="USD") + Money(Decimal("1.00"), currency="BRL")
