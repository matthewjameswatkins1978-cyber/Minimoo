"""Probe C: grammar-constrained finite-choice output."""
import json, sys, urllib.request
sys.path.insert(0, ".")
BASE = "http://127.0.0.1:19432"

# C1: response_format json_schema on chat endpoint
payload = {
    "model": "LFM3-1.7B",
    "messages": [{"role": "system", "content": "Classify the request."},
                 {"role": "user", "content": "Nightly hygiene found 3 stale branches, no conflicts."}],
    "max_tokens": 128, "temperature": 0.1, "top_k": 50,
    "response_format": {
        "type": "json_schema",
        "json_schema": {"name": "route",
                        "schema": {"type": "object",
                                   "properties": {"capability": {
                                       "type": "string",
                                       "enum": ["dispatcher", "watchdog", "repo-hygiene",
                                                "briefing", "ABSTAIN"]}},
                                   "required": ["capability"]}}},
    "stream": False,
}
try:
    req = urllib.request.Request(BASE + "/v1/chat/completions", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode())
    print("C1 response_format supported")
    print("answer:", d["choices"][0]["message"].get("content", "")[:200])
except Exception as e:
    print("C1 failed:", str(e)[:300])

# C2: GBNF grammar on /completion endpoint (finite choice)
grammar = 'root ::= ("dispatcher" | "watchdog" | "repo-hygiene" | "briefing" | "ABSTAIN")'
payload2 = {"prompt": "Classify: Nightly hygiene found 3 stale branches.\nAnswer with one word:",
            "n_predict": 10, "temperature": 0.1, "top_k": 50, "grammar": grammar,
            "stream": False}
try:
    req = urllib.request.Request(BASE + "/completion", data=json.dumps(payload2).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode())
    print("C2 GBNF supported; content:", repr(d.get("content", "")))
except Exception as e:
    print("C2 failed:", str(e)[:300])
