from fastapi import Request
from fastapi.responses import JSONResponse

from finops_token_saver.application.chat_completion import ForwardChatCompletion
from finops_token_saver.domain.cache_status import CACHE_STATUS_BYPASS
from finops_token_saver.domain.provider import ProviderError


def get_chat_completion_use_case(request: Request) -> ForwardChatCompletion:
    return ForwardChatCompletion(
        provider_client=request.app.state.provider_client,
        cache_store=request.app.state.cache_store,
        cache_ttl_seconds=request.app.state.settings.cache_ttl_seconds,
    )


def provider_error_response(error: ProviderError, request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        headers={"X-Cache-Status": CACHE_STATUS_BYPASS, "X-Request-Id": request_id},
        content={
            "error": {
                "message": error.safe_message,
                "type": error.error_type,
                "code": error.code or error.error_type,
            }
        },
    )
