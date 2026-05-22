import pytest

from finops_token_saver.infrastructure.settings import (
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_DATABASE_URL,
    DEFAULT_GATEWAY_API_KEYS,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_RETRY_ATTEMPTS,
    DEFAULT_PROVIDER_TIMEOUT_SECONDS,
    DEFAULT_REDIS_URL,
    AppSettings,
    ConfigurationError,
)


def test_development_uses_safe_defaults() -> None:
    settings = AppSettings.from_env({})

    assert settings.environment == "development"
    assert settings.gateway_api_keys == DEFAULT_GATEWAY_API_KEYS
    assert settings.openai_api_key is None
    assert settings.redis_url == DEFAULT_REDIS_URL
    assert settings.database_url == DEFAULT_DATABASE_URL
    assert settings.cache_ttl_seconds == DEFAULT_CACHE_TTL_SECONDS
    assert settings.provider_timeout_seconds == DEFAULT_PROVIDER_TIMEOUT_SECONDS
    assert settings.max_retry_attempts == DEFAULT_MAX_RETRY_ATTEMPTS
    assert settings.log_level == DEFAULT_LOG_LEVEL


def test_reads_configured_environment_values() -> None:
    settings = AppSettings.from_env(
        {
            "APP_ENV": "development",
            "GATEWAY_API_KEYS": "first-key, second-key",
            "OPENAI_API_KEY": "provider-secret",
            "REDIS_URL": "redis://cache.example/0",
            "DATABASE_URL": "postgresql://db.example/app",
            "CACHE_TTL_SECONDS": "60",
            "PROVIDER_TIMEOUT_SECONDS": "2.5",
            "MAX_RETRY_ATTEMPTS": "5",
            "LOG_LEVEL": "warning",
        }
    )

    assert settings.gateway_api_keys == ("first-key", "second-key")
    assert settings.openai_api_key == "provider-secret"
    assert settings.redis_url == "redis://cache.example/0"
    assert settings.database_url == "postgresql://db.example/app"
    assert settings.cache_ttl_seconds == 60
    assert settings.provider_timeout_seconds == 2.5
    assert settings.max_retry_attempts == 5
    assert settings.log_level == "WARNING"


def test_production_requires_secrets_without_printing_secret_values() -> None:
    with pytest.raises(ConfigurationError) as error:
        AppSettings.from_env(
            {
                "APP_ENV": "production",
                "GATEWAY_API_KEYS": "gateway-secret-value",
            }
        )

    message = str(error.value)

    assert "OPENAI_API_KEY" in message
    assert "REDIS_URL" in message
    assert "DATABASE_URL" in message
    assert "gateway-secret-value" not in message


def test_rejects_invalid_numeric_values_without_printing_values() -> None:
    with pytest.raises(ConfigurationError) as error:
        AppSettings.from_env({"CACHE_TTL_SECONDS": "secret-ish-invalid-value"})

    message = str(error.value)

    assert "CACHE_TTL_SECONDS" in message
    assert "secret-ish-invalid-value" not in message
