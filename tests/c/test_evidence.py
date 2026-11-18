"""Bounded synthetic contract tests; no target import, network, or source writes."""
import copy
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))
from reqea_evidence import evaluate, render_html

SHA = "a" * 40
OTHER_SHA = "b" * 40
DIGEST = "c" * 64


def fixture():
    manifest = {
        "schema_version": "reqea.v1", "source_sha": SHA, "policy_sha": OTHER_SHA,
        "requirements": [{"req_id": "REQ-019", "title": "Run safely", "description": "Read-only",
          "acceptance_criteria": ["Run at src/app.py:run", "Never execute untrusted code"],
          "explicit_refs": ["src/app.py:run"], "source_document": "docs/REQ.md"}],
        "warnings": []}
    index = {"schema_version": "reqea.v1", "source_sha": SHA,
        "files": [{"path": "src/app.py", "language": "python", "sha256": DIGEST,
                   "bytes": 15, "symbols": [{"name": "run", "kind": "function", "line": 10}],
                   "imports": []}], "edges": [], "warnings": [],
        "limits": {"truncated": False, "scanned_files": 1, "skipped_files": 0}}
    return manifest, index


class EvidenceTests(unittest.TestCase):
    def test_exact_candidate_and_criterion_uncertainty(self):
        m, i = fixture()
        a = evaluate(m, i, {})
        self.assertEqual(a["findings"][0]["status"], "CODE_CANDIDATE")
        self.assertEqual(a["findings"][0]["evidence"][0],
            {"path": "src/app.py", "symbol": "run", "line": 10,
             "kind": "static", "source_sha": SHA})
        self.assertEqual([x["status"] for x in a["findings"][0]["acceptance_criteria"]],
                         ["CODE_CANDIDATE", "UNASSESSED"])
        self.assertEqual(a["summary"]["code_candidates"], 1)
        self.assertNotIn("VERIFIED", json.dumps(a))

    def test_sha_mismatch_removes_evidence(self):
        m, i = fixture()
        i["source_sha"] = OTHER_SHA
        a = evaluate(m, i, {})
        self.assertEqual(a["status"], "REVIEW_REQUIRED")
        self.assertEqual(a["findings"][0]["evidence"], [])
        self.assertIn("SOURCE_SHA_MISMATCH", a["warnings"])

    def test_truncated_scan_is_not_gap(self):
        m, i = fixture()
        i["files"] = []
        i["limits"]["truncated"] = True
        a = evaluate(m, i, {})
        self.assertEqual(a["findings"][0]["status"], "UNASSESSED")
        i["limits"]["truncated"] = False
        a = evaluate(m, i, {})
        self.assertEqual(a["findings"][0]["status"], "GAP_CANDIDATE")

    def test_missing_criteria_never_yields_candidate(self):
        m, i = fixture()
        m["requirements"][0]["acceptance_criteria"] = []
        self.assertEqual(evaluate(m, i, {})["status"], "UNASSESSED")

    def test_conflicting_digest_quarantines_path(self):
        m, i = fixture()
        x = copy.deepcopy(i["files"][0])
        x["sha256"] = "f" * 64
        i["files"].extend([x, copy.deepcopy(i["files"][0])])
        a = evaluate(m, i, {})
        self.assertEqual(a["status"], "REVIEW_REQUIRED")
        self.assertEqual(a["findings"][0]["evidence"], [])
        self.assertIn("CONFLICTING_FILE_HASH", a["warnings"])

    def test_reject_bad_contract_and_duplicate_ids(self):
        m, i = fixture()
        i["schema_version"] = "reqea.v2"
        with self.assertRaises(ValueError):
            evaluate(m, i, {})
        i["schema_version"] = "reqea.v1"
        m["requirements"].append(copy.deepcopy(m["requirements"][0]))
        with self.assertRaises(ValueError):
            evaluate(m, i, {})

    def test_deterministic_sort_and_json(self):
        m, i = fixture()
        req2 = copy.deepcopy(m["requirements"][0])
        req2.update(req_id="REQ-002", explicit_refs=["src/not_present.py"])
        m["requirements"].append(req2)
        one = json.dumps(evaluate(m, i, {}), ensure_ascii=False, sort_keys=True)
        m["requirements"].reverse()
        two = json.dumps(evaluate(m, i, {}), ensure_ascii=False, sort_keys=True)
        self.assertEqual(one, two)
        self.assertEqual([f["req_id"] for f in evaluate(m, i, {})["findings"]],
                         ["REQ-002", "REQ-019"])

    def test_html_escapes_and_redacts_untrusted_text(self):
        m, i = fixture()
        a = evaluate(m, i, {})
        a["findings"][0]["rationale"] = '<script>alert(1)</script>'
        a["findings"][0]["evidence"][0]["path"] = 'src/<img src=x onerror=alert(1)>.py'
        a["findings"][0]["acceptance_criteria"][0]["criterion"] = 'PASSWORD=supersecret'
        a["warnings"].append('Authorization: Bearer secret123')
        html = render_html(a)
        self.assertIn("rationale redacted", html)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img", html)
        self.assertNotIn("supersecret", html)
        self.assertNotIn("secret123", html)
        self.assertIn("[path redacted]", html)
        self.assertIn("WARNING_REDACTED", html)

    def test_malformed_report_values_do_not_execute_or_leak(self):
        m, i = fixture()
        a = evaluate(m, i, {})
        a["source_sha"] = {"secret": "do-not-show"}
        a["status"] = ["<script>bad</script>"]
        a["findings"][0]["status"] = []
        a["findings"][0]["rationale"] = {"private": "do-not-show"}
        a["findings"][0]["acceptance_criteria"][0]["status"] = []
        html = render_html(a)
        self.assertNotIn("do-not-show", html)
        self.assertNotIn("<script>", html)
        self.assertIn("UNASSESSED", html)

    def test_invalid_path_not_evidence(self):
        m, i = fixture()
        m["requirements"][0]["explicit_refs"] = ["../../.env", "/tmp/secret.py"]
        a = evaluate(m, i, {})
        self.assertEqual(a["findings"][0]["status"], "UNASSESSED")
        self.assertEqual(a["findings"][0]["evidence"], [])
        self.assertIn("INVALID_EXPLICIT_REF", a["warnings"])

    def test_js_ts_unindexed_reference_is_unassessed(self):
        m, i = fixture()
        m["requirements"][0]["explicit_refs"] = ["src/client.ts"]
        i["files"] = []
        a = evaluate(m, i, {})
        self.assertEqual(a["status"], "UNASSESSED")
        self.assertIn("UNSUPPORTED_STATIC_SCOPE", a["warnings"])

    def test_skipped_scan_blocks_false_gap(self):
        m, i = fixture()
        i["files"] = []
        i["limits"]["skipped_files"] = 2
        self.assertEqual(evaluate(m, i, {})["status"], "UNASSESSED")


if __name__ == "__main__":
    unittest.main()
