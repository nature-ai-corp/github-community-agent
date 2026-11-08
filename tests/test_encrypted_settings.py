"""Windows DPAPI encrypted Settings; no plaintext credential persistence."""
import json
import sys

import pytest

from github_community_agent import encrypted_settings as es


def _payload(key="model-secret-for-tests-only", provider="openai"):
    return {"provider": provider, "model": "gpt-4.1-mini",
            "repository": "nature-ai-corp/nature-ai-worker",
            "model_key": key, "read_token": "github-read-token-tests-only"}


def test_rejects_unencrypted_persistence_on_other_os(tmp_path, monkeypatch):
    monkeypatch.setattr(es.sys, "platform", "linux")
    store = es.EncryptedSettings(tmp_path)
    with pytest.raises(es.SettingsError, match="Windows"):
        store.save(_payload())
    assert not store.path.exists()


def test_saved_settings_roundtrip_without_exposing_secret(tmp_path, monkeypatch):
    monkeypatch.setattr(es.sys, "platform", "win32")
    calls = []
    # Fake crypto only in this offline unit test. The production implementation
    # uses real Windows CryptProtectData/CryptUnprotectData.
    def encrypt(plaintext):
        calls.append("encrypt")
        return b"ENCRYPTED_" + plaintext[::-1]
    def decrypt(ciphertext):
        calls.append("decrypt")
        assert ciphertext.startswith(b"ENCRYPTED_")
        return ciphertext[len(b"ENCRYPTED_"):][::-1]
    monkeypatch.setattr(es, "protect_for_current_user", encrypt)
    monkeypatch.setattr(es, "unprotect_for_current_user", decrypt)
    store = es.EncryptedSettings(tmp_path)
    result = store.save(_payload())
    assert result == {"provider": "openai", "model": "gpt-4.1-mini",
                      "repository": "nature-ai-corp/nature-ai-worker",
                      "has_model_key": True, "has_read_token": True}
    raw = store.path.read_bytes()
    assert b"model-secret-for-tests-only" not in raw
    assert b"github-read-token-tests-only" not in raw
    restarted = es.EncryptedSettings(tmp_path)
    assert restarted.load()["model_key"] == "model-secret-for-tests-only"
    assert restarted.public()["has_model_key"] is True
    assert "model_key" not in restarted.public()
    assert "read_token" not in restarted.public()
    assert "encrypt" in calls and "decrypt" in calls

    # Empty password on Save preserves current provider key and GitHub token.
    retained = restarted.save({**_payload(key=""), "read_token": ""})
    assert retained["has_model_key"] and retained["has_read_token"]
    assert restarted.load()["model_key"] == "model-secret-for-tests-only"
    assert restarted.load()["read_token"] == "github-read-token-tests-only"

    # Never silently send a previous OpenAI key to DeepSeek.
    with pytest.raises(es.SettingsError, match="changing providers"):
        restarted.save({**_payload(key="", provider="deepseek"), "read_token": ""})
    assert restarted.load()["provider"] == "openai"


@pytest.mark.skipif(sys.platform != "win32", reason="native Windows DPAPI required")
def test_native_windows_dpapi_encrypted_settings(tmp_path):
    store = es.EncryptedSettings(tmp_path)
    stored = store.save(_payload())
    assert stored["has_model_key"]
    assert b"model-secret-for-tests-only" not in store.path.read_bytes()
    assert es.EncryptedSettings(tmp_path).load()["model_key"] == "model-secret-for-tests-only"
