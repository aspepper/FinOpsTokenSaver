import time
from typing import Optional

from fastapi import BackgroundTasks, Body, Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from finops_token_saver.api.auth import require_gateway_auth
from finops_token_saver.api.chat_completions import (
    get_chat_completion_use_case,
    provider_error_response,
)
from finops_token_saver.api.observability import (
    CACHE_STATUS_HEADER,
    PROVIDER_HEADER,
    RETRY_COUNT_HEADER,
    add_observability_middleware,
    get_request_id,
)
from finops_token_saver.application.cache import CacheStore
from finops_token_saver.application.chat_completion import ForwardChatCompletion
from finops_token_saver.application.metrics import (
    MetricRecorder,
    MetricsRepository,
    build_finops_metric,
)
from finops_token_saver.application.provider import ProviderClient
from finops_token_saver.domain.pricing import PricingCatalog
from finops_token_saver.domain.provider import ProviderError
from finops_token_saver.infrastructure.provider import provider_client_from_settings
from finops_token_saver.infrastructure.settings import AppSettings

SERVICE_NAME = "finops-token-saver"
CHAT_COMPLETION_BODY = Body(...)
CHAT_COMPLETION_USE_CASE = Depends(get_chat_completion_use_case)


def create_app(
    settings: Optional[AppSettings] = None,
    provider_client: Optional[ProviderClient] = None,
    cache_store: Optional[CacheStore] = None,
    metrics_repository: Optional[MetricsRepository] = None,
    pricing_catalog: Optional[PricingCatalog] = None,
) -> FastAPI:
    app_settings = settings or AppSettings.from_env()
    app = FastAPI(title="FinOpsTokenSaver", version="0.1.0")
    app.state.settings = app_settings
    app.state.provider_client = provider_client or provider_client_from_settings(app_settings)
    app.state.cache_store = cache_store
    app.state.metrics_repository = metrics_repository
    app.state.pricing_catalog = pricing_catalog or PricingCatalog()
    add_observability_middleware(app)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE_NAME}

    @app.post("/v1/chat/completions", dependencies=[Depends(require_gateway_auth)])
    async def chat_completions(
        request: Request,
        background_tasks: BackgroundTasks,
        payload: dict = CHAT_COMPLETION_BODY,
        use_case: ForwardChatCompletion = CHAT_COMPLETION_USE_CASE,
    ) -> JSONResponse:
        request_id = get_request_id(request)
        started_at = time.perf_counter()
        try:
            result = await use_case.execute(payload, headers=request.headers)
        except ProviderError as error:
            return provider_error_response(error)

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        if app.state.metrics_repository is not None:
            metric = build_finops_metric(
                request_id=request_id,
                payload=payload,
                result=result,
                latency_ms=latency_ms,
                pricing_catalog=app.state.pricing_catalog,
            )
            background_tasks.add_task(
                MetricRecorder(app.state.metrics_repository).record_safely,
                metric,
            )

        return JSONResponse(
            status_code=result.provider_response.status_code,
            content=result.provider_response.body,
            headers={
                CACHE_STATUS_HEADER: result.cache_status,
                PROVIDER_HEADER: result.provider_response.provider,
                RETRY_COUNT_HEADER: "0",
            },
        )

    return app
