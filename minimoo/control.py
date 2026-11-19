"""Deterministic control spine: identity, validation, routing, policy, budgets.

Owns all state transitions. Never executes model-generated shell. Small
schemas, finite choices, abstain on uncertainty, bounded retries.
"""
from __future__ import annotations
import re
from .store import Store

MISSION_RE = re.compile(r"^MIN-[0-9]{3,}$")
TOOL_ALLOW = {
    "repo.status", "repo.branches", "repo.diffstat", "log.tail",
    "test.parse", "health.check", "memory.recall", "inventory.list",
}
WRITE_TOOLS = {"handover.write", "briefing.write", "receipt.file", "job.submit"}

JOB_TOOL = {
    "dispatcher": {"tools": ["job.submit"], "kind": "deterministic"},
    "mission-clerk": {"tools": ["job.submit"], "kind": "deterministic"},
    "watchdog": {"tools": ["health.check", "log.tail"], "kind": "deterministic"},
    "repo-hygiene": {"tools": ["repo.status", "repo.branches", "repo.diffstat"], "kind": "deterministic"},
    "test-investigator": {"tools": ["test.parse", "log.tail"], "kind": "deterministic"},
    "handover-clerk": {"tools": ["handover.write"], "kind": "deterministic"},
    "knowledge-librarian": {"tools": ["memory.recall"], "kind": "model"},
    "compute-steward": {"tools": ["health.check"], "kind": "model"},
    "briefing": {"tools": ["briefing.write", "inventory.list"], "kind": "model"},
    "inventory": {"tools": ["inventory.list", "repo.status"], "kind": "deterministic"},
    "log-classifier": {"tools": ["log.tail"], "kind": "model"},
}

class PolicyDenied(Exception):
    pass

def check_tool_call(capability: str, tool: str, args: dict, project_root: str,
                    write_approved: bool = False) -> None:
    """Fail-closed tool gate: allowlisted tools, validated args, root containment."""
    spec = JOB_TOOL.get(capability)
    if spec is None:
        raise PolicyDenied(f"unknown capability {capability!r} — abstain")
    allowed = set(spec["tools"]) | ({"repo.status"} if capability else set())
    if tool not in TOOL_ALLOW and tool not in WRITE_TOOLS:
        raise PolicyDenied(f"tool {tool!r} not in catalogue")
    if tool not in allowed and tool not in {"repo.status", "health.check", "log.tail"}:
        raise PolicyDenied(f"tool {tool!r} not allowed for {capability!r}")
    if tool in WRITE_TOOLS and not write_approved:
        raise PolicyDenied(f"material write {tool!r} needs explicit approval")
    # path containment for any path arg
    import os
    for k in ("path", "worktree", "repo", "file"):
        v = (args or {}).get(k)
        if v:
            ap = os.path.abspath(os.path.join(project_root, v) if not os.path.isabs(v) else v)
            root = os.path.abspath(project_root)
            if not (ap == root or ap.startswith(root + os.sep)):
                raise PolicyDenied(f"path escape: {v!r} outside {root}")
    # no shell metachars smuggled as tool args
    blob = str(args)
    if any(t in blob for t in (";", "&&", "$(", "`", "| sh", "powershell -c")):
        # allow plain prose but not shell composition
        if tool not in {"briefing.write", "handover.write"}:
            raise PolicyDenied("shell composition in tool args refused")

def route_mission(store: Store, mission_id: str, capability: str) -> dict | None:
    """Pick an available agent with the capability; else abstain (None)."""
    if not MISSION_RE.match(mission_id or ""):
        raise ValueError(f"bad mission id {mission_id!r}")
    import json
    cands = []
    for a in store.list_agents():
        caps = json.loads(a["capabilities"] or "[]")
        if capability in caps and a["availability"] == "available" and not a["current_job"]:
            cands.append(a)
    # prefer local-free-first
    cands.sort(key=lambda a: (0 if a["cost_pref"] == "local-free-first" else 1, a["name"]))
    return cands[0] if cands else None

def validate_receipt_fields(fields: dict) -> list[str]:
    problems = []
    for k in ("summary", "output_ref", "checks"):
        if k not in (fields or {}):
            problems.append(f"missing {k}")
    if not isinstance((fields or {}).get("checks", None), list):
        problems.append("checks must be a list")
    return problems
