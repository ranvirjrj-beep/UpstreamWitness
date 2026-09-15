from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .api import GitHubAPI
from .util import contains_sensitive_text
from .reporting import write_result
from .scanner import scan

PR_URL_RE = re.compile(r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/pull/(?P<number>\d+)(?:[/?#].*)?$")
TITLE_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{2,}")
GENERIC = {"add", "adds", "added", "change", "changes", "chore", "code", "docs", "feature", "fix", "fixed", "fixes", "issue", "main", "patch", "pull", "release", "repo", "repository", "test", "tests", "update", "updated"}


def parse_pr_url(url: str) -> tuple[str, int]:
    match = PR_URL_RE.match(url.strip())
    if not match:
        raise ValueError("Expected a public GitHub PR URL like https://github.com/owner/repo/pull/123")
    return f"{match.group('owner')}/{match.group('repo')}", int(match.group("number"))


def title_keywords(title: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for token in TITLE_TOKEN_RE.findall(title):
        normalized = token.lower().strip("./_-")
        if len(normalized) < 3 or normalized in GENERIC or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out[:12]


def safe_extra_keyword(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Extra keyword cannot be empty")
    if len(value) > 80:
        raise ValueError("Extra keyword is too long; use a short sanitized concept")
    if contains_sensitive_text(value):
        raise ValueError("Extra keyword looks sensitive; use a sanitized concept instead")
    return value.lower()


def fetch_changed_files(client: GitHubAPI, repo: str, number: int) -> list[str]:
    files: list[str] = []
    page = 1
    while True:
        rows = client.get(f"/repos/{repo}/pulls/{number}/files?per_page=100&page={page}")
        if not rows:
            break
        files.extend(row.get("filename", "") for row in rows if row.get("filename"))
        if len(rows) < 100:
            break
        page += 1
        if page > 10:
            raise RuntimeError("PR changes more than 1000 files; create a narrower manual case config")
    return files


def build_case(url: str, *, extra_keywords: list[str] | None = None, client: GitHubAPI | None = None) -> dict[str, Any]:
    client = client or GitHubAPI()
    repo, number = parse_pr_url(url)
    repo_meta = client.get(f"/repos/{repo}")
    if repo_meta.get("private"):
        raise ValueError("UpstreamWitness public mode refuses private repositories")
    pr = client.get(f"/repos/{repo}/pulls/{number}")
    title = (pr.get("title") or "").strip()
    created_at = pr.get("created_at")
    if not created_at:
        raise RuntimeError("PR metadata did not include created_at")
    keywords = title_keywords(title)
    for raw in extra_keywords or []:
        item = safe_extra_keyword(raw)
        if item not in keywords:
            keywords.append(item)
    files = fetch_changed_files(client, repo, number)[:100]
    return {
        "name": f"{repo} public PR #{number}",
        "repo": repo,
        "submitted_at": created_at,
        "pr_number": number,
        "paths": files,
        "symbols": [],
        "keywords": keywords[:20],
        "anchors": [title] if title else [],
        "max_commits": 40,
        "path_commit_limit": 15,
        "max_path_queries": 8,
        "max_candidate_details": 20,
    }


def write_case(case: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(case, indent=2) + "\n", encoding="utf-8")


def trace_public_pr(url: str, out_dir: Path, *, extra_keywords: list[str] | None = None):
    client = GitHubAPI()
    case = build_case(url, extra_keywords=extra_keywords or [], client=client)
    result = scan(case, client=client)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_case(case, out_dir / "case.json")
    write_result(result, markdown=out_dir / "report.md", json_path=out_dir / "report.json")
    return result
