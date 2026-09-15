import unittest
import upstreamwitness


class FalsePositiveMatrix(unittest.TestCase):
    def score(self, **overrides):
        base = dict(message="maintenance update", files=["unrelated.py"], patch="small cleanup", paths=["src/security/session.py"], symbols=["SessionGuard"], keywords=["session", "revocation"], anchors=["serialize session revocation"])
        base.update(overrides)
        return upstreamwitness.score_candidate(**base)

    def test_anchor_and_same_keywords_stay_one_text_channel(self):
        score, channels, _ = self.score(message="serialize session revocation")
        self.assertGreater(score, 0)
        self.assertEqual(channels, 1)

    def test_path_only_is_one_channel(self):
        score, channels, _ = self.score(files=["src/security/session.py"], patch="cleanup")
        self.assertGreater(score, 0); self.assertEqual(channels, 1)

    def test_readme_plus_keywords_is_one_real_channel(self):
        score, channels, _ = upstreamwitness.score_candidate(message="session revocation docs", files=["README.md"], patch="session revocation", paths=["README.md"], symbols=[], keywords=["session", "revocation"], anchors=[])
        self.assertGreater(score, 0); self.assertEqual(channels, 1)

    def test_path_plus_symbol_is_possible_not_strong(self):
        score, channels, _ = self.score(files=["src/security/session.py"], patch="+ SessionGuard", message="internal cleanup")
        result = upstreamwitness.ScanResult(name="x", repo="o/r", submitted_at="2026-01-01T00:00:00Z", observed_at="2026-01-02T00:00:00Z", candidates=[upstreamwitness.Candidate("s", "u", "d", "m", score=score, channels=channels)], releases=[], pr=None, listed_commits=1, evaluated_candidates=1, path_queries=1, api_calls=4, scan_truncated=False)
        self.assertEqual(result.classification, "POSSIBLE_SIGNAL")

    def test_anchor_path_symbol_can_be_strong(self):
        score, channels, _ = self.score(message="serialize session revocation", files=["src/security/session.py"], patch="+ SessionGuard")
        self.assertGreaterEqual(score, 10); self.assertGreaterEqual(channels, 3)

    def test_unrelated_security_words_do_not_match(self):
        self.assertEqual(self.score(message="security hardening for oauth cache", files=["src/oauth/cache.py"], patch="rotate oauth nonce")[:2], (0, 0))


if __name__ == "__main__": unittest.main()
