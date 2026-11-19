"""Minimoo CLI — ergonomic local operator surface."""
from __future__ import annotations
import argparse
import json
import os
import sys

from .config import MinimooConfig
from .store import Store
from .inference import InferenceAdapter
from .control import route_mission, check_tool_call
from .jobs_catalog import CATALOGUE
from .bridge import envelope, append_message, outbox_checksum

def _ctx():
    cfg = MinimooConfig.load()
    os.makedirs(cfg.data_dir, exist_ok=True)
    store = Store(cfg.db_path)
    infer = InferenceAdapter(cfg.llama_server, cfg.model, cfg.host,
                             19432 if cfg.port == 3737 else cfg.port + 10000,
                             cfg.n_ctx, cfg.n_gpu_layers, cfg.gpu_pause_file)
    return cfg, store, infer

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="minimoo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("status")
    p = sub.add_parser("submit"); p.add_argument("--mission", required=True)
    p.add_argument("--title", required=True); p.add_argument("--body", default="")
    p.add_argument("--capability", default=""); p.add_argument("--project", default="")
    p = sub.add_parser("claim"); p.add_argument("--owner", required=True)
    p.add_argument("--capability", default="")
    p = sub.add_parser("state"); p.add_argument("--job", required=True)
    p.add_argument("--to", required=True); p.add_argument("--evidence", default="")
    p = sub.add_parser("agent"); p.add_argument("--name", required=True)
    p.add_argument("--caps", default="dispatcher"); p.add_argument("--worktree", default="")
    p = sub.add_parser("receipt"); p.add_argument("--mission", required=True)
    p.add_argument("--job", required=True); p.add_argument("--agent", required=True)
    p.add_argument("--status", default="DONE"); p.add_argument("--summary", required=True)
    p.add_argument("--output-ref", required=True)
    p = sub.add_parser("recover")
    p = sub.add_parser("gpu"); p.add_argument("--pause", choices=["on", "off"], default="off")
    p = sub.add_parser("gpu-start")
    p = sub.add_parser("dashboard")
    sub.add_parser("catalogue")
    p = sub.add_parser("packet"); p.add_argument("--mission", required=True)
    p.add_argument("--kind", required=True); p.add_argument("--from", dest="frm", required=True)
    p.add_argument("--to", required=True); p.add_argument("--body", default="")
    p.add_argument("--job", default="")
    a = ap.parse_args(argv)
    cfg, store, infer = _ctx()
    try:
        if a.cmd == "init":
            store.register_agent("pi-cli", ["dispatcher", "mission-clerk", "watchdog",
                                            "repo-hygiene", "test-investigator",
                                            "handover-clerk", "inventory"],
                                 worktree="F:/Projects/Minimoo")
            print(f"init ok: {cfg.db_path}")
        elif a.cmd == "status":
            print(json.dumps({"db": cfg.db_path, "gpu": infer.status(),
                              "jobs": len(store.list_jobs()),
                              "agents": store.list_agents()}, indent=2, default=str))
        elif a.cmd == "submit":
            j = store.submit_job(a.mission, a.title, a.body, capability=a.capability,
                                 project=a.project)
            print(json.dumps(j, indent=2, default=str))
        elif a.cmd == "claim":
            j = store.claim_job(a.owner, a.capability)
            print(json.dumps(j, indent=2, default=str) if j else "no-claim (abstain: none available)")
        elif a.cmd == "state":
            print(json.dumps(store.set_state(a.job, a.to, "cli", a.evidence), indent=2, default=str))
        elif a.cmd == "agent":
            print(json.dumps(store.register_agent(a.name, a.caps.split(","),
                                                  worktree=a.worktree), indent=2, default=str))
        elif a.cmd == "receipt":
            r = store.add_receipt(a.mission, a.job, a.agent, a.status,
                                  {"summary": a.summary, "output_ref": a.output_ref,
                                   "checks": ["stored"]}, [], actor="cli")
            print(json.dumps(r, indent=2, default=str))
        elif a.cmd == "recover":
            print(json.dumps({"recovered": len(store.recover_stale("cli"))}, indent=2))
        elif a.cmd == "gpu":
            print(json.dumps(infer.pause(a.pause == "on"), indent=2))
        elif a.cmd == "gpu-start":
            print(json.dumps(infer.start(), indent=2, default=str))
        elif a.cmd == "dashboard":
            from .server import serve
            httpd = serve(store, infer, cfg.host, cfg.port, cfg.api_token)
            print(f"dashboard on http://{cfg.host}:{cfg.port} (127.0.0.1 only)")
            httpd.serve_forever()
        elif a.cmd == "catalogue":
            print(json.dumps(CATALOGUE, indent=2))
        elif a.cmd == "packet":
            pkt = store.add_packet(a.mission, a.kind, a.frm, a.to, a.body, job_id=a.job)
            print(json.dumps(pkt, indent=2, default=str))
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    finally:
        store.close()
    return 0
