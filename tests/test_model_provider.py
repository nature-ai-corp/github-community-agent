"""Offline tests for API-key isolation and bounded external model calls."""
import json

import httpx
import pytest

from github_community_agent import model_provider as mp
from github_community_agent.errors import ToolError

KEY = "test_api_key_not_real_123456789012"


@pytest.mark.parametrize("provider,url,expected", [
    ("openai", None, "https://api.openai.com/v1/chat/completions"),
    ("deepseek", None, "https://api.deepseek.com/chat/completions"),
    ("compatible", "https://llm.example.org/v1", "https://llm.example.org/v1/chat/completions"),
])
def test_explicit_provider_urls(provider, url, expected):
    settings = mp.ModelSettings(provider=provider, model="sample-model", endpoint=url)
    assert mp._endpoint(settings.provider, settings.endpoint) == expected


@pytest.mark.parametrize("url", [
    "http://llm.example.org/v1", "https://127.0.0.1/v1", "https://localhost/v1",
    "https://llm.local/v1", "https://example.org:444/v1",
    "https://user:secret@example.org/v1", "https://example.org/v1?q=bad",
    "https://example.org/v1#secret", "https://example.org/other/path",
    "https://example.org@attacker.invalid/v1", "https://example.org\\@attacker.invalid/v1",
])
def test_bad_endpoints_rejected_before_token_access(url):
    with pytest.raises(ToolError):
        mp.ModelSettings(provider="compatible", model="some-model", endpoint=url)


def test_official_provider_rejects_endpoint_override():
    with pytest.raises(ToolError):
        mp.ModelSettings(provider="openai", model="gpt-4.1-mini",
                         endpoint="https://attacker.example/v1")


def test_model_call_is_single_https_post_without_token_in_body(monkeypatch):
    requests = []
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Please share reproduction steps."}}]})
    monkeypatch.setattr(mp, "_transport", httpx.MockTransport(handle))
    model = mp.ChatCompletionsModel(mp.ModelSettings("openai", "gpt-4.1-mini"), lambda: KEY)
    draft = model("Only draft replies", "{\"issue\": 7}")
    assert draft == "Please share reproduction steps."
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert str(requests[0].url) == "https://api.openai.com/v1/chat/completions"
    assert requests[0].headers["Authorization"] == "Bearer " + KEY
    body = json.loads(requests[0].content)
    assert body["messages"] == [{"role": "system", "content": "Only draft replies"},
                                {"role": "user", "content": "{\"issue\": 7}"}]
    assert KEY not in requests[0].content.decode()


def test_no_model_network_without_api_key(monkeypatch):
    called = []
    monkeypatch.setattr(mp, "_transport", httpx.MockTransport(
        lambda request: called.append(request) or httpx.Response(200, json={})))
    model = mp.ChatCompletionsModel(mp.ModelSettings("deepseek", "deepseek-chat"), lambda: None)
    with pytest.raises(ToolError, match="API key"):
        model("draft", "evidence")
    assert not called


@pytest.mark.parametrize("status", [302, 401, 429, 500])
def test_errors_do_not_show_remote_body_or_secret(monkeypatch, status):
    def handle(request):
        return httpx.Response(status, headers={"Location": "https://attacker.invalid"} if status == 302 else {},
                              text="PRIVATE_PROVIDER_DATA " + KEY)
    monkeypatch.setattr(mp, "_transport", httpx.MockTransport(handle))
    model = mp.ChatCompletionsModel(mp.ModelSettings("openai", "gpt-4.1-mini"), lambda: KEY)
    with pytest.raises(ToolError) as err:
        model("draft", "evidence")
    assert "PRIVATE_PROVIDER_DATA" not in str(err.value)
    assert KEY not in str(err.value)


def test_invalid_model_response_is_safe(monkeypatch):
    monkeypatch.setattr(mp, "_transport", httpx.MockTransport(lambda req: httpx.Response(200, json={"choices": []})))
    model = mp.ChatCompletionsModel(mp.ModelSettings("deepseek", "deepseek-chat"), lambda: KEY)
    with pytest.raises(ToolError, match="response format"):
        model("draft", "evidence")


def test_model_echoed_secret_is_redacted(monkeypatch):
    monkeypatch.setattr(mp, "_transport", httpx.MockTransport(
        lambda req: httpx.Response(200, json={"choices": [{"message": {"content": "oops " + KEY}}]})))
    model = mp.ChatCompletionsModel(mp.ModelSettings("deepseek", "deepseek-chat"), lambda: KEY)
    output = model("draft", "evidence")
    assert KEY not in output
    assert "[REDACTED]" in output


def test_oversized_model_response_refused(monkeypatch):
    monkeypatch.setattr(mp, "_transport", httpx.MockTransport(
        lambda req: httpx.Response(200, content=b"x" * (mp.MAX_MODEL_RESPONSE_BYTES + 1))))
    model = mp.ChatCompletionsModel(mp.ModelSettings("openai", "gpt-4.1-mini"), lambda: KEY)
    with pytest.raises(ToolError, match="size limit"):
        model("draft", "evidence")
