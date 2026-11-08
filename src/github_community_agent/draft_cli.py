"""Explicit, one-shot Draft Replies acceptance entrypoint (no GitHub writes).

The developer opts into an external model API by invoking this command. The
credential is read from a dedicated environment variable, never CLI arguments.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .errors import ToolError
from .model_provider import ChatCompletionsModel, ModelSettings
from .runtime import CommunityRuntime, CommunitySettings

KEY_ENV = "GITHUB_COMMUNITY_AGENT_MODEL_API_KEY"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="github-community-agent-draft")
    parser.add_argument("--repo", required=True, help="Explicit public GitHub owner/repository")
    parser.add_argument("--target", choices=("issue", "discussion"), required=True)
    parser.add_argument("--number", type=int, required=True)
    parser.add_argument("--provider", choices=("openai", "deepseek", "compatible"), required=True)
    parser.add_argument("--model", required=True, help="Model identifier configured by the user")
    parser.add_argument("--endpoint", help="Explicit HTTPS endpoint (compatible provider only)")
    options = parser.parse_args(argv)
    try:
        settings = CommunitySettings(options.repo)
        model_settings = ModelSettings(options.provider, options.model, options.endpoint)
        # Check the dedicated token before reading community data. Never inherit
        # OPENAI_API_KEY, GH_TOKEN or GITHUB_TOKEN by accident.
        if not os.getenv(KEY_ENV):
            raise ToolError(f"Set the dedicated {KEY_ENV} environment variable before drafting.")
        model = ChatCompletionsModel(model_settings, api_key=lambda: os.getenv(KEY_ENV))
        runtime = CommunityRuntime(settings, model=model)
        result = runtime.run("draft_replies", target=options.target, number=options.number)
    except ToolError as exc:
        print(f"Drafting unavailable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
