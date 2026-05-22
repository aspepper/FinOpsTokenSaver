from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

TOKENS_PER_MILLION = Decimal("1000000")
USD = "USD"
ZERO_USD = Decimal("0")


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int

    def __post_init__(self) -> None:
        if self.prompt_tokens < 0:
            raise ValueError("prompt_tokens must not be negative")
        if self.completion_tokens < 0:
            raise ValueError("completion_tokens must not be negative")


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = USD

    @classmethod
    def zero(cls) -> "Money":
        return cls(ZERO_USD)

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Cannot add money with different currencies")
        return Money(self.amount + other.amount, self.currency)


@dataclass(frozen=True)
class ModelPrice:
    prompt_per_million_tokens: Decimal
    completion_per_million_tokens: Decimal
    version: str


@dataclass(frozen=True)
class CostEstimate:
    prompt_cost: Money
    completion_cost: Money
    total_cost: Money
    model_name: str
    price_version: Optional[str]
    is_model_priced: bool


DEFAULT_MODEL_PRICES: Mapping[str, ModelPrice] = {
    "gpt-4o-mini": ModelPrice(
        prompt_per_million_tokens=Decimal("0.15"),
        completion_per_million_tokens=Decimal("0.60"),
        version="openai-2024-07-18",
    ),
}


class PricingCatalog:
    def __init__(self, prices_by_model: Optional[Mapping[str, ModelPrice]] = None) -> None:
        self._prices_by_model = dict(prices_by_model or DEFAULT_MODEL_PRICES)

    def estimate_cost(self, model_name: str, usage: TokenUsage) -> CostEstimate:
        model_price = self._prices_by_model.get(model_name)
        if model_price is None:
            return CostEstimate(
                prompt_cost=Money.zero(),
                completion_cost=Money.zero(),
                total_cost=Money.zero(),
                model_name=model_name,
                price_version=None,
                is_model_priced=False,
            )

        prompt_cost = _calculate_token_cost(
            token_count=usage.prompt_tokens,
            price_per_million_tokens=model_price.prompt_per_million_tokens,
        )
        completion_cost = _calculate_token_cost(
            token_count=usage.completion_tokens,
            price_per_million_tokens=model_price.completion_per_million_tokens,
        )
        return CostEstimate(
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=prompt_cost + completion_cost,
            model_name=model_name,
            price_version=model_price.version,
            is_model_priced=True,
        )


def _calculate_token_cost(token_count: int, price_per_million_tokens: Decimal) -> Money:
    return Money((Decimal(token_count) / TOKENS_PER_MILLION) * price_per_million_tokens)
