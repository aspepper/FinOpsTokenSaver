from typing import Optional

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse

from finops_token_saver.api.auth import require_gateway_auth
from finops_token_saver.infrastructure.settings import AppSettings

SERVICE_NAME = "finops-token-saver"


def create_app(settings: Optional[AppSettings] = None) -> FastAPI:
    app_settings = settings or AppSettings.from_env()
    app = FastAPI(title="FinOpsTokenSaver", version="0.1.0")
    app.state.settings = app_settings

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    @app.post("/v1/chat/completions", dependencies=[Depends(require_gateway_auth)])
    async def chat_completions() -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content={
                "error": {
                    "message": "Chat completions proxy is not implemented yet",
                    "type": "not_implemented",
                    "code": "not_implemented",
                }
            },
        )

    return app
