import json

from finops_token_saver.domain.canonical_payload import CanonicalPayload


def test_equivalent_payloads_with_different_property_order_generate_same_hash() -> None:
    first_payload = {
        "model": "gpt-test",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.2,
        "metadata": {"ignored": True},
    }
    second_payload = {
        "metadata": {"ignored": False},
        "temperature": 0.2,
        "messages": [{"content": "hello", "role": "user"}],
        "model": "gpt-test",
    }

    first = CanonicalPayload.from_chat_completion_payload(first_payload, provider="openai")
    second = CanonicalPayload.from_chat_completion_payload(second_payload, provider="openai")

    assert first.value == second.value
    assert first.sha256() == second.sha256()


def test_generation_parameters_change_hash() -> None:
    base_payload = {
        "model": "gpt-test",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.2,
    }
    changed_payload = {
        "model": "gpt-test",
        "messages": [{"role": "user", "content": "hello"}],
        "temperature": 0.8,
    }

    base = CanonicalPayload.from_chat_completion_payload(base_payload, provider="openai")
    changed = CanonicalPayload.from_chat_completion_payload(changed_payload, provider="openai")

    assert base.sha256() != changed.sha256()


def test_provider_changes_hash() -> None:
    payload = {
        "model": "gpt-test",
        "messages": [{"role": "user", "content": "hello"}],
    }

    openai = CanonicalPayload.from_chat_completion_payload(payload, provider="openai")
    anthropic = CanonicalPayload.from_chat_completion_payload(payload, provider="anthropic")

    assert openai.sha256() != anthropic.sha256()


def test_hash_does_not_expose_prompt_content() -> None:
    payload = {
        "model": "gpt-test",
        "messages": [{"role": "user", "content": "sensitive prompt content"}],
    }

    canonical_payload = CanonicalPayload.from_chat_completion_payload(payload, provider="openai")

    assert "sensitive prompt content" in canonical_payload.value
    assert "sensitive prompt content" not in canonical_payload.sha256()


def test_canonical_value_is_deterministic_json() -> None:
    payload = {
        "tools": [{"function": {"name": "search", "parameters": {"type": "object"}}}],
        "model": "gpt-test",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": True,
    }

    canonical_payload = CanonicalPayload.from_chat_completion_payload(payload, provider="openai")
    decoded = json.loads(canonical_payload.value)

    assert decoded == {
        "messages": [{"content": "hello", "role": "user"}],
        "model": "gpt-test",
        "provider": "openai",
        "tools": [{"function": {"name": "search", "parameters": {"type": "object"}}}],
    }
    assert "stream" not in decoded
