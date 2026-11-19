# Minimoo 1.0 — Threat model

## Boundaries

- Dashboard binds 127.0.0.1 only; writes need `MINIMOO_TOKEN`. No unauthenticated network service. Cloud Lucy cannot reach localhost — bridge files or manual checkpoint only.
- Tool catalogue: allowlisted `repo.status/branches/diffstat, log.tail, test.parse, health.check, memory.recall, inventory.list` read-only first; writes (`handover.write, briefing.write, receipt.file, job.submit`) need explicit approval. Project-root containment enforced; `; && $() backticks | sh` in args refused (except prose fields). No arbitrary model-generated shell.
- No destructive cleanup, remote merges/releases, external sends, paid spend, credential scraping. Receipts never store tokens/secrets. Incoming content treated as untrusted (prompt-injection probes in qualify suite must abstain).

## Abuse cases covered (tests)

Kill/restart mid-job → lease recovery, no loss; duplicate submit → dedup hash; duplicate claim → single winner; lost notification → state is in DB, not the notification; sleeping/offline agent → watchdog stale detection; rate-limited Basic Memory → bounded retry/backoff, local-first; stale lease → recover; concurrent claim → `BEGIN IMMEDIATE` atomic; malformed/malicious IDs → `squares in square holes` regex refusal; bad tool args/path escape → `PolicyDenied`; failed inference → explicit error, no silent CPU fallback; interrupted write → checksum-guarded outbox refuses stale; unknown allowance → steward abstains.
