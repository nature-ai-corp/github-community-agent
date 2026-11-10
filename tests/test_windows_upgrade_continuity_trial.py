"""Static safety contract for the isolated upgrade-continuity trial."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "scripts/windows_upgrade_continuity_trial.py").read_text(encoding="utf-8")
ISS = (ROOT / "packaging/windows/gc-agent.iss").read_text(encoding="utf-8")


def test_trial_uses_fresh_isolated_identity_and_data_root():
    assert "guid = str(uuid.uuid4()).upper()" in SRC
    assert "/DPayloadVerificationAppId=" in SRC
    assert "/DIsolatedAppName=GitHub Community Agent Upgrade Trial" in SRC
    assert "LOCALAPPDATA=str(appdata)" in SRC
    assert 'run.mkdir(parents=True, exist_ok=False)' in SRC
    # The real AppId is only ever READ (fingerprint), never passed to an installer.
    assert SRC.count("REAL_APP_ID") == 2
    assert "#ifndef IsolatedAppName" in ISS and "#define AppName IsolatedAppName" in ISS


def test_trial_proves_builds_differ_and_guards_real_data():
    for token in ("Old build is identical to current src", "New bundle is not identical to current src",
                  "Old build UI asset differs", "OLD build already has the new schema",
                  "real_installation_and_user_data_unchanged", "settings_dpapi_bytes_unchanged",
                  "data_unchanged_by_uninstall", "trial_registry_entry_removed", '.open("x"',
                  "nonexistent-", '"read_token": ""'):
        assert token in SRC, token


def test_trial_never_posts_signs_releases_or_touches_other_products():
    for forbidden in ("/test-connection", "/review\"", "gh release", "git push", "signtool",
                      "Set-AuthenticodeSignature", "nature-ai-worker", "NatureAIWorker"):
        assert forbidden not in SRC, forbidden
