import os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from minimoo.store import Store
from minimoo.control import check_tool_call, PolicyDenied, route_mission
from tests.qualify_suite import SUITE

class TStore(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.s = Store(os.path.join(self.d, "t.db"))

    def tearDown(self):
        self.s.close()

    def test_submit_claim_recover(self):
        j = self.s.submit_job("MIN-001", "hello", "body")
        self.assertEqual(j["state"], "PENDING")
        c = self.s.claim_job("pi-cli")
        self.assertIsNotNone(c)
        self.assertEqual(c["id"], j["id"])
        # duplicate message: second claim finds nothing (no lost job, no dup exec)
        self.assertIsNone(self.s.claim_job("other"))
        # kill mid-job: force lease expiry then recover
        self.s.cx.execute("UPDATE jobs SET lease_until=0 WHERE id=?", (j["id"],))
        rec = self.s.recover_stale("watchdog")
        self.assertEqual(len(rec), 1)
        self.assertEqual(rec[0]["state"], "PENDING")

    def test_dedup(self):
        a = self.s.submit_job("MIN-001", "same", "body")
        b = self.s.submit_job("MIN-001", "same", "body")
        self.assertEqual(a["id"], b["id"])

    def test_receipt_validation(self):
        j = self.s.submit_job("MIN-001", "r", "")
        with self.assertRaises(ValueError):
            self.s.add_receipt("MIN-001", j["id"], "pi-cli", "DONE", {"summary": "x"}, [])
        r = self.s.add_receipt("MIN-001", j["id"], "pi-cli", "DONE",
                               {"summary": "x", "output_ref": "y", "checks": []}, [])
        self.assertTrue(r["id"].startswith("RCPT-"))

    def test_lucy_loop(self):
        m = "MIN-001"
        j = self.s.submit_job(m, "lucy mission", "")
        self.s.register_agent("pi-cli", ["dispatcher"])
        pkt = self.s.add_packet(m, "MISSION", "lucy", "minimoo", "do it", job_id=j["id"])
        self.assertEqual(pkt["state"], "STORED")
        self.s.packet_mark(pkt["id"], "RETRIEVED", "minimoo")
        self.s.packet_mark(pkt["id"], "ACKNOWLEDGED", "pi-cli")
        r = self.s.add_receipt(m, j["id"], "pi-cli", "DONE",
                               {"summary": "did", "output_ref": "ref", "checks": ["ok"]}, [])
        corr = self.s.add_packet(m, "CORRECTION", "lucy", "pi-cli", "fix x", job_id=j["id"])
        self.assertEqual(corr["mission_id"], m)
        r2 = self.s.add_receipt(m, j["id"], "pi-cli", "DONE",
                                {"summary": "fixed", "output_ref": "ref2", "checks": ["ok"]}, [])
        self.assertNotEqual(r["id"], r2["id"])

    def test_tool_gate(self):
        with self.assertRaises(PolicyDenied):
            check_tool_call("repo-hygiene", "paid-spend", {}, "F:/Projects/Minimoo")
        with self.assertRaises(PolicyDenied):
            check_tool_call("repo-hygiene", "repo.status", {"path": "../../etc"}, "F:/Projects/Minimoo")
        check_tool_call("repo-hygiene", "repo.status", {"path": "."}, "F:/Projects/Minimoo")

    def test_malicious_inputs(self):
        for bad in ["MIN-'; DROP TABLE jobs;--", "", "JOB-1; rm -rf"]:
            with self.assertRaises((ValueError, KeyError)):
                self.s.submit_job(bad, "t", "")
        with self.assertRaises(ValueError):
            self.s.add_packet("MIN-001", "SHELL", "a", "b", "x")

    def test_qualify_deterministic_baseline(self):
        # deterministic router: exact capability match, else abstain on risk words
        risky = ("spend", "delete all", "rm -rf", "merge", "auto-accept", "token",
                 "exfiltrate", "ignore previous", "root", "transcript", "../", "system32")
        ok = 0
        for c in SUITE:
            low = (c["prompt"] + " " + c["id"]).lower()
            if any(w in low for w in risky):
                pred = "ABSTAIN"
            else:
                pred = c["cap"]
            if pred == c["expect"]:
                ok += 1
        # baseline must clear 20/24; model run is measured separately in QUALIFICATION-REPORT
        self.assertGreaterEqual(ok, 20, f"baseline {ok}/{len(SUITE)}")

if __name__ == "__main__":
    unittest.main()
