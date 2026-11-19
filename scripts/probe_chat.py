"""Probe A–E: thinking on/off, grammar/structured output, function calling."""
import json, sys
sys.path.insert(0, ".")
from minimoo.chat import ChatClient, template_check

c = ChatClient()
props = c.props()
print("TEMPLATE:", json.dumps(template_check(props)))
print("server model:", (props.get("models") or props.get("model_path") or "?"))

print("\n=== A: thinking enabled (default) ===")
r = c.chat([{"role": "user", "content": "In one sentence, why back up files?"}],
           max_tokens=256)
print("think_len:", len(r["thinking"]), "| answer:", r["answer"][:200])
print("usage:", r["usage"])

print("\n=== B: thinking disabled ===")
try:
    r2 = c.chat([{"role": "user", "content": "In one sentence, why back up files?"}],
                max_tokens=256, thinking=False)
    print("think_len:", len(r2["thinking"]), "| answer:", r2["answer"][:200])
except Exception as e:
    print("B failed:", str(e)[:200])

print("\n=== D: native function calling ===")
tools = [
    {"type": "function", "function": {
        "name": "search_keeper",
        "description": "Search Speedy Keeper notes",
        "parameters": {"type": "object",
                       "properties": {"query": {"type": "string"}},
                       "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "repo_status",
        "description": "Show git branch and status for a repo",
        "parameters": {"type": "object",
                       "properties": {"repo": {"type": "string"}},
                       "required": ["repo"]}}},
]
r4 = c.chat([{"role": "system", "content": "You route workshop jobs. Use tools when they fit."},
             {"role": "user", "content": "Search keeper notes for GPU pause evidence."}],
            max_tokens=512, tools=tools, tool_choice="auto")
print("tool_calls:", json.dumps(r4["tool_calls"])[:500])
print("answer:", r4["answer"][:200])

print("\n=== E: structured JSON extraction ===")
r5 = c.chat([{"role": "system", "content": "Reply with a single JSON object only."},
             {"role": "user", "content": 'Extract from: "MIN-042 nightly hygiene run passed 11 tests in 3 min, commit abc123". Fields: mission_id, tests_passed, duration_min, commit.'}],
            max_tokens=256)
print("answer:", r5["answer"][:300])
try:
    print("json_ok:", json.loads(r5["answer"]))
except Exception as e:
    print("json_parse_failed:", str(e)[:120])
