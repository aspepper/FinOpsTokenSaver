from finops_token_saver.domain.cache_policy import CachePolicy
from finops_token_saver.domain.provider import ProviderResponse


def test_allows_cache_lookup_for_non_streaming_request_without_bypass_header() -> None:
    policy = CachePolicy()

    allowed = policy.allows_cache_lookup(
        payload={"model": "gpt-test", "messages": []},
        headers={},
    )

    assert allowed is True


def test_blocks_cache_lookup_for_streaming_request() -> None:
    policy = CachePolicy()

    allowed = policy.allows_cache_lookup(
        payload={"model": "gpt-test", "messages": [], "stream": True},
        headers={},
    )

    assert allowed is False


def test_blocks_cache_lookup_when_cache_bypass_header_is_true() -> None:
    policy = CachePolicy()

    allowed = policy.allows_cache_lookup(
        payload={"model": "gpt-test", "messages": []},
        headers={"X-Cache-Bypass": "true"},
    )

    assert allowed is False


def test_cache_bypass_header_is_case_insensitive() -> None:
    policy = CachePolicy()

    allowed = policy.allows_cache_lookup(
        payload={"model": "gpt-test", "messages": []},
        headers={"x-cache-bypass": " TRUE "},
    )

    assert allowed is False


def test_allows_cache_storage_for_success_response() -> None:
    policy = CachePolicy()
    response = ProviderResponse(status_code=200, body={"id": "ok"}, provider="fake")

    allowed = policy.allows_cache_storage(
        payload={"model": "gpt-test", "messages": []},
        headers={},
        response=response,
    )

    assert allowed is True


def test_blocks_cache_storage_for_provider_error_response() -> None:
    policy = CachePolicy()
    response = ProviderResponse(status_code=500, body={"error": "provider failed"}, provider="fake")

    allowed = policy.allows_cache_storage(
        payload={"model": "gpt-test", "messages": []},
        headers={},
        response=response,
    )

    assert allowed is False


def test_blocks_cache_storage_when_lookup_is_not_allowed() -> None:
    policy = CachePolicy()
    response = ProviderResponse(status_code=200, body={"id": "ok"}, provider="fake")

    allowed = policy.allows_cache_storage(
        payload={"model": "gpt-test", "messages": [], "stream": True},
        headers={},
        response=response,
    )

    assert allowed is False
