from typing import Optional

from fastapi import Header, HTTPException, Request, status

from finops_token_saver.domain.authentication import GatewayCredentialValidator

AUTHENTICATE_HEADER = {"WWW-Authenticate": "Bearer"}
UNAUTHORIZED_MESSAGE = "Invalid or missing gateway API key"


async def require_gateway_auth(
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> None:
    settings = request.app.state.settings
    validator = GatewayCredentialValidator(settings.gateway_api_keys)

    if validator.is_authorized_header(authorization):
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=UNAUTHORIZED_MESSAGE,
        headers=AUTHENTICATE_HEADER,
    )
