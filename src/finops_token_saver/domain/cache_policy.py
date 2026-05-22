from collections.abc import Mapping
from typing import Any

from finops_token_saver.domain.provider import ProviderResponse

CACHE_BYPASS_HEADER = "x-cache-bypass"
SUCCESS_STATUS_CODE_START = 200
SUCCESS_STATUS_CODE_END = 299


class CachePolicy:
    def allows_cache_lookup(
        self,
        payload: dict[str, Any],
        headers: Mapping[str, str],
    ) -> bool:
        return not self._is_streaming_request(payload) and not self._has_cache_bypass(headers)

    def allows_cache_storage(
        self,
        payload: dict[str, Any],
        headers: Mapping[str, str],
        response: ProviderResponse,
    ) -> bool:
        return self.allows_cache_lookup(payload, headers) and self._is_success_response(response)

    def _is_streaming_request(self, payload: dict[str, Any]) -> bool:
        return payload.get("stream") is True

    def _has_cache_bypass(self, headers: Mapping[str, str]) -> bool:
        normalized_headers = {name.lower(): value for name, value in headers.items()}
        return normalized_headers.get(CACHE_BYPASS_HEADER, "").strip().lower() == "true"

    def _is_success_response(self, response: ProviderResponse) -> bool:
        return SUCCESS_STATUS_CODE_START <= response.status_code <= SUCCESS_STATUS_CODE_END
