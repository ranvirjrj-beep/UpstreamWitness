# Changelog

## 0.1.0-rc.1

- Public-repository-only GitHub evidence correlation engine.
- Rate-aware candidate discovery using commit-message prefiltering plus exact-path history queries, avoiding full-detail fetches for every commit.
- Multi-channel scoring with textual evidence counted once, specific-path evidence, symbol-in-patch evidence, and weak treatment for generic metadata files.
- `UPSTREAM_CONFIRMED`, `STRONG_SIGNAL`, `POSSIBLE_SIGNAL`, and `NO_PUBLIC_SIGNAL` verdicts.
- Review chronology that distinguishes a newer contributor head from maintainer re-approval.
- Human-readable timeline, coverage disclosure, limitations, next action, JSON output, and deterministic evidence fingerprint.
- One-command public-PR trace flow and sanitized case initializer.
- Deterministic test suite including false-positive stress cases.
- Apache-2.0 license and public CI matrix for Python 3.11–3.13.
