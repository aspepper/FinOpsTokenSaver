import hashlib
import json
from dataclasses import dataclass
from typing import Any

CACHE_RELEVANT_FIELDS = (
    "provider",
    "model",
    "messages",
    "temperature",
    "top_p",
    "max_tokens",
    "response_format",
    "tools",
    "tool_choice",
)


@dataclass(frozen=True)
class CanonicalPayload:
    value: str

    @classmethod
    def from_chat_completion_payload(
        cls,
        payload: dict[str, Any],
        provider: str,
    ) -> "CanonicalPayload":
        relevant_payload = _select_cache_relevant_fields(payload, provider)
        canonical_value = json.dumps(
            relevant_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return cls(canonical_value)

    def sha256(self) -> str:
        return hashlib.sha256(self.value.encode("utf-8")).hexdigest()


def _select_cache_relevant_fields(payload: dict[str, Any], provider: str) -> dict[str, Any]:
    relevant_payload: dict[str, Any] = {"provider": provider}
    for field_name in CACHE_RELEVANT_FIELDS:
        if field_name == "provider":
            continue
        if field_name in payload:
            relevant_payload[field_name] = payload[field_name]
    return relevant_payload
