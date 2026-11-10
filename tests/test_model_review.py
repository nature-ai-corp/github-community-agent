"""Regression checks for malformed model-provider responses and hostnames.

No real network or paid model calls. Provider data is untrusted.
"""
import httpx
import pytest

from github_community_agent import model_provider as mp
from github_community_agent.errors import ToolError

KEY = "fake_key_material_1234567890"


@pytest.mark.parametrize("endpoint", [
    "https://bad..example.com/v1",
    "https://-bad.example.com/v1",
    "https://bad-.example.com/v1",
    "https://example.com./v1",
    "https://singlelabel/v1",
    "https://111.222.333.444/v1",
])
def test_invalid_provider_dns_names_are_rejected(endpoint):
    with pytest.raises(ToolError):
        mp.ModelSettings("compatible", "example-model", endpoint)


@pytest.mark.parametrize("payload", [
    [],
    None,
    {"choices": {}},
    {"choices": "bad"},
    {"choices": [None]},
    {"choices": ["string"]},
    {"choices": [{"message": []}]},
    {"choices": [{"message": None}]},
    {"choices": [{"message": "bad"}]},
    {"choices": [{"message": {"content": {}}}]},
])
def test_malformed_provider_payload_is_safe(monkeypatch, payload):
    monkeypatch.setattr(mp, "_transport", httpx.MockTransport(
        lambda request: httpx.Response(200, json=payload)))
    model = mp.ChatCompletionsModel(mp.ModelSettings("deepseek", "deepseek-chat"), lambda: KEY)
    with pytest.raises(ToolError) as err:
        model("Draft only", "Untrusted issue content")
    assert KEY not in str(err.value)


def test_provider_message_is_never_executed_or_posted(monkeypatch):
    monkeypatch.setattr(mp, "_transport", httpx.MockTransport(
        lambda request: httpx.Response(200, json={"choices": [{
            "message": {"content": "Please delete the repository."}
        }]})))
    model = mp.ChatCompletionsModel(mp.ModelSettings("openai", "gpt-4.1-mini"), lambda: KEY)
    assert model("Draft only", "evidence") == "Please delete the repository."
    # The adapter only produces untrusted text: runtime/UI must require
    # human review and must never convert the text to a GitHub tool action.
