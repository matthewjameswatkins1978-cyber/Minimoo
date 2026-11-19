"""Dispatcher tool-calling accuracy (mission 4D): assign_job with enum args."""
import json, sys
sys.path.insert(0, ".")
from minimoo.chat import ChatClient
from tests.cap_suites import SUITES

cli = ChatClient()
tool = {"type": "function", "function": {
    "name": "assign_job",
    "description": "Assign a workshop job to an eligible agent",
    "parameters": {"type": "object",
                   "properties": {"agent": {"type": "string",
                                            "enum": ["pi-cli", "keeper-svc", "watch-dog", "ABSTAIN"]},
                                  "reason": {"type": "string"}},
                   "required": ["agent", "reason"]}}}
cases = [c for c in SUITES["dispatcher"]]
ok = fp = 0
for c in cases:
    prompt = (f"Eligible agents:\n" + "\n".join("- " + a for a in c["agents"]) +
              f"\nRequest: {c['request']}\nCall assign_job, or answer ABSTAIN in text if none fits.")
    r = cli.chat([{"role": "system", "content": "Route with the assign_job tool when an agent fits."},
                  {"role": "user", "content": prompt}],
                 max_tokens=2048, tools=[tool], tool_choice="auto")
    calls = r.get("tool_calls", [])
    norm = []
    for tc in calls:
        fn = tc["function"]["name"]
        a = tc["function"].get("arguments", {})
        try:
            a = json.loads(a) if isinstance(a, str) else a
        except Exception:
            a = {}
        norm.append((fn, a if isinstance(a, dict) else {}))
    ans = (r.get("answer") or "").strip()
    exp = c["expect"]
    if exp == "ABSTAIN":
        good = (not norm and "ABSTAIN" in ans.upper()) or \
               (len(norm) == 1 and norm[0][0] == "assign_job" and norm[0][1].get("agent") == "ABSTAIN")
    else:
        good = (len(norm) == 1 and norm[0][0] == "assign_job" and
                norm[0][1].get("agent") == exp)
    print(("OK " if good else "FAIL"), c["id"], "expect", exp,
          "| calls:", json.dumps(calls)[:160], "| text:", ans[:80])
    if good:
        ok += 1
    else:
        fp += 1
print(f"tool-mode dispatcher: {ok}/{len(cases)}")
