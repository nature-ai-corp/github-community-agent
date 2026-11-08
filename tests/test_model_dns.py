"""Provider DNS destination screening: mock DNS only, no real network."""
import socket

import pytest

from github_community_agent import model_provider as mp
from github_community_agent.errors import ToolError


@pytest.mark.parametrize("address", [
    "127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.2",
    "169.254.169.254", "0.0.0.0", "::1", "fc00::1", "fe80::1",
    "::ffff:127.0.0.1",
])
def test_model_dns_refuses_nonpublic_addresses(monkeypatch, address):
    monkeypatch.setattr(mp.socket, "getaddrinfo",
                        lambda host, port, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6,
                                                       "", (address, port))])
    with pytest.raises(ToolError, match="non-public"):
        mp._check_public_dns("https://ai.example.org/v1/chat/completions")


def test_model_dns_refuses_mixed_public_and_private(monkeypatch):
    def fake(*args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", 443))]
    monkeypatch.setattr(mp.socket, "getaddrinfo", fake)
    with pytest.raises(ToolError, match="non-public"):
        mp._check_public_dns("https://ai.example.org/v1/chat/completions")


def test_model_dns_public_resolution_accepted(monkeypatch):
    monkeypatch.setattr(mp.socket, "getaddrinfo",
                        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM,
                                                  6, "", ("8.8.8.8", 443))])
    mp._check_public_dns("https://ai.example.org/v1/chat/completions")


def test_model_dns_resolution_failure_is_safe(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("internal DNS diagnostic data")
    monkeypatch.setattr(mp.socket, "getaddrinfo", fail)
    with pytest.raises(ToolError, match="Unable to resolve") as exc:
        mp._check_public_dns("https://ai.example.org/v1/chat/completions")
    assert "internal DNS diagnostic" not in str(exc.value)


def test_nonpublic_dns_rejected_before_secret_lookup(monkeypatch):
    monkeypatch.setattr(mp, "_transport", None)
    monkeypatch.setattr(mp.socket, "getaddrinfo",
                        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6,
                                                  "", ("127.0.0.1", 443))])
    called = []
    model = mp.ChatCompletionsModel(mp.ModelSettings("compatible", "example",
                                                     "https://ai.example.org/v1"),
                                    lambda: called.append(True) or "test_key_1234567890123")
    with pytest.raises(ToolError, match="non-public"):
        model("Instruction", "Evidence")
    assert called == []


@pytest.mark.parametrize("url", [
    "https://ai.internal/v1", "https://ai.home.arpa/v1",
])
def test_explicit_private_network_names_rejected(url):
    with pytest.raises(ToolError):
        mp.ModelSettings("compatible", "example", url)
