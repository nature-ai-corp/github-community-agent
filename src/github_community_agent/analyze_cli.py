"""Developer acceptance: real GitHub public Issues + optional OpenAI AI analysis.

Reads only. Never posts. This is not the final Windows UI.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .ai_review import CommunityAnalyst
from .errors import ToolError
from .model_provider import ChatCompletionsModel, ModelSettings
from .runtime import CommunityRuntime, CommunitySettings

MODEL_KEY_ENV = "GITHUB_COMMUNITY_AGENT_MODEL_API_KEY"
READ_TOKEN_ENV = "GITHUB_COMMUNITY_AGENT_READ_TOKEN"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="github-community-agent-analyze")
    parser.add_argument("--repo", required=True, help="Explicit public owner/repository")
    parser.add_argument("--workflow", choices=("review_issues", "community_report"),
                        required=True)
    parser.add_argument("--provider", choices=("openai", "deepseek", "compatible"),
                        required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--endpoint", help="Explicit HTTPS endpoint for compatible provider")
    args = parser.parse_args(argv)
    try:
        settings = CommunitySettings(args.repo)
        model_settings = ModelSettings(args.provider, args.model, args.endpoint)
        if not os.getenv(MODEL_KEY_ENV):
            raise ToolError(f"Set the dedicated {MODEL_KEY_ENV} environment variable.")
        model = ChatCompletionsModel(model_settings, api_key=lambda: os.getenv(MODEL_KEY_ENV))
        runtime = CommunityRuntime(
            settings, discussion_token=lambda: os.getenv(READ_TOKEN_ENV))
        result = CommunityAnalyst(runtime, model).run(args.workflow)
    except ToolError as exc:
        print(f"Community analysis unavailable: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
