# V1 independent runtime — first development increment

The `github-community-agent-workflow` console command exercises the new
standalone **CommunityRuntime** code path, not the old Worker profile. This is
a *developer acceptance CLI*, not a finished user application.

```powershell
python -m pip install -e ".[dev]"
github-community-agent-workflow --repo nature-ai-corp/nature-ai-worker --workflow review_issues
github-community-agent-workflow --repo nature-ai-corp/nature-ai-worker --workflow community_report
```

- `review_issues`: reads the first page of public issues and returns evidence URLs and metadata.
- `review_discussions`: implemented in the runtime, but the command intentionally has no credential entry facility yet. It fails safely if no Discussions token has been configured in an integration.
- `draft_replies`: implemented with a model-adapter injection point, but no AI provider is connected in this increment. It fails safely without a configured model, and cannot post.
- `community_report`: returns a limited evidence summary; without a Discussions read token it explicitly says `incomplete: true` and `discussions_checked: false`.

The Runtime does **not** currently analyze community priorities with an AI model or create an end-user quality report. That requires a later model connector, prompt validation and UI acceptance. It has no GitHub write or approval mechanism.

The runtime never defaults to a repository or to a cloud AI provider, and the current CLI has no auth or local persistent data. It is an architectural starting point for the four V1 workflows, **not a V1 feature-completion claim**.

Next increments: carefully scoped local/cloud AI provider adapter, isolated credentials/configuration, Windows-friendly UI, complete work result format, approval-bound external posting/outbox and actual end-to-end testing.
