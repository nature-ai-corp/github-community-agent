# Offline Windows packaging preflight. No API keys, GitHub network, installer
# installation, signing, or external publishing is involved.
# This script uses only a temporary location and cleans it on exit.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
$python = if (Test-Path -LiteralPath $venvPython) {
    $venvPython
} else {
    (Get-Command python -ErrorAction Stop).Source
}
$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("gc-agent-wheel-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    Push-Location $root
    try {
        Write-Host "Building GC Agent wheel (offline runtime smoke; build dependencies may require pip access on initial setup)..."
        & $python -m pip wheel . --no-deps --wheel-dir $temp
        if ($LASTEXITCODE -ne 0) { throw "pip wheel failed: $LASTEXITCODE" }
        $wheels = @(Get-ChildItem -LiteralPath $temp -Filter '*.whl')
        if ($wheels.Count -ne 1) { throw "Expected exactly one GC Agent wheel." }
        $install = Join-Path $temp 'installed'
        & $python -m pip install --no-deps --no-index --target $install $wheels[0].FullName
        if ($LASTEXITCODE -ne 0) { throw "Isolated target installation failed." }
        $env:GC_PREFLIGHT_TARGET = $install
        $smoke = @'
import importlib.metadata as meta
import importlib.resources as resources
import os
import pathlib
import sys

target = pathlib.Path(os.environ["GC_PREFLIGHT_TARGET"])
sys.path.insert(0, str(target))
import github_community_agent
from github_community_agent import work_center
distributions = list(meta.distributions(path=[str(target)]))
matches = [d for d in distributions if d.metadata.get("Name", "").lower().replace("_", "-") == "github-community-agent"]
assert len(matches) == 1, "GC Agent distribution metadata missing from wheel"
d = matches[0]
scripts = {e.name: e for e in d.entry_points if e.group == "console_scripts"}
assert "github-community-agent-home" in scripts, "Missing GUI entrypoint"
assert "github-community-agent-desktop" in scripts, "Missing compatibility entrypoint"
assert scripts["github-community-agent-home"].value == "github_community_agent.work_center:main"
assets = resources.files("github_community_agent")
for name in ("home.html", "gc.css", "worker_v011.css"):
    data = (assets / name).read_bytes()
    assert data, "Missing wheel UI asset " + name
print("Windows wheel smoke PASS; package version:", d.version, "UI assets and entrypoints OK.")
if d.version.endswith(".dev0") or d.version == "0.0.0":
    print("RELEASE BLOCKER: development version; do not publish this wheel as an official release.")
'@
        $smoke | & $python -
        if ($LASTEXITCODE -ne 0) { throw "Installed wheel smoke failed." }
    } finally {
        Pop-Location
    }
} finally {
    Remove-Item Env:GC_PREFLIGHT_TARGET -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $temp -Force -Recurse -ErrorAction SilentlyContinue
}
