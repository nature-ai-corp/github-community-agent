"""Independent GitHub Community Agent encrypted local settings.

Windows credentials are protected with the CURRENT WINDOWS USER's DPAPI.
No plaintext credentials or encryption keys are placed in the work database,
project directory, browser storage, or HTTP GET responses. This does not
protect against a malicious process running under the same Windows user.
Non-Windows runs refuse credential persistence (no insecure fallback).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from pathlib import Path

from .windows_dpapi import protect_for_current_user, unprotect_for_current_user

class SettingsError(RuntimeError):
    pass

class EncryptedSettings:
    def __init__(self, root: Path):
        self.root = root
        self.path = root / "settings.dpapi"
        self._lock = threading.RLock()

    @staticmethod
    def _defaults() -> dict:
        return {"provider": "openai", "model": "gpt-4.1-mini",
                "repository": "", "model_key": "", "read_token": ""}

    def _verify(self):
        if sys.platform != "win32":
            raise SettingsError("Encrypted settings require Windows user DPAPI.")
        if self.root.is_symlink() or self.path.is_symlink():
            raise SettingsError("Unsafe credential storage path.")

    def _load_locked(self) -> dict:
        self._verify()
        result = self._defaults()
        try:
            ciphertext = self.path.read_bytes()
        except FileNotFoundError:
            return result
        try:
            decoded = json.loads(unprotect_for_current_user(ciphertext))
        except Exception as exc:
            raise SettingsError("Encrypted settings cannot be decrypted; no keys were loaded.") from exc
        if not isinstance(decoded, dict):
            raise SettingsError("Stored settings format is invalid.")
        for key in result:
            if isinstance(decoded.get(key), str):
                result[key] = decoded[key]
        return result

    def load(self) -> dict:
        with self._lock:
            return self._load_locked()

    def public(self) -> dict:
        data = self.load()
        return {"provider": data["provider"], "model": data["model"],
                "repository": data["repository"],
                "has_model_key": bool(data["model_key"]),
                "has_read_token": bool(data["read_token"])}

    def save(self, supplied: dict) -> dict:
        if not isinstance(supplied, dict):
            raise SettingsError("Expected settings object.")
        with self._lock:
            existing = self._load_locked()
            provider = supplied.get("provider")
            model = supplied.get("model")
            repository = supplied.get("repository")
            if provider not in ("openai", "deepseek") or not isinstance(model, str):
                raise SettingsError("Invalid AI provider or model.")
            if not isinstance(repository, str):
                raise SettingsError("Invalid repository.")
            model = model.strip()
            repository = repository.strip()
            from .model_provider import ModelSettings
            from .runtime import CommunitySettings
            ModelSettings(provider, model)
            CommunitySettings(repository)
            provided_model_key = supplied.get("model_key", "")
            provided_read_token = supplied.get("read_token", "")
            if not isinstance(provided_model_key, str) or not isinstance(provided_read_token, str):
                raise SettingsError("Invalid credential field.")
            # Never carry an OpenAI token across to DeepSeek or vice versa.
            model_key = provided_model_key or (
                existing["model_key"] if provider == existing["provider"] else "")
            if not model_key:
                raise SettingsError("API key required when changing providers.")
            values = {
                "provider": provider, "model": model, "repository": repository,
                "model_key": model_key,
                "read_token": provided_read_token or existing["read_token"],
            }
            self._verify()
            # Save with restrictive default Windows user profile ACL inherited
            # from LOCALAPPDATA. Refuse linked root and existing linked targets.
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._verify()
            encrypted = protect_for_current_user(json.dumps(values).encode("utf-8"))
            fd, temporary = tempfile.mkstemp(prefix=".gc-settings-", dir=self.root)
            try:
                with os.fdopen(fd, "wb") as output:
                    output.write(encrypted)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, self.path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            return self.public()
