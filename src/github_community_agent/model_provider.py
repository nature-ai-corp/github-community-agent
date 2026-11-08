"""Minimal, explicit OpenAI-compatible chat-completions model adapter.

Supports OpenAI, DeepSeek and explicitly configured compatible HTTPS APIs.
No token persistence, no arbitrary URL supplied by a GitHub issue/model, no
redirects, environment proxies, automatic retries, or response body logging.
Model output is *draft text only*, never an instruction to post on GitHub.
"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlsplit

import httpx

from .errors import ToolError

MAX_MODEL_RESPONSE_BYTES = 1_000_000
MAX_COMPLETION_TOKENS = 1200
MAX_RESPONSE_CHARS = 6000
DEFAULT_ENDPOINTS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
}
MODEL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}\Z")
HOST_LABEL_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z")
API_KEY_PATTERN = re.compile(r"[^\s\x00-\x1f\x7f]{12,4096}\Z")

# Mock transport is used only by offline tests.
_transport: httpx.BaseTransport | None = None


def _endpoint(provider: str, explicit: str | None) -> str:
    if provider not in ("openai", "deepseek", "compatible"):
        raise ToolError("Unknown model provider.")
    if provider == "compatible":
        if not explicit:
            raise ToolError("An explicit HTTPS API endpoint is required for a compatible provider.")
        candidate = explicit
    else:
        default = DEFAULT_ENDPOINTS[provider]
        if explicit is not None and explicit.rstrip("/") != default:
            raise ToolError("This provider only accepts its official API endpoint.")
        candidate = default

    # Endpoint is supplied by the user in application settings, never by GitHub
    # content, model output, or task arguments. Restrict the destination anyway.
    try:
        parsed = urlsplit(candidate)
        host = parsed.hostname
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ToolError("Invalid AI provider endpoint.") from exc
    if (parsed.scheme != "https" or not host or len(host) > 253
            or "." not in host or all(label.isdigit() for label in host.split("."))
            or any(not HOST_LABEL_PATTERN.fullmatch(label) for label in host.split("."))
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or port is not None or "\\" in candidate or "@" in candidate):
        raise ToolError("AI provider endpoint must be a safe HTTPS host without credentials or parameters.")

    if (host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".home.arpa"))):
        raise ToolError("Local endpoints are not supported by this cloud API adapter.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ToolError("AI provider endpoint must be a public hostname, not an IP address.")

    path = parsed.path.rstrip("/")
    if path not in ("", "/v1"):
        raise ToolError("AI provider endpoint path must be empty or /v1.")
    return candidate.rstrip("/") + "/chat/completions"



def _check_public_dns(url: str) -> None:
    """Reject endpoints resolving to non-public IPs before sending a secret.

    This is defense in depth, not a complete anti-DNS-rebinding guarantee:
    HTTPX resolves hostnames again when connecting. A future hardened client
    should pin the inspected address while preserving TLS SNI/verification.
    """
    host = urlsplit(url).hostname
    if not host:
        raise ToolError("Invalid AI provider endpoint.")
    try:
        answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except (socket.gaierror, OSError) as exc:
        raise ToolError("Unable to resolve the configured AI provider host.") from exc
    if not answers:
        raise ToolError("Unable to resolve the configured AI provider host.")
    for answer in answers:
        try:
            address = ipaddress.ip_address(answer[4][0])
            if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
                address = address.ipv4_mapped
        except (IndexError, TypeError, ValueError) as exc:
            raise ToolError("AI provider DNS response was invalid.") from exc
        if not address.is_global:
            raise ToolError("AI provider host resolved to a private or non-public network address.")


@dataclass(frozen=True)
class ModelSettings:
    provider: str
    model: str
    endpoint: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not MODEL_PATTERN.fullmatch(self.model):
            raise ToolError("Configure a valid AI model name.")
        _endpoint(self.provider, self.endpoint)


class ChatCompletionsModel:
    def __init__(self, settings: ModelSettings, api_key: Callable[[], str | None]):
        self.settings = settings
        self.api_key = api_key

    def __call__(self, instruction: str, evidence: str) -> str:
        url = _endpoint(self.settings.provider, self.settings.endpoint)
        # Normal production requests perform DNS screening before the key is
        # retrieved, and never on input supplied by untrusted GitHub content.
        if _transport is None:
            _check_public_dns(url)
        secret = self.api_key()
        if not isinstance(secret, str) or not API_KEY_PATTERN.fullmatch(secret):
            raise ToolError("A configured AI provider API key is required.")
        request_body = {
            "model": self.settings.model,
            "messages": [
                {"role": "system", "content": instruction},
                {"role": "user", "content": evidence},
            ],
            "temperature": 0.2,
            "max_tokens": MAX_COMPLETION_TOKENS,
        }
        try:
            with httpx.Client(timeout=30, follow_redirects=False, trust_env=False,
                              transport=_transport) as client:
                with client.stream(
                    "POST", url, json=request_body,
                    headers={"Authorization": "Bearer " + secret,
                             "Content-Type": "application/json",
                             "Accept": "application/json"},
                ) as response:
                    if response.status_code != 200:
                        # Avoid disclosing provider-returned bodies, URLs or keys.
                        raise ToolError(f"AI provider request failed (HTTP {response.status_code}).")
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        raw.extend(chunk)
                        if len(raw) > MAX_MODEL_RESPONSE_BYTES:
                            raise ToolError("AI provider response exceeds size limit.")
        except httpx.HTTPError as exc:
            raise ToolError("Unable to contact the configured AI provider.") from exc

        try:
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("not an object")
            choices = payload.get("choices")
            if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                raise ValueError("bad choices")
            message = choices[0].get("message")
            if not isinstance(message, dict):
                raise ValueError("bad message")
            content = message.get("content")
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            raise ToolError("Unexpected AI provider response format.") from None
        if not isinstance(content, str) or not content.strip():
            raise ToolError("The configured AI model returned no usable text.")
        # Exact token must never appear in the returned draft, even if a provider
        # echoes it in source text. Output remains a *reviewable*, unposted draft.
        return content.strip().replace(secret, "[REDACTED]")[:MAX_RESPONSE_CHARS]
