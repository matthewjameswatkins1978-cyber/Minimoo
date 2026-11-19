# Minimoo 1.0 — Job catalogue (working, with evidence + permissions)

| Job | Kind | Permission | Status | Live evidence |
|---|---|---|---|---|
| dispatcher | deterministic | queue | proven | e2e submit/claim/dedup/atomic race (scripts/e2e.py 11/11) |
| mission-clerk | deterministic | validate | proven | receipt schema rejection + Lucy correction loop (e2e) |
| watchdog | deterministic | read | proven | kill/restart recovery, stale-lease sweep (`recover` → 0 pending) |
| repo-hygiene | deterministic | read+recommend | proven | live `repo.status` on F:/Projects/Minimoo (branch master, 8 untracked, recommend only) |
| test-investigator | deterministic | read+approved-tests | proven | `python -m unittest discover -s tests` 7/7 + e2e 11/11 parsed |
| handover-clerk | deterministic | write-with-approval | proven | JOB-FFE27704 checkpoint packet in live DB |
| inventory | deterministic | read | proven | live file inventory for this repo (JOB-AD1D40EA) |
| knowledge-librarian | model | read | experimental | needs full 24-case model pass + human promotion approval |
| compute-steward | model | read | experimental | abstains on unknown allowance (tested); needs quota evidence |
| briefing | model | write-with-approval | experimental | drafts only; human approves |
| log-classifier | model | read | experimental | triage only; no auto-remediation |
| remote-merge | n/a | denied | unsupported | out of scope by policy |
| paid-spend | n/a | denied | unsupported | out of scope by policy |

Versioned in `minimoo/jobs_catalog.py`. Deterministic jobs run now; model jobs
escalate/abstain until qualified per `docs/QUALIFICATION-REPORT.md`.
