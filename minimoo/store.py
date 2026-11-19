"""Durable SQLite store: jobs, packets, receipts, agents, audit.

Design: single SQLite file, WAL mode, append-only audit. Atomic claim via
BEGIN IMMEDIATE + conditional UPDATE. Restart recovery = leases expire.
Dedup via content hash. No lost jobs: every state change is audited.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sqlite3
import time
import uuid

ID_RE = re.compile(r"^(MIN|JOB|PKT|RCPT|AG)-[A-Za-z0-9][A-Za-z0-9\-]{0,63}$")
STATE_OK = {"PENDING", "CLAIMED", "ACTIVE", "BLOCKED", "REVIEW",
            "ACCEPTED", "DONE", "CANCELLED", "FAILED", "ESCALATED"}
PACKET_STATE = {"STORED", "RETRIEVED", "ACKNOWLEDGED", "ACCEPTED", "EXECUTED"}

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS jobs(
  id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, title TEXT NOT NULL,
  body TEXT NOT NULL DEFAULT '', agent TEXT NOT NULL DEFAULT '',
  capability TEXT NOT NULL DEFAULT '', project TEXT NOT NULL DEFAULT '',
  worktree TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT 'PENDING',
  lease_owner TEXT NOT NULL DEFAULT '', lease_until REAL NOT NULL DEFAULT 0,
  attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
  dedup_hash TEXT NOT NULL DEFAULT '', parent_id TEXT NOT NULL DEFAULT '',
  revision INTEGER NOT NULL DEFAULT 1, evidence TEXT NOT NULL DEFAULT '[]',
  created_at REAL NOT NULL, updated_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_jobs_state ON jobs(state, lease_until);
CREATE INDEX IF NOT EXISTS idx_jobs_mission ON jobs(mission_id);
CREATE TABLE IF NOT EXISTS packets(
  id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, job_id TEXT NOT NULL DEFAULT '',
  kind TEXT NOT NULL, from_agent TEXT NOT NULL, to_agent TEXT NOT NULL,
  body TEXT NOT NULL DEFAULT '', state TEXT NOT NULL DEFAULT 'STORED',
  created_at REAL NOT NULL, updated_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_packets_mission ON packets(mission_id);
CREATE TABLE IF NOT EXISTS receipts(
  id TEXT PRIMARY KEY, mission_id TEXT NOT NULL, job_id TEXT NOT NULL,
  agent TEXT NOT NULL, status TEXT NOT NULL, fields TEXT NOT NULL DEFAULT '{}',
  evidence TEXT NOT NULL DEFAULT '[]', created_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_receipts_mission ON receipts(mission_id);
CREATE TABLE IF NOT EXISTS agents(
  name TEXT PRIMARY KEY, capabilities TEXT NOT NULL DEFAULT '[]',
  availability TEXT NOT NULL DEFAULT 'unknown', last_seen REAL NOT NULL DEFAULT 0,
  current_job TEXT NOT NULL DEFAULT '', quota_note TEXT NOT NULL DEFAULT 'unknown',
  cost_pref TEXT NOT NULL DEFAULT 'local-free-first', worktree TEXT NOT NULL DEFAULT '',
  evidence TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS audit(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, actor TEXT NOT NULL,
  action TEXT NOT NULL, target TEXT NOT NULL DEFAULT '', detail TEXT NOT NULL DEFAULT '');
"""

def now() -> float:
    return time.time()

def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

def validate_id(v: str) -> None:
    if not ID_RE.match(v or ""):
        raise ValueError(f"bad id (squares in square holes): {v!r}")

def dedup_hash(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update((p or "").encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:32]

class Store:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path
        self.cx = sqlite3.connect(path, timeout=30.0, isolation_level=None,
                                  check_same_thread=False)
        self.cx.row_factory = sqlite3.Row
        self.cx.executescript(SCHEMA)

    def close(self):
        try:
            self.cx.close()
        except Exception:
            pass

    # -- audit ----------------------------------------------------------
    def audit(self, actor: str, action: str, target: str = "", detail: str = "") -> None:
        self.cx.execute("INSERT INTO audit(ts,actor,action,target,detail) VALUES(?,?,?,?,?)",
                        (now(), actor, action, target, detail[:4000]))

    # -- jobs -----------------------------------------------------------
    def submit_job(self, mission_id: str, title: str, body: str = "", agent: str = "",
                   capability: str = "", project: str = "", worktree: str = "",
                   parent_id: str = "", max_attempts: int = 3,
                   actor: str = "minimoo") -> dict:
        validate_id(mission_id)
        jid = new_id("JOB")
        dh = dedup_hash(mission_id, title, body, capability)
        row = self.cx.execute("SELECT id FROM jobs WHERE dedup_hash=? LIMIT 1", (dh,)).fetchone()
        if row:
            return self.get_job(row["id"])
        t = now()
        self.cx.execute(
            "INSERT INTO jobs(id,mission_id,title,body,agent,capability,project,worktree,state,"
            "lease_owner,lease_until,attempts,max_attempts,dedup_hash,parent_id,revision,"
            "evidence,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (jid, mission_id, title, body, agent, capability, project, worktree, "PENDING",
             "", 0, 0, max_attempts, dh, parent_id, 1, "[]", t, t))
        self.audit(actor, "job.submit", jid, title[:200])
        return self.get_job(jid)

    def get_job(self, jid: str) -> dict:
        row = self.cx.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        if not row:
            raise KeyError(f"no such job {jid}")
        return dict(row)

    def list_jobs(self, state: str = "", limit: int = 200) -> list[dict]:
        if state:
            rows = self.cx.execute("SELECT * FROM jobs WHERE state=? ORDER BY updated_at DESC LIMIT ?",
                                   (state, limit)).fetchall()
        else:
            rows = self.cx.execute("SELECT * FROM jobs ORDER BY updated_at DESC LIMIT ?",
                                   (limit,)).fetchall()
        return [dict(r) for r in rows]

    def claim_job(self, owner: str, capability: str = "", lease_secs: float = 300) -> dict | None:
        """Atomic assignment/claim. One winner under concurrency."""
        if not owner:
            raise ValueError("claim needs an owner")
        self.cx.execute("BEGIN IMMEDIATE")
        try:
            if capability:
                row = self.cx.execute(
                    "SELECT id FROM jobs WHERE state='PENDING' AND capability=? "
                    "AND (lease_until IS NULL OR lease_until < ?) ORDER BY created_at LIMIT 1",
                    (capability, now())).fetchone()
            else:
                row = self.cx.execute(
                    "SELECT id FROM jobs WHERE state='PENDING' "
                    "AND (lease_until IS NULL OR lease_until < ?) ORDER BY created_at LIMIT 1",
                    (now(),)).fetchone()
            if not row:
                self.cx.execute("COMMIT")
                return None
            jid = row["id"]
            cur = self.cx.execute("SELECT attempts,max_attempts FROM jobs WHERE id=?", (jid,)).fetchone()
            if cur["attempts"] >= cur["max_attempts"]:
                self.cx.execute("UPDATE jobs SET state='ESCALATED',updated_at=? WHERE id=?",
                                (now(), jid))
                self.audit(owner, "job.escalated", jid, "attempts exhausted")
                self.cx.execute("COMMIT")
                return self.get_job(jid)
            self.cx.execute(
                "UPDATE jobs SET state='CLAIMED',lease_owner=?,lease_until=?,attempts=attempts+1,"
                "updated_at=? WHERE id=? AND state='PENDING'",
                (owner, now() + lease_secs, now(), jid))
            if self.cx.total_changes == 0:
                self.cx.execute("ROLLBACK")
                return None
            self.audit(owner, "job.claim", jid, f"lease {lease_secs}s")
            self.cx.execute("COMMIT")
            return self.get_job(jid)
        except Exception:
            try:
                self.cx.execute("ROLLBACK")
            except Exception:
                pass
            raise

    def set_state(self, jid: str, state: str, actor: str, evidence: str = "") -> dict:
        if state not in STATE_OK:
            raise ValueError(f"bad state {state!r}")
        job = self.get_job(jid)
        allowed = {
            "PENDING": {"CLAIMED", "CANCELLED"},
            "CLAIMED": {"ACTIVE", "BLOCKED", "CANCELLED", "PENDING"},
            "ACTIVE": {"BLOCKED", "REVIEW", "FAILED", "CANCELLED", "DONE"},
            "BLOCKED": {"PENDING", "CANCELLED", "ESCALATED"},
            "REVIEW": {"ACCEPTED", "ACTIVE", "ESCALATED"},
            "ACCEPTED": {"DONE"},
            "FAILED": {"PENDING", "ESCALATED"},
            "ESCALATED": {"PENDING", "CANCELLED"},
            "DONE": set(), "CANCELLED": set(),
        }
        if state not in allowed.get(job["state"], set()) and state != job["state"]:
            raise ValueError(f"illegal transition {job['state']} -> {state}")
        ev = json.loads(job["evidence"] or "[]")
        if evidence:
            ev.append({"ts": now(), "by": actor, "note": evidence[:1000]})
        self.cx.execute("UPDATE jobs SET state=?,evidence=?,updated_at=? WHERE id=?",
                        (state, json.dumps(ev), now(), jid))
        self.audit(actor, f"job.{state.lower()}", jid, evidence[:200])
        return self.get_job(jid)

    def heartbeat(self, jid: str, owner: str, lease_secs: float = 300) -> dict:
        job = self.get_job(jid)
        if job["lease_owner"] != owner:
            raise ValueError("heartbeat by non-owner")
        self.cx.execute("UPDATE jobs SET lease_until=?,updated_at=? WHERE id=?",
                        (now() + lease_secs, now(), jid))
        return self.get_job(jid)

    def recover_stale(self, actor: str = "watchdog") -> list[dict]:
        """Restart recovery: expired CLAIMED/ACTIVE leases go back to PENDING."""
        rows = self.cx.execute(
            "SELECT * FROM jobs WHERE state IN ('CLAIMED','ACTIVE') AND lease_until < ?",
            (now(),)).fetchall()
        out = []
        for r in rows:
            self.cx.execute("UPDATE jobs SET state='PENDING',lease_owner='',updated_at=? WHERE id=?",
                            (now(), r["id"]))
            self.audit(actor, "job.recover-stale", r["id"], f"owner was {r['lease_owner']}")
            out.append(self.get_job(r["id"]))
        return out

    # -- packets / receipts ---------------------------------------------
    def add_packet(self, mission_id: str, kind: str, from_agent: str, to_agent: str,
                   body: str, job_id: str = "", actor: str = "minimoo",
                   pid: str = "") -> dict:
        validate_id(mission_id)
        if kind not in {"MISSION", "CORRECTION", "RECEIPT", "REVIEW", "NOTE", "HANDOVER"}:
            raise ValueError(f"bad packet kind {kind!r}")
        pid = pid or new_id("PKT")
        validate_id(pid)
        t = now()
        self.cx.execute(
            "INSERT INTO packets(id,mission_id,job_id,kind,from_agent,to_agent,body,state,"
            "created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (pid, mission_id, job_id, kind, from_agent, to_agent, body, "STORED", t, t))
        self.audit(actor, "packet.stored", pid, f"{kind} {from_agent}->{to_agent}")
        return dict(self.cx.execute("SELECT * FROM packets WHERE id=?", (pid,)).fetchone())

    def packet_mark(self, pid: str, state: str, actor: str) -> dict:
        if state not in PACKET_STATE:
            raise ValueError(f"bad packet state {state!r}")
        self.cx.execute("UPDATE packets SET state=?,updated_at=? WHERE id=?", (state, now(), pid))
        self.audit(actor, f"packet.{state.lower()}", pid, "")
        return dict(self.cx.execute("SELECT * FROM packets WHERE id=?", (pid,)).fetchone())

    def add_receipt(self, mission_id: str, job_id: str, agent: str, status: str,
                    fields: dict, evidence: list, actor: str = "") -> dict:
        """Validate required receipt fields before accepting."""
        validate_id(mission_id)
        required = {"summary", "output_ref", "checks"}
        missing = required - set((fields or {}).keys())
        if missing:
            raise ValueError(f"receipt missing required fields: {sorted(missing)}")
        rid = new_id("RCPT")
        self.cx.execute(
            "INSERT INTO receipts(id,mission_id,job_id,agent,status,fields,evidence,created_at)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (rid, mission_id, job_id, agent, status, json.dumps(fields),
             json.dumps(evidence or []), now()))
        self.audit(actor or agent, "receipt.stored", rid, f"{mission_id} {status}")
        return dict(self.cx.execute("SELECT * FROM receipts WHERE id=?", (rid,)).fetchone())

    # -- agents -----------------------------------------------------------
    def register_agent(self, name: str, capabilities: list[str], worktree: str = "",
                       quota_note: str = "unknown", cost_pref: str = "local-free-first",
                       evidence: str = "") -> dict:
        t = now()
        self.cx.execute(
            "INSERT INTO agents(name,capabilities,availability,last_seen,current_job,quota_note,"
            "cost_pref,worktree,evidence) VALUES(?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET capabilities=excluded.capabilities,"
            "worktree=excluded.worktree,quota_note=excluded.quota_note,cost_pref=excluded.cost_pref,"
            "evidence=excluded.evidence,last_seen=excluded.last_seen",
            (name, json.dumps(capabilities), "available", t, "", quota_note, cost_pref,
             worktree, evidence))
        self.audit(name, "agent.register", name, ",".join(capabilities)[:200])
        return dict(self.cx.execute("SELECT * FROM agents WHERE name=?", (name,)).fetchone())

    def heartbeat_agent(self, name: str, availability: str = "available", current_job: str = "") -> dict:
        self.cx.execute("UPDATE agents SET availability=?,last_seen=?,current_job=? WHERE name=?",
                        (availability, now(), current_job, name))
        return dict(self.cx.execute("SELECT * FROM agents WHERE name=?", (name,)).fetchone())

    def list_agents(self) -> list[dict]:
        return [dict(r) for r in self.cx.execute("SELECT * FROM agents ORDER BY name").fetchall()]
