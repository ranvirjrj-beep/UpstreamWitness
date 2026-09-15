from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .version import SCHEMA_VERSION


@dataclass
class Candidate:
    sha: str
    url: str
    date: str
    message: str
    score: int = 0
    channels: int = 0
    reasons: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    discovery: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    name: str
    repo: str
    submitted_at: str
    observed_at: str
    candidates: list[Candidate]
    releases: list[dict[str, Any]]
    pr: dict[str, Any] | None
    listed_commits: int
    evaluated_candidates: int
    path_queries: int
    api_calls: int
    scan_truncated: bool
    rate_remaining: int | None = None
    case_fingerprint: str = ""

    @property
    def top_score(self) -> int:
        return max((c.score for c in self.candidates), default=0)

    @property
    def top_channels(self) -> int:
        return max((c.channels for c in self.candidates), default=0)

    @property
    def classification(self) -> str:
        if self.pr and self.pr.get("merged"):
            return "UPSTREAM_CONFIRMED"
        if self.top_score >= 10 and self.top_channels >= 2:
            return "STRONG_SIGNAL"
        if self.top_score >= 5 and self.top_channels >= 2:
            return "POSSIBLE_SIGNAL"
        return "NO_PUBLIC_SIGNAL"

    @property
    def confidence(self) -> str:
        return "HIGH" if self.classification in {"UPSTREAM_CONFIRMED", "STRONG_SIGNAL"} else "MEDIUM" if self.classification == "POSSIBLE_SIGNAL" else "LOW"

    @property
    def executive_finding(self) -> str:
        return {
            "UPSTREAM_CONFIRMED": "The tracked public pull request is publicly recorded as merged upstream.",
            "STRONG_SIGNAL": "Later public upstream changes strongly overlap the tracked submission across multiple independent evidence channels.",
            "POSSIBLE_SIGNAL": "Later public upstream activity shows meaningful overlap, but manual review is still needed before treating it as a likely related change.",
            "NO_PUBLIC_SIGNAL": "No sufficiently strong related public upstream change was detected within the configured scan window.",
        }[self.classification]

    @property
    def next_action(self) -> str:
        return {
            "UPSTREAM_CONFIRMED": "Preserve the public merge/release links. Treat payment, bounty acceptance, and attribution as separate questions requiring their own evidence.",
            "STRONG_SIGNAL": "Manually inspect the highest-ranked candidate diff and preserve relevant public links before using the evidence in any follow-up.",
            "POSSIBLE_SIGNAL": "Review candidate diffs manually and tighten sanitized paths/symbols/anchors before drawing a conclusion.",
            "NO_PUBLIC_SIGNAL": "Rescan later if needed; absence of a public signal does not prove absence of private work or a future fix.",
        }[self.classification]

    @property
    def evidence_fingerprint(self) -> str:
        payload = {
            "schema": SCHEMA_VERSION,
            "repo": self.repo,
            "submitted_at": self.submitted_at,
            "case_fingerprint": self.case_fingerprint,
            "classification": self.classification,
            "pr": {key: (self.pr or {}).get(key) for key in [
                "state", "merged", "merged_at", "merge_commit_sha", "head_sha",
                "latest_review_state", "latest_review_submitted_at",
                "latest_changes_requested_at", "latest_approval_at", "latest_approval_commit",
                "changes_requested_followed_by_new_head", "approval_on_current_head",
            ]},
            "candidates": [{"sha": c.sha, "score": c.score, "channels": c.channels, "reasons": c.reasons} for c in self.candidates[:15]],
            "releases": [{"tag": r.get("tag"), "published_at": r.get("published_at")} for r in self.releases],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
