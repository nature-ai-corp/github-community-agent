"""Offline unit tests for the bounded GitHub static transport audit."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "gc_github_static_audit", ROOT / "scripts/github_readonly_transport_audit.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_actual_github_adapter_transport_is_source_read_only():
    source = (ROOT / "src/github_community_agent/github_readonly.py").read_text(
        encoding="utf-8"
    )
    report = mod.audit(source)
    assert report["pass"] is True, report["problems"]
    assert report["direct_send_methods"] == ["GET", "POST"]
    assert report["fixed_graphql_query_names"] == ["DISCUSSIONS_QUERY", "DISCUSSION_QUERY"]
    assert report["independent_github_side_effect_audit"] is False


def test_mutation_and_dynamic_transport_are_rejected():
    source = """
def _send(method, url):
    with httpx.Client(trust_env=False, follow_redirects=False) as client:
        client.stream(method, url)
def _get():
    _send('DELETE', '/x')
def _graphql(query):
    if query not in (DISCUSSIONS_QUERY, DISCUSSION_QUERY):
        raise ValueError()
    _send('POST', '/graphql')
DISCUSSIONS_QUERY = 'mutation { addComment(input:{}) { clientMutationId } }'
DISCUSSION_QUERY = 'query($x: Int!) { viewer { login } }'
"""
    report = mod.audit(source)
    assert report["pass"] is False
    assert any("Unexpected GitHub HTTP method" in p for p in report["problems"])
    assert any("not a GraphQL query" in p for p in report["problems"])
