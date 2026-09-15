from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Iterable

WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}|[A-Za-z0-9][A-Za-z0-9._/-]{3,}")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
TOKEN_RE = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})\b")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
GENERIC_TERMS = {
    "add", "adds", "added", "change", "changes", "chore", "code", "docs",
    "feature", "fix", "fixed", "fixes", "issue", "main", "patch", "pull",
    "release", "repo", "repository", "test", "tests", "update", "updated",
}
LOW_SIGNAL_BASENAMES = {
    "readme.md", "changelog.md", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "cargo.lock", "go.sum", "requirements.txt", ".gitignore",
}


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc(value: str) -> dt.datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def iso_z(value: dt.datetime) -> str:
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def words(values: Iterable[str], *, drop_generic: bool = False) -> set[str]:
    out: set[str] = set()
    for value in values:
        for token in WORD_RE.findall(value or ""):
            normalized = token.lower().strip("./_-")
            if len(normalized) < 3:
                continue
            if drop_generic and normalized in GENERIC_TERMS:
                continue
            out.add(normalized)
    return out


def text_tokens(text: str) -> set[str]:
    return words([text], drop_generic=True)


def phrase_hits(phrases: Iterable[str], text: str) -> list[str]:
    haystack = text.lower()
    return [p for p in phrases if p and p.lower() in haystack]


def path_hits(tracked_paths: Iterable[str], changed_files: Iterable[str]) -> list[str]:
    hits: list[str] = []
    tracked = [p.lower().strip() for p in tracked_paths if p and p.strip()]
    for filename in changed_files:
        fl = filename.lower().strip()
        for tl in tracked:
            if fl == tl or fl.endswith("/" + tl) or tl.endswith("/" + fl):
                hits.append(filename)
                break
    return hits


def is_low_signal_path(path: str) -> bool:
    return Path(path).name.lower() in LOW_SIGNAL_BASENAMES


def contains_sensitive_text(text: str) -> bool:
    return bool(EMAIL_RE.search(text) or JWT_RE.search(text) or TOKEN_RE.search(text) or PRIVATE_KEY_RE.search(text))
