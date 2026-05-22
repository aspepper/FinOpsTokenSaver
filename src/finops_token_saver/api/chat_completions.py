from fastapi import Request
from fastapi.responses import JSONResponse

from finops_token_saver.application.chat_completion import ForwardChatCompletion
from finops_token_saver.domain.provider import ProviderError


def get_chat_completion_use_case(request: Request) -> ForwardChatCompletion:
    return ForwardChatCompletion(request.app.state.provider_client)


def provider_error_response(error: ProviderError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "message": error.safe_message,
                "type": error.error_type,
                "code": error.code or error.error_type,
            }
        },
    )
