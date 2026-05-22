import hmac
from typing import Optional

BEARER_SCHEME = "Bearer"


class GatewayCredentialValidator:
    def __init__(self, valid_api_keys: tuple[str, ...]) -> None:
        self._valid_api_keys = valid_api_keys

    def is_authorized_header(self, authorization_header: Optional[str]) -> bool:
        token = self._extract_bearer_token(authorization_header)
        if token is None:
            return False

        return any(hmac.compare_digest(token, valid_key) for valid_key in self._valid_api_keys)

    def _extract_bearer_token(self, authorization_header: Optional[str]) -> Optional[str]:
        if authorization_header is None:
            return None

        scheme, separator, token = authorization_header.strip().partition(" ")
        if separator == "" or scheme != BEARER_SCHEME:
            return None

        stripped_token = token.strip()
        if not stripped_token:
            return None

        return stripped_token
