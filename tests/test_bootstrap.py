from __future__ import annotations

import pytest

from finops_token_saver.infrastructure.bootstrap import (
    build_dependencies,
    create_configured_app,
)
from finops_token_saver.infrastructure.postgres_metrics import PostgresMetricsRepository
from finops_token_saver.infrastructure.provider import (
    OpenAIProviderClient,
    UnconfiguredProviderClient,
)
from finops_token_saver.infrastructure.redis_cache import RedisCacheStore
from finops_token_saver.infrastructure.settings import AppSettings, ConfigurationError


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

    assert isinstance(dependencies.provider_client, OpenAIProviderClient)
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

    assert isinstance(dependencies.provider_client, OpenAIProviderClient)
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
    assert isinstance(app.state.provider_client, OpenAIProviderClient)
    assert isinstance(app.state.cache_store, RedisCacheStore)
    assert isinstance(app.state.metrics_repository, PostgresMetricsRepository)
