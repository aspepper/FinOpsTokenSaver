import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Optional

DEFAULT_CACHE_TTL_SECONDS = 43_200
DEFAULT_DATABASE_URL = "postgresql://localhost:5432/finops_token_saver"
DEFAULT_ENVIRONMENT = "development"
DEFAULT_GATEWAY_API_KEYS = ("dev-gateway-key",)
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MAX_RETRY_ATTEMPTS = 3
DEFAULT_PROVIDER_TIMEOUT_SECONDS = 30.0
DEFAULT_REDIS_URL = "redis://localhost:6379/0"

ENVIRONMENTS_REQUIRING_SECRETS = {"production", "staging"}
REQUIRED_SECRET_VARIABLES = (
    "GATEWAY_API_KEYS",
    "OPENAI_API_KEY",
    "REDIS_URL",
    "DATABASE_URL",
)
SUPPORTED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class ConfigurationError(RuntimeError):
    """Raised when environment configuration is missing or invalid."""


@dataclass(frozen=True)
class AppSettings:
    environment: str
    gateway_api_keys: tuple[str, ...]
    openai_api_key: Optional[str]
    redis_url: str
    database_url: str
    cache_ttl_seconds: int
    provider_timeout_seconds: float
    max_retry_attempts: int
    log_level: str

    @classmethod
    def from_env(cls, environ: Optional[Mapping[str, str]] = None) -> "AppSettings":
        env = os.environ if environ is None else environ
        environment = _read_text(env, "APP_ENV", DEFAULT_ENVIRONMENT).lower()
        _ensure_required_secrets(env, environment)

        return cls(
            environment=environment,
            gateway_api_keys=_read_gateway_api_keys(env, environment),
            openai_api_key=_read_optional_text(env, "OPENAI_API_KEY"),
            redis_url=_read_text(env, "REDIS_URL", DEFAULT_REDIS_URL),
            database_url=_read_text(env, "DATABASE_URL", DEFAULT_DATABASE_URL),
            cache_ttl_seconds=_read_positive_int(
                env,
                "CACHE_TTL_SECONDS",
                DEFAULT_CACHE_TTL_SECONDS,
            ),
            provider_timeout_seconds=_read_positive_float(
                env,
                "PROVIDER_TIMEOUT_SECONDS",
                DEFAULT_PROVIDER_TIMEOUT_SECONDS,
            ),
            max_retry_attempts=_read_positive_int(
                env,
                "MAX_RETRY_ATTEMPTS",
                DEFAULT_MAX_RETRY_ATTEMPTS,
            ),
            log_level=_read_log_level(env),
        )


def _ensure_required_secrets(env: Mapping[str, str], environment: str) -> None:
    if environment not in ENVIRONMENTS_REQUIRING_SECRETS:
        return

    missing_names = [
        name for name in REQUIRED_SECRET_VARIABLES if not _read_optional_text(env, name)
    ]
    if missing_names:
        missing = ", ".join(sorted(missing_names))
        raise ConfigurationError(f"Missing required environment variables: {missing}")


def _read_gateway_api_keys(env: Mapping[str, str], environment: str) -> tuple[str, ...]:
    raw_value = _read_optional_text(env, "GATEWAY_API_KEYS")
    if raw_value is None:
        if environment in ENVIRONMENTS_REQUIRING_SECRETS:
            raise ConfigurationError("Missing required environment variables: GATEWAY_API_KEYS")
        return DEFAULT_GATEWAY_API_KEYS

    keys = tuple(part.strip() for part in raw_value.split(",") if part.strip())
    if not keys:
        raise ConfigurationError("GATEWAY_API_KEYS must contain at least one key")
    return keys


def _read_text(env: Mapping[str, str], name: str, default: str) -> str:
    value = _read_optional_text(env, name)
    return default if value is None else value


def _read_optional_text(env: Mapping[str, str], name: str) -> Optional[str]:
    value = env.get(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _read_positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw_value = _read_optional_text(env, name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a positive integer") from error

    if value <= 0:
        raise ConfigurationError(f"{name} must be a positive integer")
    return value


def _read_positive_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw_value = _read_optional_text(env, name)
    if raw_value is None:
        return default

    try:
        value = float(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be a positive number") from error

    if value <= 0:
        raise ConfigurationError(f"{name} must be a positive number")
    return value


def _read_log_level(env: Mapping[str, str]) -> str:
    log_level = _read_text(env, "LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    if log_level not in SUPPORTED_LOG_LEVELS:
        raise ConfigurationError("LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL")
    return log_level
