# Minimoo 1.0 — Architecture

Small, maintainable, Windows-friendly. Python stdlib only, no extra deps.

```
minimoo/
  config.py      paths, ports, model/runtime (reuse Nisaba intact)
  store.py       SQLite durable jobs/packets/receipts/agents/audit
  control.py     deterministic spine: validate, route, policy, budgets
  inference.py   llama-server lifecycle (start/stop/pause/generate)
  tools.py       restricted catalogue (read-only first, root containment)
  bridge.py      WB v1 envelope, checksum-guarded own-outbox appends
  jobs_catalog.py  proven / experimental / unsupported + permissions
  server.py      loopback dashboard (127.0.0.1:3737, token-gated writes)
  cli.py         operator surface
```

## Decisions (source-linked)

- Reuse `D:\Nisaba-dev\runtime\b12499-vulkan\llama-server.exe` + `D:\Nisaba-dev\models\LFM3-1.7B-Q4_K_M.gguf` intact; adapter only. `b12499` (CPU) measured 34 t/s vs Vulkan 128 t/s — default is Vulkan, no silent CPU fallback.
- SQLite WAL in `%USERPROFILE%\.minimoo\minimoo.db`; operational state separate from knowledge (Speedy Keeper / Basic Memory).
- Speedy Keeper reused via its CLI when present; never embedded as scheduler. TAXI repo not found on this machine — Pi telemetry concepts reused, no duplicate store.
- Basic Memory Cloud: bounded, low-frequency promotion only (rate limits observed 2026-11-19); never an event bus.
- No competing Pi broker: dashboard is loopback-only; Pi Intercom stays the Pi↔Pi live transport.

## State machine

`PENDING → CLAIMED → ACTIVE → REVIEW → ACCEPTED → DONE`, with `BLOCKED/FAILED/ESCALATED/CANCELLED` escapes. Illegal transitions refused. Packets: `STORED → RETRIEVED → ACKNOWLEDGED → ACCEPTED/EXECUTED`. Receipts require `{summary, output_ref, checks[]}` or are rejected — no auto-acceptance.

## MIN-002 additions

- `minimoo/chat.py`: chat-completions client for the corrected LFM3 harness
  (official template via `--jinja`, Liquid sampling, reasoning separation,
  XML tool-call fallback, template verification). Never executes model output.
- Scoped capability flags (`control.cap_enabled`, `CAP_FLAGS`): each
  model-dependent capability has its own opt-in env flag, default off.
- `eval_feedback` table + `minimoo feedback[.log|-list]`: lightweight learning
  log (decisions, corrections, failures, approvals, outcomes). No training infra.
- Draft-only model jobs (`secretary-draft`, `receipt-draft`): model output is
  watermarked UNREVIEWED and requires human review; writes need approval.
