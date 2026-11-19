"""Deferred tool discovery probe (mission 7): search first, then use found tool."""
import json, sys
sys.path.insert(0, ".")
from minimoo.chat import ChatClient

cli = ChatClient()
search_tool = {"type": "function", "function": {
    "name": "search_tools",
    "description": "Search the tool catalog by keyword. Returns tool names.",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                   "required": ["query"]}}}
repo_tool = {"type": "function", "function": {
    "name": "repo_status", "defer_loading": True,
    "description": "Show git branch and status for a repo",
    "parameters": {"type": "object", "properties": {"repo": {"type": "string"}},
                   "required": ["repo"]}}}

msgs = [{"role": "system", "content": ("You only have one tool right now: search_tools, "
         "which searches a catalog of many more tools. If none of your current tools "
         "can handle a request, call search_tools to find one, then call the tool it returns.")},
        {"role": "user", "content": "Is the Minimoo repo clean or dirty? Check F:/Projects/Minimoo."}]
r1 = cli.chat(msgs, max_tokens=512, tools=[search_tool, repo_tool], tool_choice="auto")
print("turn1 calls:", json.dumps(r1["tool_calls"])[:300])
print("turn1 text:", r1["answer"][:150])
# Simulate harness executing search_tools -> returns tool_reference for repo_status
calls = r1.get("tool_calls", [])
names = []
for tc in calls:
    fn = tc["function"]["name"]
    a = tc["function"].get("arguments", {})
    a = json.loads(a) if isinstance(a, str) else a
    if fn == "search_tools":
        q = str(a.get("query", "")).lower()
        names = ["repo_status"] if any(w in q for w in ("repo", "git", "status", "branch", "clean", "dirty") ) else []
print("search returned:", names)
