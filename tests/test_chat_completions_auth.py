from typing import Optional

import pytest
from fastapi.testclient import TestClient

from finops_token_saver.api.app import create_app
from finops_token_saver.infrastructure.settings import AppSettings


def create_test_client() -> TestClient:
    settings = AppSettings.from_env({"GATEWAY_API_KEYS": "valid-token"})
    return TestClient(create_app(settings))


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "",
        "Bearer",
        "Bearer ",
        "Basic valid-token",
        "Bearer wrong-token",
    ],
)
def test_chat_completions_rejects_missing_empty_or_invalid_api_key(
    authorization: Optional[str],
) -> None:
    client = create_test_client()
    headers = {}
    if authorization is not None:
        headers["Authorization"] = authorization

    response = client.post("/v1/chat/completions", headers=headers, json={"model": "test"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing gateway API key"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_chat_completions_accepts_valid_api_key() -> None:
    client = create_test_client()

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer valid-token"},
        json={"model": "test"},
    )

    assert response.status_code == 501
    assert response.json() == {
        "error": {
            "message": "Chat completions proxy is not implemented yet",
            "type": "not_implemented",
            "code": "not_implemented",
        }
    }
