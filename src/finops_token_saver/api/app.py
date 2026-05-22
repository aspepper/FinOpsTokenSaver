from typing import Optional

from fastapi import Body, Depends, FastAPI
from fastapi.responses import JSONResponse

from finops_token_saver.api.auth import require_gateway_auth
from finops_token_saver.api.chat_completions import (
    get_chat_completion_use_case,
    provider_error_response,
)
from finops_token_saver.application.chat_completion import ForwardChatCompletion
from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.domain.provider import ProviderError
from finops_token_saver.infrastructure.provider import UnconfiguredProviderClient
from finops_token_saver.infrastructure.settings import AppSettings

SERVICE_NAME = "finops-token-saver"
CHAT_COMPLETION_BODY = Body(...)
CHAT_COMPLETION_USE_CASE = Depends(get_chat_completion_use_case)


def create_app(
    settings: Optional[AppSettings] = None,
    provider_client: Optional[ProviderClient] = None,
) -> FastAPI:
    app_settings = settings or AppSettings.from_env()
    app = FastAPI(title="FinOpsTokenSaver", version="0.1.0")
    app.state.settings = app_settings
    app.state.provider_client = provider_client or UnconfiguredProviderClient()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    @app.post("/v1/chat/completions", dependencies=[Depends(require_gateway_auth)])
    async def chat_completions(
        payload: dict = CHAT_COMPLETION_BODY,
        use_case: ForwardChatCompletion = CHAT_COMPLETION_USE_CASE,
    ) -> JSONResponse:
        try:
            provider_response = await use_case.execute(payload)
        except ProviderError as error:
            return provider_error_response(error)

        return JSONResponse(
            status_code=provider_response.status_code,
            content=provider_response.body,
        )

    return app
