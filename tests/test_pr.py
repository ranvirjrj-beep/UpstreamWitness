import unittest
from upstreamwitness import pr


class FakeClient:
    def __init__(self): self.calls = 0
    def get(self, path):
        self.calls += 1
        if path == "/repos/example/project":
            return {"private": False}
        if path == "/repos/example/project/pulls/9":
            return {"title": "security: serialize lifecycle across workers", "body": "PRIVATE-SHOULD-NOT-BE-COPIED", "created_at": "2026-09-10T15:49:43Z"}
        if path == "/repos/example/project/pulls/9/files?per_page=100&page=1":
            return [{"filename": "src/session.py"}, {"filename": "tests/test_session.py"}]
        raise AssertionError(path)


class PrivateClient:
    def __init__(self): self.calls = 0
    def get(self, path):
        self.calls += 1
        if path == "/repos/example/private": return {"private": True}
        raise AssertionError("private PR metadata should not be fetched")


class PRTests(unittest.TestCase):
    def test_parse_url(self):
        self.assertEqual(pr.parse_pr_url("https://github.com/example/project/pull/123"), ("example/project", 123))
    def test_reject_issue_url(self):
        with self.assertRaises(ValueError): pr.parse_pr_url("https://github.com/example/project/issues/123")
    def test_title_keywords_keep_compounds(self):
        words = pr.title_keywords("fix: add scheduled auto-rebalance dry-run mode")
        self.assertIn("auto-rebalance", words); self.assertIn("dry-run", words); self.assertNotIn("fix", words)
    def test_sensitive_extra_keyword_rejected(self):
        with self.assertRaises(ValueError): pr.safe_extra_keyword("note person@example.com here")
    def test_private_repo_fails_before_pr_fetch(self):
        with self.assertRaises(ValueError): pr.build_case("https://github.com/example/private/pull/9", client=PrivateClient())

    def test_build_case_never_copies_body(self):
        case = pr.build_case("https://github.com/example/project/pull/9", client=FakeClient())
        self.assertNotIn("PRIVATE-SHOULD-NOT-BE-COPIED", repr(case))
        self.assertEqual(case["paths"], ["src/session.py", "tests/test_session.py"])


if __name__ == "__main__": unittest.main()
