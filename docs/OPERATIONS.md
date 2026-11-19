# Minimoo 1.0 — Operations

## Fresh install

```powershell
.\scripts\install.ps1        # data dir %USERPROFILE%\.minimoo, registers pi-cli agent
python -m minimoo status
python -m minimoo dashboard  # http://127.0.0.1:3737
```

## Everyday commands

```powershell
python -m minimoo submit --mission MIN-001 --title "nightly hygiene" --capability repo-hygiene
python -m minimoo claim --owner pi-cli --capability repo-hygiene
python -m minimoo state --job JOB-XXXX --to ACTIVE --evidence "started"
python -m minimoo receipt --mission MIN-001 --job JOB-XXXX --agent pi-cli --summary "..." --output-ref "..."
python -m minimoo recover     # watchdog: expired leases -> PENDING
python -m minimoo gpu --pause on|off
$env:MINIMOO_LLAMA_SERVER="D:\Nisaba-dev\runtime\b12499-vulkan\llama-server.exe"
python -m minimoo gpu-start   # on-demand inference, no idle loop
python -m minimoo catalogue
```

## Config (env)

`MINIMOO_DATA, MINIMOO_HOST(127.0.0.1), MINIMOO_PORT(3737), MINIMOO_LLAMA_SERVER,
MINIMOO_MODEL, MINIMOO_CTX(4096), MINIMOO_GPU_LAYERS(99), MINIMOO_TOKEN`

## Upgrade / backup / rollback

- Upgrade: pull, `python -m unittest discover -s tests`, restart dashboard. DB schema is additive (`CREATE TABLE IF NOT EXISTS`).
- Backup: copy `%USERPROFILE%\.minimoo\minimoo.db` + `outbox-pi.md`. Restore: stop dashboard, copy back, `recover`.
- Rollback: `git log --oneline`, `git reset --hard <sha>` to last green, re-run tests.
- Uninstall: `scripts/stop.ps1`, delete checkout, optionally delete `%USERPROFILE%\.minimoo`. Nisaba model/runtime untouched.

## Troubleshooting

- `llama-server exited during startup`: check `.minimoo/llama-server.log`; never add flags blindly (e.g. `--n-parse` was removed in b12499).
- Port in use: another `llama-server` alive (`Get-Process llama-server`) — stop it first.
- Basic Memory 429: wait out `retry_after`, keep working locally; bridge is pull-based.
