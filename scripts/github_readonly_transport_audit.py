"""Conservative static GitHub read-only transport contract report.

This does not use tokens, make network calls or audit GitHub server events.
It inspects the exact source for the GitHub adapter's fixed REST/GraphQL
send boundaries; failure or an unfamiliar dynamic path means manual review.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def audit(source: str) -> dict:
    tree = ast.parse(source)
    functions = {n.name: n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    problems = []
    methods = []
    graphql_ops = []
    if "_send" not in functions or "_get" not in functions or "_graphql" not in functions:
        problems.append("Expected GitHub transport functions not found")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_send":
            if not node.args or not isinstance(node.args[0], ast.Constant):
                problems.append("Dynamic GitHub _send method argument")
            else:
                method = node.args[0].value
                methods.append(method)
                if method not in ("GET", "POST"):
                    problems.append("Unexpected GitHub HTTP method: " + str(method))
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("DISCUSSIONS_QUERY", "DISCUSSION_QUERY"):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        graphql_ops.append((target.id, node.value.value))
                    else:
                        problems.append("Nonliteral GraphQL document")
    if sorted(methods) != ["GET", "POST"]:
        problems.append("Expected exactly REST GET and GraphQL POST _send calls")
    if len(graphql_ops) != 2:
        problems.append("Expected exactly two fixed GraphQL documents")
    for name, document in graphql_ops:
        if not document.lstrip().startswith("query("):
            problems.append(name + " is not a GraphQL query operation")
        if "mutation" in document.lower() or "subscription" in document.lower():
            problems.append(name + " has unexpected mutation/subscription token")
    if "_graphql" in functions:
        f = functions["_graphql"]
        src = ast.get_source_segment(source, f) or ""
        if "if query not in (DISCUSSIONS_QUERY, DISCUSSION_QUERY)" not in src:
            problems.append("GraphQL query allowlist not recognized")
    if "_send" in functions:
        src = ast.get_source_segment(source, functions["_send"]) or ""
        for expected in ("trust_env=False", "follow_redirects=False", "client.stream(method, url"):
            if expected not in src:
                problems.append("Transport guard missing: " + expected)
    return {
        "scope": "Source GitHub-adapter static review; NOT independent GitHub server-side no-write proof",
        "direct_send_methods": sorted(methods),
        "fixed_graphql_query_names": sorted(x[0] for x in graphql_ops),
        "problems": problems,
        "pass": not problems,
        "independent_github_side_effect_audit": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error("Report already exists: preserve past security evidence")
    result = audit(args.source.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("GitHub transport source audit:", "PASS" if result["pass"] else "FAIL")
    print("Source send methods:", ", ".join(result["direct_send_methods"]))
    print("GraphQL fixed documents:", ", ".join(result["fixed_graphql_query_names"]))
    for problem in result["problems"]:
        print("REVIEW:", problem)
    print("Report:", args.output)
    print("INDEPENDENT GITHUB NO-WRITE EVIDENCE STILL REQUIRED.")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
