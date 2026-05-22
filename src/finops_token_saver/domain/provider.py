from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ProviderResponse:
    status_code: int
    body: dict
    provider: str
    retry_count: int = 0


class ProviderError(RuntimeError):
    def __init__(
        self,
        status_code: int,
        error_type: str,
        safe_message: str,
        code: Optional[str] = None,
        retry_count: int = 0,
    ) -> None:
        super().__init__(safe_message)
        self.status_code = status_code
        self.error_type = error_type
        self.safe_message = safe_message
        self.code = code
        self.retry_count = retry_count


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    pass
