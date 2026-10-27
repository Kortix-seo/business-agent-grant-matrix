#!/usr/bin/env python3
"""Resolve a queue of agent tool calls against a business grant policy.

Kortix is open source: the policy this script reads is the same file a Kortix
project reads, mirrored as JSON so the script runs on the standard library
alone.

Usage:
    python3 check_grants.py --policy examples/policy.json --calls examples/calls.json

Output: one line per call, then a count per action. Exit code 1 when a call
that the policy blocks is still in the queue.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path

RUN, HOLD, BLOCK = "run", "hold", "block"


def _matches(pattern: str, value: str) -> bool:
    return fnmatch.fnmatchcase(value, pattern)


def _condition_holds(condition: dict, arguments: dict) -> bool:
    """True when this condition is met by the call's arguments."""
    name = condition.get("arg")
    if name is None:
        return True
    actual = arguments.get(name)
    if actual is None:
        return False
    hit = _matches(str(condition.get("match", "*")), str(actual))
    return not hit if condition.get("negate") else hit


def resolve(call: dict, policy: dict) -> tuple[str, str]:
    """Return (action, reason) for one call under the policy."""
    agent = call["agent"]
    connector = call["connector"]
    action = call["action"]
    arguments = call.get("arguments") or {}

    grants = policy.get("agents", {}).get(agent)
    if grants is None:
        return BLOCK, f"agent {agent!r} is not declared in the manifest"
    if connector not in grants.get("connectors", []):
        return BLOCK, f"agent {agent!r} has no grant for connector {connector!r}"

    qualified = f"{connector}.{action}"

    for rule in policy.get("policies", []):
        if not _matches(rule["match"], qualified):
            continue
        if all(_condition_holds(c, arguments) for c in rule.get("conditions", [])):
            return _translate(rule["action"]), f"project rule {rule['match']}"

    declared = policy.get("connectors", {}).get(connector)
    if declared is None:
        return BLOCK, f"connector {connector!r} is not declared"

    for rule in declared.get("policies", []):
        if _matches(rule["match"], action):
            return _translate(rule["action"]), f"connector rule {connector}:{rule['match']}"

    mode = policy.get("policy", {}).get("default_mode", "allow_all")
    if mode == "risk":
        return (RUN, "default_mode risk, unmatched action is not a write") if action.startswith("get_") else (
            HOLD,
            "default_mode risk, unmatched action may write",
        )
    return RUN, "default_mode allow_all, no rule matched"


def _translate(action: str) -> str:
    return {
        "always_run": RUN,
        "allow": RUN,
        "require_approval": HOLD,
        "ask": HOLD,
        "block": BLOCK,
        "deny": BLOCK,
    }.get(action, BLOCK)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default="examples/policy.json")
    parser.add_argument("--calls", default="examples/calls.json")
    args = parser.parse_args()

    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    calls = json.loads(Path(args.calls).read_text(encoding="utf-8"))

    counts = {RUN: 0, HOLD: 0, BLOCK: 0}
    width = max((len(c["label"]) for c in calls), default=5)
    for call in calls:
        action, reason = resolve(call, policy)
        counts[action] += 1
        print(f"{call['label']:<{width}}  {action:<5}  {call['connector']}.{call['action']:<18} {reason}")

    print()
    print(f"{counts[RUN]} run · {counts[HOLD]} hold · {counts[BLOCK]} block")
    return 1 if counts[BLOCK] else 0


if __name__ == "__main__":
    raise SystemExit(main())
