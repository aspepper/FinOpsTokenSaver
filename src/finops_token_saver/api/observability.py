import logging
import time
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-Id"
GATEWAY_LATENCY_HEADER = "X-Gateway-Latency-Ms"
PROVIDER_HEADER = "X-Provider"
RETRY_COUNT_HEADER = "X-Retry-Count"
CACHE_STATUS_HEADER = "X-Cache-Status"

DEFAULT_PROVIDER_HEADER = "unknown"
DEFAULT_RETRY_COUNT = "0"

LOGGER_NAME = "finops_token_saver.api"


def add_observability_middleware(
    app: FastAPI,
    logger: Optional[logging.Logger] = None,
) -> None:
    request_logger = logger or logging.getLogger(LOGGER_NAME)

    @app.middleware("http")
    async def observe_request(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = _request_id_from_header(request) or str(uuid4())
        request.state.request_id = request_id

        started_at = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        request.state.gateway_latency_ms = latency_ms

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[GATEWAY_LATENCY_HEADER] = str(latency_ms)
        _log_response(request_logger, request, response, latency_ms)
        return response


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def _request_id_from_header(request: Request) -> Optional[str]:
    request_id = request.headers.get(REQUEST_ID_HEADER)
    if request_id is None or not request_id.strip():
        return None
    return request_id.strip()


def _log_response(
    logger: logging.Logger,
    request: Request,
    response: Response,
    latency_ms: int,
) -> None:
    logger.info(
        "gateway_request",
        extra={
            "request_id": get_request_id(request),
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "provider": response.headers.get(PROVIDER_HEADER, DEFAULT_PROVIDER_HEADER),
            "cache_status": response.headers.get(CACHE_STATUS_HEADER),
            "retry_count": response.headers.get(RETRY_COUNT_HEADER, DEFAULT_RETRY_COUNT),
            "latency_ms": latency_ms,
        },
    )
