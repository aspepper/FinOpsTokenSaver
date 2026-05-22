from __future__ import annotations

import json
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import uvicorn

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from finops_token_saver.api.app import create_app  # noqa: E402
from finops_token_saver.application.cache import CacheStore  # noqa: E402
from finops_token_saver.application.provider import ProviderClient  # noqa: E402
from finops_token_saver.domain.provider import ProviderResponse  # noqa: E402
from finops_token_saver.infrastructure.settings import AppSettings  # noqa: E402

SMOKE_GATEWAY_TOKEN = "smoke-local-token"
SMOKE_PAYLOAD = {
    "model": "smoke-model",
    "messages": [{"role": "user", "content": "local smoke prompt"}],
    "temperature": 0,
}
OBSERVABILITY_HEADERS = (
    "X-Request-Id",
    "X-Gateway-Latency-Ms",
    "X-Cache-Status",
    "X-Provider",
    "X-Retry-Count",
)


@dataclass(frozen=True)
class SmokeHttpResponse:
    status_code: int
    headers: dict[str, str]
    body: dict


class SmokeProviderClient(ProviderClient):
    def __init__(self) -> None:
        self.call_count = 0

    async def create_chat_completion(self, payload: dict) -> ProviderResponse:
        self.call_count += 1
        return ProviderResponse(
            status_code=200,
            provider="smoke",
            body={
                "id": "smoke-completion",
                "object": "chat.completion",
                "model": payload.get("model", "smoke-model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "smoke-ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            },
        )


class SmokeCacheStore(CacheStore):
    def __init__(self) -> None:
        self._items: dict[str, dict] = {}

    async def get(self, key: str) -> dict | None:
        return self._items.get(key)

    async def set(self, key: str, value: dict, ttl_seconds: int) -> None:
        self._items[key] = value


def main() -> int:
    provider_client = SmokeProviderClient()
    app = create_app(
        settings=AppSettings.from_env({"GATEWAY_API_KEYS": SMOKE_GATEWAY_TOKEN}),
        provider_client=provider_client,
        cache_store=SmokeCacheStore(),
    )
    port = _free_tcp_port()
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            access_log=False,
            log_level="warning",
            lifespan="off",
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    try:
        health = _wait_for_health(base_url)
        unauthenticated = _request("POST", f"{base_url}/v1/chat/completions", SMOKE_PAYLOAD)
        cache_miss = _request(
            "POST",
            f"{base_url}/v1/chat/completions",
            SMOKE_PAYLOAD,
            headers={"Authorization": f"Bearer {SMOKE_GATEWAY_TOKEN}"},
        )
        cache_hit = _request(
            "POST",
            f"{base_url}/v1/chat/completions",
            SMOKE_PAYLOAD,
            headers={"Authorization": f"Bearer {SMOKE_GATEWAY_TOKEN}"},
        )

        _print_result("health", health)
        _print_result("unauthenticated", unauthenticated)
        _print_result("cache_miss", cache_miss)
        _print_result("cache_hit", cache_hit)
        _assert_smoke_result(health, unauthenticated, cache_miss, cache_hit, provider_client)
        print("smoke_test=passed")
        return 0
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def _request(
    method: str,
    url: str,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
) -> SmokeHttpResponse:
    request_headers = {"Content-Type": "application/json"}
    request_headers.update(headers or {})
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=request_headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return _read_response(response.status, dict(response.headers), response.read())
    except urllib.error.HTTPError as error:
        return _read_response(error.code, dict(error.headers), error.read())


def _wait_for_health(base_url: str) -> SmokeHttpResponse:
    deadline = time.monotonic() + 5
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return _request("GET", f"{base_url}/health")
        except urllib.error.URLError as error:
            last_error = error
            time.sleep(0.05)
    raise RuntimeError(f"Local application did not start: {last_error}")


def _read_response(status_code: int, headers: dict[str, str], raw_body: bytes) -> SmokeHttpResponse:
    normalized_headers = {key.lower(): value for key, value in headers.items()}
    if raw_body:
        body = json.loads(raw_body.decode("utf-8"))
    else:
        body = {}
    return SmokeHttpResponse(status_code=status_code, headers=normalized_headers, body=body)


def _print_result(name: str, response: SmokeHttpResponse) -> None:
    parts = [name, f"status={response.status_code}"]
    for header in OBSERVABILITY_HEADERS:
        value = response.headers.get(header.lower())
        if value is not None:
            parts.append(f"{header.lower()}={value}")
    print(" ".join(parts))


def _assert_smoke_result(
    health: SmokeHttpResponse,
    unauthenticated: SmokeHttpResponse,
    cache_miss: SmokeHttpResponse,
    cache_hit: SmokeHttpResponse,
    provider_client: SmokeProviderClient,
) -> None:
    expected = [
        ("health", health.status_code == 200),
        ("unauthenticated", unauthenticated.status_code == 401),
        ("cache_miss", cache_miss.status_code == 200),
        ("cache_miss_header", cache_miss.headers.get("x-cache-status") == "MISS"),
        ("cache_hit", cache_hit.status_code == 200),
        ("cache_hit_header", cache_hit.headers.get("x-cache-status") == "HIT"),
        ("provider_called_once", provider_client.call_count == 1),
    ]
    failures = [name for name, passed in expected if not passed]
    if failures:
        raise RuntimeError(f"Smoke test failed: {', '.join(failures)}")


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


if __name__ == "__main__":
    raise SystemExit(main())
