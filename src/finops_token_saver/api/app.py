from typing import Optional

from fastapi import FastAPI

from finops_token_saver.infrastructure.settings import AppSettings


def create_app(settings: Optional[AppSettings] = None) -> FastAPI:
    app_settings = settings or AppSettings.from_env()
    app = FastAPI(title="FinOpsTokenSaver", version="0.1.0")
    app.state.settings = app_settings

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
