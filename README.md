# Minimoo 1.0 — local GPU workshop worker

Always-available local AI worker and workshop dispatcher for Matthew's Windows
workstation. GPU-accelerated small model already on this PC
(`D:\Nisaba-dev\models\LFM3-1.7B-Q4_K_M.gguf` via reused
`D:\Nisaba-dev\runtime\b12499\llama-server.exe`, Vulkan on RX 5700 XT).
Nothing is copied or moved — the adapter shells out to the existing runtime.

## Install / start / stop (fresh)

```powershell
# PowerShell 7
.\scripts\install.ps1
python -m minimoo status
python -m minimoo dashboard   # http://127.0.0.1:3737 (loopback only)
```

Data lives in `%USERPROFILE%\.minimoo\minimoo.db`. Uninstall: stop the
dashboard job (`scripts/stop.ps1`), delete the repo checkout and (optionally)
`%USERPROFILE%\.minimoo`. The Nisaba model/runtime are never touched.

## What it does

- Durable numbered jobs/packets/receipts (SQLite, atomic claim, leases,
  dedup, restart recovery, audit). A missed notification never means a lost job.
- Lucy supervision loop: MISSION → agent → receipt (validated) → Lucy →
  CORRECTION (same mission) → same agent → final receipt.
- Agent registry with capabilities, availability timestamps, quota unknown-ok,
  local-free-first preference.
- Restricted tool catalogue (read-only first, writes need approval, root
  containment, no shell passthrough).
- Local dashboard + CLI for pause/resume/submit/cancel/inspect/correction.
- GPU pause file for gaming/other apps: `python -m minimoo gpu --pause on`.

## Connection matrix (honest)

| Path | Status | Evidence |
|---|---|---|
| Pi CLI | working | `pi --help` + file-exchange round trip in tests |
| Antigravity | manual/checkpoint fallback | no supported auto-launch found; documented |
| ChatGPT/Codex | manual/checkpoint fallback | cloud cannot reach localhost; bounded bridge files |
| Basic Memory | bounded, rate-limited | low-frequency promotion only, retry/backoff |

See `docs/` for architecture, threat model, operations, qualification and GPU evidence.
