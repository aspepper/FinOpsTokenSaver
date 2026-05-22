from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI

from finops_token_saver.api.app import create_app
from finops_token_saver.application.cache import CacheStore
from finops_token_saver.application.metrics import MetricsRepository
from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.infrastructure.postgres_metrics import PostgresMetricsRepository
from finops_token_saver.infrastructure.provider import (
    OpenAIProviderClient,
    UnconfiguredProviderClient,
)
from finops_token_saver.infrastructure.redis_cache import RedisCacheStore
from finops_token_saver.infrastructure.settings import (
    DEFAULT_DATABASE_URL,
    DEFAULT_ENVIRONMENT,
    DEFAULT_REDIS_URL,
    ENVIRONMENTS_REQUIRING_SECRETS,
    AppSettings,
)


@dataclass(frozen=True)
class BootstrappedDependencies:
    provider_client: ProviderClient
    cache_store: CacheStore | None
    metrics_repository: MetricsRepository | None


def create_configured_app(settings: AppSettings | None = None) -> FastAPI:
    app_settings = settings or AppSettings.from_env()
    dependencies = build_dependencies(app_settings)
    return create_app(
        settings=app_settings,
        provider_client=dependencies.provider_client,
        cache_store=dependencies.cache_store,
        metrics_repository=dependencies.metrics_repository,
    )


def build_dependencies(settings: AppSettings) -> BootstrappedDependencies:
    return BootstrappedDependencies(
        provider_client=_provider_client(settings),
        cache_store=_cache_store(settings),
        metrics_repository=_metrics_repository(settings),
    )


def _provider_client(settings: AppSettings) -> ProviderClient:
    if settings.openai_api_key is None:
        return UnconfiguredProviderClient()
    return OpenAIProviderClient(
        api_key=settings.openai_api_key,
        timeout_seconds=settings.provider_timeout_seconds,
    )


def _cache_store(settings: AppSettings) -> CacheStore | None:
    if not _has_real_redis_url(settings):
        return None
    return RedisCacheStore.from_url(settings.redis_url)


def _metrics_repository(settings: AppSettings) -> MetricsRepository | None:
    if not _has_real_database_url(settings):
        return None
    return PostgresMetricsRepository.from_database_url(settings.database_url)


def _has_real_redis_url(settings: AppSettings) -> bool:
    return settings.environment != DEFAULT_ENVIRONMENT or settings.redis_url != DEFAULT_REDIS_URL


def _has_real_database_url(settings: AppSettings) -> bool:
    return (
        settings.environment in ENVIRONMENTS_REQUIRING_SECRETS
        or settings.database_url != DEFAULT_DATABASE_URL
    )
