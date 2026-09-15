from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any

from .util import contains_sensitive_text, is_low_signal_path, iso_z, path_hits, phrase_hits, text_tokens, utc, words

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def _bounded_strings(value: Any, name: str, *, max_items: int, max_len: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a JSON array")
    if len(value) > max_items:
        raise ValueError(f"{name} has too many items (max {max_items})")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{name} items must be strings")
        item = item.strip()
        if not item:
            continue
        if len(item) > max_len:
            raise ValueError(f"{name} item exceeds {max_len} characters")
        if name in {"symbols", "keywords", "anchors"} and contains_sensitive_text(item):
            raise ValueError(f"{name} contains sensitive-looking text; use sanitized metadata")
        out.append(item)
    return out


def _validate_repo_paths(paths: list[str]) -> list[str]:
    clean: list[str] = []
    for value in paths:
        if value.startswith(("/", "~")) or "\\" in value or re.match(r"^[A-Za-z]:", value):
            raise ValueError("paths must be relative public-repository paths, not local filesystem paths")
        path = PurePosixPath(value)
        if ".." in path.parts or not path.parts or "." == value:
            raise ValueError("paths must not contain traversal components")
        clean.append(path.as_posix())
    return clean


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ValueError("case config must be a JSON object")
    repo = str(config.get("repo", "")).strip()
    if not REPO_RE.match(repo):
        raise ValueError("repo must use owner/name format")
    submitted_at = str(config.get("submitted_at", "")).strip()
    if not submitted_at:
        raise ValueError("submitted_at is required")
    utc(submitted_at)

    name = str(config.get("name") or repo).strip()[:240]
    if contains_sensitive_text(name):
        raise ValueError("name contains sensitive-looking text; use a sanitized label")

    pr_number = config.get("pr_number")
    if pr_number is not None:
        pr_number = int(pr_number)
        if pr_number <= 0:
            raise ValueError("pr_number must be positive")

    settings = {
        "max_commits": (int(config.get("max_commits", 40)), 1, 100),
        "path_commit_limit": (int(config.get("path_commit_limit", 15)), 1, 30),
        "max_path_queries": (int(config.get("max_path_queries", 8)), 0, 12),
        "max_candidate_details": (int(config.get("max_candidate_details", 20)), 1, 30),
    }
    for setting_name, (value, lower, upper) in settings.items():
        if not lower <= value <= upper:
            raise ValueError(f"{setting_name} must be between {lower} and {upper}")

    paths = _bounded_strings(config.get("paths"), "paths", max_items=100, max_len=300)
    normalized = dict(config)
    normalized.update({
        "name": name,
        "repo": repo,
        "submitted_at": iso_z(utc(submitted_at)),
        "pr_number": pr_number,
        "paths": _validate_repo_paths(paths),
        "symbols": _bounded_strings(config.get("symbols"), "symbols", max_items=50, max_len=120),
        "keywords": _bounded_strings(config.get("keywords"), "keywords", max_items=50, max_len=120),
        "anchors": _bounded_strings(config.get("anchors"), "anchors", max_items=20, max_len=240),
        **{setting_name: value[0] for setting_name, value in settings.items()},
    })
    return normalized


def case_fingerprint(config: dict[str, Any]) -> str:
    cfg = validate_config(config)
    tracked = {
        key: cfg.get(key)
        for key in [
            "name", "repo", "submitted_at", "pr_number", "paths", "symbols",
            "keywords", "anchors", "max_commits", "path_commit_limit",
            "max_path_queries", "max_candidate_details",
        ]
    }
    raw = json.dumps(tracked, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def score_candidate(*, message: str, files: list[str], patch: str, paths: list[str], symbols: list[str], keywords: list[str], anchors: list[str]) -> tuple[int, int, list[str]]:
    """Score candidate evidence without double-counting repeated wording."""
    score = 0
    channels = 0
    reasons: list[str] = []
    combined = "\n".join([message, patch])

    text_channel = False
    anchor_matches = phrase_hits(anchors, combined)
    if anchor_matches:
        text_channel = True
        score += min(8, 4 * len(anchor_matches))
        reasons.append("anchor phrase: " + ", ".join(anchor_matches[:4]))
    overlap = words(keywords, drop_generic=True) & text_tokens(combined)
    if len(overlap) >= 2:
        text_channel = True
        score += min(4, len(overlap))
        reasons.append("keyword overlap: " + ", ".join(sorted(overlap)[:8]))
    if text_channel:
        channels += 1

    exact_paths = path_hits(paths, files)
    strong_paths = [p for p in exact_paths if not is_low_signal_path(p)]
    weak_paths = [p for p in exact_paths if is_low_signal_path(p)]
    if strong_paths:
        channels += 1
        score += min(6, 3 + len(strong_paths))
        reasons.append("tracked path: " + ", ".join(strong_paths[:6]))
    if weak_paths:
        score += 1
        reasons.append("low-signal tracked file: " + ", ".join(weak_paths[:4]))

    symbol_matches = phrase_hits(symbols, patch)
    if symbol_matches:
        channels += 1
        score += min(6, 2 * len(symbol_matches))
        reasons.append("symbol in patch: " + ", ".join(symbol_matches[:6]))
    return score, channels, reasons


def review_snapshot(reviews: list[dict[str, Any]], head_sha: str | None, head_commit_at: str | None) -> dict[str, Any]:
    submitted = [r for r in reviews if r.get("submitted_at")]
    latest = max(submitted, key=lambda r: r["submitted_at"], default=None)
    requests = [r for r in submitted if r.get("state") == "CHANGES_REQUESTED"]
    approvals = [r for r in submitted if r.get("state") == "APPROVED"]
    latest_request = max(requests, key=lambda r: r["submitted_at"], default=None)
    latest_approval = max(approvals, key=lambda r: r["submitted_at"], default=None)
    request_at = latest_request.get("submitted_at") if latest_request else None
    approval_at = latest_approval.get("submitted_at") if latest_approval else None
    newer_head = bool(request_at and head_commit_at and utc(head_commit_at) > utc(request_at))

    approval_commit = latest_approval.get("commit_id") if latest_approval else None
    if latest_approval and head_sha and approval_commit:
        approval_on_current_head = approval_commit == head_sha
    else:
        approval_on_current_head = bool(approval_at and head_commit_at and utc(approval_at) >= utc(head_commit_at))

    return {
        "latest_review_state": latest.get("state") if latest else None,
        "latest_review_submitted_at": latest.get("submitted_at") if latest else None,
        "latest_changes_requested_at": request_at,
        "latest_approval_at": approval_at,
        "latest_approval_commit": approval_commit,
        "changes_requested_followed_by_new_head": newer_head,
        "approval_on_current_head": approval_on_current_head,
    }
