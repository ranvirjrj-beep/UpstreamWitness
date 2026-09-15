import copy
import unittest

import upstreamwitness
from upstreamwitness import core


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0
        self.rate_remaining = 50
        self.rate_reset = None
        self.paths = []
    def get(self, path):
        self.calls += 1
        self.paths.append(path)
        if path not in self.responses:
            raise AssertionError(f"unexpected API path: {path}")
        return copy.deepcopy(self.responses[path])


def make_result(*, candidates=None, pr=None, observed_at="2026-01-02T00:00:00Z", api_calls=4):
    return upstreamwitness.ScanResult(
        name="demo", repo="owner/repo", submitted_at="2026-01-01T00:00:00Z",
        observed_at=observed_at, candidates=candidates or [], releases=[], pr=pr,
        listed_commits=4, evaluated_candidates=len(candidates or []), path_queries=1,
        api_calls=api_calls, scan_truncated=False, rate_remaining=50,
    )


class CoreTests(unittest.TestCase):
    def test_config_rejects_sensitive_keyword(self):
        with self.assertRaises(ValueError):
            upstreamwitness.validate_config({"repo": "owner/repo", "submitted_at": "2026-01-01T00:00:00Z", "keywords": ["person@example.com"]})

    def test_config_rejects_local_filesystem_path(self):
        with self.assertRaises(ValueError):
            upstreamwitness.validate_config({"repo": "owner/repo", "submitted_at": "2026-01-01T00:00:00Z", "paths": ["C:\\Users\\name\\secret.py"]})

    def test_config_rejects_sensitive_case_name(self):
        with self.assertRaises(ValueError):
            upstreamwitness.validate_config({"name": "contact person@example.com", "repo": "owner/repo", "submitted_at": "2026-01-01T00:00:00Z"})

    def test_case_fingerprint_changes_when_tracking_config_changes(self):
        first = core.case_fingerprint({"repo": "owner/repo", "submitted_at": "2026-01-01T00:00:00Z", "paths": ["src/a.py"]})
        second = core.case_fingerprint({"repo": "owner/repo", "submitted_at": "2026-01-01T00:00:00Z", "paths": ["src/b.py"]})
        self.assertNotEqual(first, second)

    def test_approval_must_apply_to_current_head(self):
        snap = core.review_snapshot([
            {"state": "APPROVED", "submitted_at": "2026-01-02T13:00:00Z", "commit_id": "old"}
        ], "new", "2026-01-02T12:00:00Z")
        self.assertFalse(snap["approval_on_current_head"])

    def test_generic_terms_do_not_count(self):
        self.assertEqual(
            upstreamwitness.score_candidate(message="fix tests and update docs", files=["README.md"], patch="updated tests", paths=["src/session.py"], symbols=["SessionService"], keywords=["fix", "update", "test"], anchors=[]),
            (0, 0, []),
        )

    def test_generic_metadata_path_is_weak(self):
        score, channels, reasons = upstreamwitness.score_candidate(message="docs refresh", files=["README.md"], patch="session lifecycle", paths=["README.md"], symbols=[], keywords=[], anchors=[])
        self.assertEqual((score, channels), (1, 0))
        self.assertTrue(any("low-signal" in r for r in reasons))

    def test_strong_requires_multiple_channels(self):
        one = make_result(candidates=[upstreamwitness.Candidate("a", "u", "d", "m", score=12, channels=1)])
        two = make_result(candidates=[upstreamwitness.Candidate("b", "u", "d", "m", score=10, channels=2)])
        self.assertEqual(one.classification, "NO_PUBLIC_SIGNAL")
        self.assertEqual(two.classification, "STRONG_SIGNAL")

    def test_merged_pr_is_confirmed(self):
        self.assertEqual(make_result(pr={"merged": True}).classification, "UPSTREAM_CONFIRMED")

    def test_review_snapshot_keeps_old_change_request_after_comment(self):
        snap = core.review_snapshot([
            {"state": "CHANGES_REQUESTED", "submitted_at": "2026-01-01T10:00:00Z"},
            {"state": "COMMENTED", "submitted_at": "2026-01-01T11:00:00Z"},
        ], "head123", "2026-01-01T12:00:00Z")
        self.assertEqual(snap["latest_review_state"], "COMMENTED")
        self.assertTrue(snap["changes_requested_followed_by_new_head"])

    def test_fingerprint_ignores_observation_time(self):
        self.assertEqual(make_result(observed_at="2026-01-02T00:00:00Z").evidence_fingerprint, make_result(observed_at="2026-01-03T00:00:00Z", api_calls=99).evidence_fingerprint)

    def test_scan_fetches_details_only_for_candidates(self):
        since = "2026-01-01T00%3A00%3A00Z"
        responses = {
            "/repos/owner/repo": {"private": False},
            f"/repos/owner/repo/commits?since={since}&per_page=40": [
                {"sha": "msg", "commit": {"message": "session lifecycle follow-up", "committer": {"date": "2026-01-05T00:00:00Z"}}},
                {"sha": "noise", "commit": {"message": "docs", "committer": {"date": "2026-01-04T00:00:00Z"}}},
            ],
            f"/repos/owner/repo/commits?path=src%2Fsession.py&since={since}&per_page=15": [
                {"sha": "path", "commit": {"message": "internal cleanup", "committer": {"date": "2026-01-06T00:00:00Z"}}}
            ],
            "/repos/owner/repo/commits/msg": {"html_url": "u1", "commit": {"message": "session lifecycle follow-up", "committer": {"date": "2026-01-05T00:00:00Z"}}, "files": [{"filename": "other.py", "patch": "+ session lifecycle"}]},
            "/repos/owner/repo/commits/path": {"html_url": "u2", "commit": {"message": "internal cleanup", "committer": {"date": "2026-01-06T00:00:00Z"}}, "files": [{"filename": "src/session.py", "patch": "+ SessionService lifecycle_guard"}]},
            "/repos/owner/repo/releases?per_page=30": [],
        }
        client = FakeClient(responses)
        result = upstreamwitness.scan({"repo": "owner/repo", "submitted_at": "2026-01-01T00:00:00Z", "paths": ["src/session.py"], "symbols": ["SessionService"], "keywords": ["session", "lifecycle"]}, client=client)
        self.assertEqual(result.evaluated_candidates, 2)
        self.assertNotIn("/repos/owner/repo/commits/noise", client.paths)
        self.assertEqual(result.classification, "POSSIBLE_SIGNAL")
        self.assertEqual(result.api_calls, 6)

    def test_report_has_limits_and_non_entitlement_language(self):
        text = upstreamwitness.report(make_result())
        self.assertIn("Evidence fingerprint", text)
        self.assertIn("not proof of attribution", text)
        self.assertIn("payment entitlement", text)
        self.assertIn("## Limits", text)


if __name__ == "__main__": unittest.main()
