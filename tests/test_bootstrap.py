from __future__ import annotations

import pytest

from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.application.retrying_provider import RetryingProviderClient
from finops_token_saver.domain.provider import ProviderError, ProviderResponse
from finops_token_saver.infrastructure.bootstrap import (
    build_dependencies,
    create_configured_app,
)
from finops_token_saver.infrastructure.postgres_metrics import PostgresMetricsRepository
from finops_token_saver.infrastructure.provider import HttpClient, UnconfiguredProviderClient
from finops_token_saver.infrastructure.redis_cache import RedisCacheStore
from finops_token_saver.infrastructure.settings import AppSettings, ConfigurationError


class FakeProviderClient(ProviderClient):
    def __init__(self, outcomes: list[ProviderError | ProviderResponse]) -> None:
        self.requests: list[dict] = []
        self._outcomes = outcomes

    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        self.requests.append(payload)
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, ProviderError):
            raise outcome
        return outcome


class FakeSleeper:
    def __init__(self) -> None:
        self.delays: list[float] = []

    async def sleep(self, delay_seconds: float) -> None:
        self.delays.append(delay_seconds)


class CapturingOpenAIProviderFactory:
    def __init__(self, provider_client: ProviderClient) -> None:
        self.provider_client = provider_client
        self.calls: list[dict] = []

    def __call__(
        self,
        *,
        api_key: str,
        timeout_seconds: float,
        http_client: HttpClient | None = None,
    ) -> ProviderClient:
        self.calls.append(
            {
                "api_key": api_key,
                "timeout_seconds": timeout_seconds,
                "http_client": http_client,
            }
        )
        return self.provider_client


def test_development_bootstrap_uses_safe_local_defaults_without_real_dependencies() -> None:
    settings = AppSettings.from_env({})

    dependencies = build_dependencies(settings)

    assert isinstance(dependencies.provider_client, UnconfiguredProviderClient)
    assert dependencies.cache_store is None
    assert dependencies.metrics_repository is None


def test_development_bootstrap_uses_real_dependencies_when_configured() -> None:
    settings = AppSettings.from_env(
        {
            "APP_ENV": "development",
            "GATEWAY_API_KEYS": "gateway-secret",
            "OPENAI_API_KEY": "provider-secret",
            "REDIS_URL": "redis://cache.example:6379/0",
            "DATABASE_URL": "postgresql://db.example/app",
        }
    )

    dependencies = build_dependencies(settings)

    assert isinstance(dependencies.provider_client, RetryingProviderClient)
    assert isinstance(dependencies.cache_store, RedisCacheStore)
    assert isinstance(dependencies.metrics_repository, PostgresMetricsRepository)


def test_staging_requires_real_configuration_without_exposing_secret_values() -> None:
    with pytest.raises(ConfigurationError) as error:
        AppSettings.from_env(
            {
                "APP_ENV": "staging",
                "GATEWAY_API_KEYS": "gateway-secret",
                "OPENAI_API_KEY": "provider-secret",
            }
        )

    message = str(error.value)

    assert "REDIS_URL" in message
    assert "DATABASE_URL" in message
    assert "gateway-secret" not in message
    assert "provider-secret" not in message


def test_production_bootstrap_mounts_real_dependencies_without_opening_connections() -> None:
    settings = AppSettings.from_env(
        {
            "APP_ENV": "production",
            "GATEWAY_API_KEYS": "gateway-secret",
            "OPENAI_API_KEY": "provider-secret",
            "REDIS_URL": "redis://cache.example:6379/0",
            "DATABASE_URL": "postgresql://db.example/app",
        }
    )

    dependencies = build_dependencies(settings)

    assert isinstance(dependencies.provider_client, RetryingProviderClient)
    assert isinstance(dependencies.cache_store, RedisCacheStore)
    assert isinstance(dependencies.metrics_repository, PostgresMetricsRepository)


def test_configured_app_uses_bootstrapped_dependencies() -> None:
    settings = AppSettings.from_env(
        {
            "APP_ENV": "development",
            "GATEWAY_API_KEYS": "gateway-secret",
            "OPENAI_API_KEY": "provider-secret",
            "REDIS_URL": "redis://cache.example:6379/0",
            "DATABASE_URL": "postgresql://db.example/app",
        }
    )

    app = create_configured_app(settings)

    assert app.state.settings == settings
    assert isinstance(app.state.provider_client, RetryingProviderClient)
    assert isinstance(app.state.cache_store, RedisCacheStore)
    assert isinstance(app.state.metrics_repository, PostgresMetricsRepository)


@pytest.mark.anyio
async def test_bootstrapped_openai_provider_succeeds_after_retry_without_real_sleep() -> None:
    response = ProviderResponse(status_code=200, body={"id": "ok"}, provider="openai")
    provider_client = FakeProviderClient([_provider_error(429), response])
    factory = CapturingOpenAIProviderFactory(provider_client)
    sleeper = FakeSleeper()
    settings = AppSettings.from_env(
        {
            "GATEWAY_API_KEYS": "gateway-secret",
            "OPENAI_API_KEY": "provider-secret",
            "MAX_RETRY_ATTEMPTS": "3",
            "PROVIDER_TIMEOUT_SECONDS": "7",
        }
    )

    dependencies = build_dependencies(
        settings,
        openai_provider_factory=factory,
        sleep=sleeper.sleep,
    )
    result = await dependencies.provider_client.create_chat_completion({"model": "test-model"})

    assert result == response
    assert len(provider_client.requests) == 2
    assert sleeper.delays
    assert factory.calls == [
        {
            "api_key": "provider-secret",
            "timeout_seconds": 7.0,
            "http_client": None,
        }
    ]


@pytest.mark.anyio
async def test_bootstrapped_openai_provider_raises_final_error_after_configured_attempts() -> None:
    final_error = _provider_error(503, code="final_error")
    provider_client = FakeProviderClient([_provider_error(503), final_error])
    sleeper = FakeSleeper()
    settings = AppSettings.from_env(
        {
            "GATEWAY_API_KEYS": "gateway-secret",
            "OPENAI_API_KEY": "provider-secret",
            "MAX_RETRY_ATTEMPTS": "2",
        }
    )

    dependencies = build_dependencies(
        settings,
        openai_provider_factory=CapturingOpenAIProviderFactory(provider_client),
        sleep=sleeper.sleep,
    )

    with pytest.raises(ProviderError) as error:
        await dependencies.provider_client.create_chat_completion({"model": "test-model"})

    assert error.value is final_error
    assert len(provider_client.requests) == 2
    assert len(sleeper.delays) == 1


@pytest.mark.anyio
async def test_bootstrapped_openai_provider_does_not_retry_client_4xx_errors() -> None:
    provider_client = FakeProviderClient([_provider_error(400)])
    sleeper = FakeSleeper()
    settings = AppSettings.from_env(
        {
            "GATEWAY_API_KEYS": "gateway-secret",
            "OPENAI_API_KEY": "provider-secret",
            "MAX_RETRY_ATTEMPTS": "3",
        }
    )

    dependencies = build_dependencies(
        settings,
        openai_provider_factory=CapturingOpenAIProviderFactory(provider_client),
        sleep=sleeper.sleep,
    )

    with pytest.raises(ProviderError):
        await dependencies.provider_client.create_chat_completion({"model": "test-model"})

    assert len(provider_client.requests) == 1
    assert sleeper.delays == []


def _provider_error(status_code: int, code: str | None = None) -> ProviderError:
    return ProviderError(
        status_code=status_code,
        error_type="provider_error",
        safe_message="Provider failed",
        code=code,
    )
