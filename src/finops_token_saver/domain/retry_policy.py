import random
from dataclasses import dataclass
from typing import Optional

from finops_token_saver.domain.provider import ProviderError

DEFAULT_BASE_DELAY_SECONDS = 2.0
DEFAULT_MAX_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {408, 429}
SERVER_ERROR_STATUS_CODE_START = 500
SERVER_ERROR_STATUS_CODE_END = 599


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = DEFAULT_MAX_ATTEMPTS
    base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS
    jitter_seconds: float = 1.0
    random_source: Optional[random.Random] = None

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if self.base_delay_seconds <= 0:
            raise ValueError("base_delay_seconds must be positive")
        if self.jitter_seconds < 0:
            raise ValueError("jitter_seconds must not be negative")

    def should_retry(self, error: ProviderError, attempt_number: int) -> bool:
        return attempt_number < self.max_attempts and self.is_retryable_error(error)

    def is_retryable_error(self, error: ProviderError) -> bool:
        return (
            error.status_code in RETRYABLE_STATUS_CODES
            or SERVER_ERROR_STATUS_CODE_START <= error.status_code <= SERVER_ERROR_STATUS_CODE_END
        )

    def delay_for_attempt(self, attempt_number: int) -> float:
        if attempt_number <= 0:
            raise ValueError("attempt_number must be positive")

        jitter = self._random().uniform(0, self.jitter_seconds)
        return self.base_delay_seconds**attempt_number + jitter

    def _random(self) -> random.Random:
        return self.random_source or random
