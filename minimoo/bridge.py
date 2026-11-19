"""Workshop Board v1-compatible bridge (bounded, pull-based).

Writer-owned outboxes, checksum-guarded appends. States:
STORED -> RETRIEVED -> ACKNOWLEDGED -> ACCEPTED / EXECUTED.
Cloud Lucy cannot reach localhost: use this bounded bridge or the documented
manual checkpoint fallback. No unauthenticated network exposure.
"""
from __future__ import annotations
import hashlib
import json
import os
import time

ENVELOPE_KEYS = {"v", "id", "from", "to", "project", "type", "summary",
                 "task", "needs", "ref", "reply_to", "session", "subject"}

def envelope(msg_id: str, from_: str, to: str, type_: str, summary: str,
             task: str = "", ref: str = "", reply_to: str = "",
             needs: str = "", subject: str = "", session: str = "") -> dict:
    return {"v": 1, "id": msg_id, "from": from_, "to": to, "project": "workshop-board",
            "type": type_, "summary": summary[:280], "task": task, "needs": needs,
            "ref": ref, "reply_to": reply_to, "session": session, "subject": subject}

def outbox_checksum(path: str) -> str:
    if not os.path.exists(path):
        return "missing"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()[:32]

def append_message(outbox: str, msg: dict, body: str, expected_checksum: str = "") -> dict:
    """Checksum-guarded append to our OWN outbox only."""
    if expected_checksum:
        cur = outbox_checksum(outbox)
        if cur != expected_checksum:
            raise ValueError(f"stale outbox checksum {cur} != {expected_checksum}; re-read, no overwrite")
    os.makedirs(os.path.dirname(outbox) or ".", exist_ok=True)
    extra = {k: v for k, v in msg.items() if k in ENVELOPE_KEYS}
    block = f"\n### {time.strftime('%Y-%m-%d')} | {msg['id']}\n```json\n{json.dumps(extra, indent=2)}\n```\n{body.rstrip()}\n"
    with open(outbox, "a", encoding="utf-8") as f:
        f.write(block)
    return {"id": msg["id"], "checksum": outbox_checksum(outbox)}
