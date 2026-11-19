"""MIN-002 regression tests: corrected harness units, scoped flags, feedback log."""
import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from minimoo.chat import split_reasoning, parse_xml_tool_calls, template_check, ChatClient, ChatError
from minimoo import control
from minimoo.control import check_tool_call, PolicyDenied, cap_enabled
from minimoo.store import Store

class TChatUnits(unittest.TestCase):
    def test_split_reasoning_inline(self):
        t, a = split_reasoning("<think>hmm</think>Final answer here")
        self.assertEqual(t, "hmm")
        self.assertEqual(a, "Final answer here")

    def test_split_reasoning_absent(self):
        t, a = split_reasoning("Just an answer")
        self.assertEqual(t, "")
        self.assertEqual(a, "Just an answer")

    def test_xml_tool_calls(self):
        text = ('<tool_call>\n<function=search_keeper>\n<parameter=query>\nGPU pause\n</parameter>\n'
                '</function>\n</tool_call>')
        calls = parse_xml_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["function"]["name"], "search_keeper")
        self.assertEqual(calls[0]["function"]["arguments"], {"query": "GPU pause"})

    def test_template_check_official(self):
        good = template_check({"chat_template": "<|im_start|> x preserve_thinking enable_thinking "
                             "tool_call defer_loading additional_tools tool_response "
                             "CONTINUE_FINAL_MESSAGE_TAG"})
        self.assertTrue(good["official"])
        bad = template_check({"chat_template": "plain"})
        self.assertFalse(bad["official"])
        self.assertTrue(bad["missing"])

    def test_gpu_unavailable_fails_closed(self):
        cli = ChatClient(base="http://127.0.0.1:19999")
        with self.assertRaises(ChatError):
            cli.chat([{"role": "user", "content": "hi"}], max_tokens=8, timeout=5)

class TScopedFlags(unittest.TestCase):
    def setUp(self):
        for k in list(os.environ):
            if k.startswith("MINIMOO_CAP_") or k == "MINIMOO_MODEL_JOBS":
                del os.environ[k]

    def tearDown(self):
        self.setUp()

    def test_model_job_denied_by_default(self):
        self.assertFalse(cap_enabled("briefing"))
        with self.assertRaises(PolicyDenied):
            check_tool_call("briefing", "briefing.write", {"path": "."}, "F:/P", True)

    def test_scoped_flag_enables_one_only(self):
        os.environ["MINIMOO_CAP_SECRETARY_DRAFT"] = "1"
        self.assertTrue(cap_enabled("secretary-draft"))
        self.assertFalse(cap_enabled("briefing"))
        check_tool_call("secretary-draft", "briefing.write", {"path": "."}, "F:/P", True)
        with self.assertRaises(PolicyDenied):
            check_tool_call("briefing", "briefing.write", {"path": "."}, "F:/P", True)

    def test_deterministic_unaffected(self):
        self.assertTrue(cap_enabled("repo-hygiene"))
        check_tool_call("repo-hygiene", "repo.status", {"path": "."}, "F:/P")

    def test_unknown_capability_abstains(self):
        with self.assertRaises(PolicyDenied):
            check_tool_call("nope-job", "repo.status", {}, "F:/P")

class TFeedback(unittest.TestCase):
    def test_roundtrip(self):
        d = tempfile.mkdtemp()
        s = Store(os.path.join(d, "f.db"))
        r = s.log_feedback("secretary-draft", "approval", "draft approved with edits",
                           mission_id="MIN-002", by="matthew")
        self.assertTrue(r["id"].startswith("FB-"))
        rows = s.list_feedback("secretary-draft")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "approval")
        with self.assertRaises(ValueError):
            s.log_feedback("x", "bogus-kind", "y")
        s.close()

if __name__ == "__main__":
    unittest.main()
