# Minimoo 1.0 — User guide (Matthew) + Agent guide (Lucy / Pi / others)

## For Matthew

- Dashboard: `python -m minimoo dashboard` → http://127.0.0.1:3737. At a glance:
  agents, pending/active/blocked/review jobs, GPU health, receipts. Pause GPU
  for games: `python -m minimoo gpu --pause on`.
- Submit: `python -m minimoo submit --mission MIN-001 --title "..." --capability repo-hygiene`
- Human review is always available: any job in REVIEW waits for you/Lucy;
  nothing auto-accepts.

## For Lucy (reviewer)

1. Issue a numbered mission: `MISSION` packet (same `mission_id`, e.g. MIN-002).
2. Minimoo routes to a suitable agent; agent returns an evidence receipt —
   fields `{summary, output_ref, checks[]}` validated, else rejected.
3. You ACCEPT or send a CORRECTIVE packet referencing the same mission;
   Minimoo routes the correction back to the same agent. Repeat to acceptance.
4. Manual path (no wake-up illusion): states are `STORED → RETRIEVED →
   ACKNOWLEDGED → ACCEPTED/EXECUTED` in the DB/outbox files; a closed app
   never wakes. If Basic Memory is rate-limited, use the local outbox files
   under `%USERPROFILE%\.minimoo` as the checkpoint transport.

## For Pi / other agents

- Register: `python -m minimoo agent --name pi-cli --caps dispatcher,watchdog --worktree F:/Projects/X`
- Work: `claim --owner <you>` → `state --job ... --to ACTIVE` → `receipt ...`
  → heartbeat via `claim` owner + `recover` sweeps stale leases.
- Tools: allowlisted only, paths contained to your project root, writes need
  approval. Never execute model-generated shell.
