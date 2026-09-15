from __future__ import annotations

import urllib.parse
from typing import Any

from .api import GitHubAPI
from .core import case_fingerprint, review_snapshot, score_candidate, validate_config
from .model import Candidate, ScanResult
from .util import is_low_signal_path, iso_z, now_utc, phrase_hits, text_tokens, utc, words


def _prefilter(row: dict[str, Any], anchors: list[str], keywords: list[str], symbols: list[str]) -> bool:
    message = row.get("commit", {}).get("message", "")
    if phrase_hits(anchors, message):
        return True
    meaningful = words(keywords, drop_generic=True) | words(symbols, drop_generic=True)
    return len(meaningful & text_tokens(message)) >= 2


def scan(config: dict[str, Any], *, client: GitHubAPI | None = None) -> ScanResult:
    cfg = validate_config(config)
    client = client or GitHubAPI()
    repo = cfg["repo"]

    repo_meta = client.get(f"/repos/{repo}")
    if repo_meta.get("private"):
        raise ValueError("UpstreamWitness public mode refuses private repositories; use a public upstream target")

    submitted = utc(cfg["submitted_at"])
    since = urllib.parse.quote(iso_z(submitted), safe="")
    general = client.get(f"/repos/{repo}/commits?since={since}&per_page={cfg['max_commits']}")

    discovery: dict[str, set[str]] = {}
    row_by_sha: dict[str, dict[str, Any]] = {}
    for row in general:
        sha = row.get("sha")
        if not sha:
            continue
        row_by_sha[sha] = row
        if _prefilter(row, cfg["anchors"], cfg["keywords"], cfg["symbols"]):
            discovery.setdefault(sha, set()).add("message")

    query_paths = [p for p in cfg["paths"] if not is_low_signal_path(p)][: cfg["max_path_queries"]]
    path_queries = 0
    for tracked in query_paths:
        encoded = urllib.parse.quote(tracked, safe="")
        rows = client.get(f"/repos/{repo}/commits?path={encoded}&since={since}&per_page={cfg['path_commit_limit']}")
        path_queries += 1
        for row in rows:
            sha = row.get("sha")
            if not sha:
                continue
            row_by_sha.setdefault(sha, row)
            discovery.setdefault(sha, set()).add("path")

    pr_row: dict[str, Any] | None = None
    reviews: list[dict[str, Any]] = []
    if cfg.get("pr_number"):
        number = int(cfg["pr_number"])
        pr_row = client.get(f"/repos/{repo}/pulls/{number}")
        reviews = client.get(f"/repos/{repo}/pulls/{number}/reviews?per_page=100")
        if pr_row.get("merged") and pr_row.get("merge_commit_sha"):
            discovery.setdefault(pr_row["merge_commit_sha"], set()).add("tracked-pr-merge")

    def rank_sha(sha: str) -> tuple[int, str]:
        sources = discovery.get(sha, set())
        priority = 2 if ("tracked-pr-merge" in sources or "message" in sources) else 1
        date = row_by_sha.get(sha, {}).get("commit", {}).get("committer", {}).get("date", "")
        return priority, date

    ordered = sorted(discovery, key=rank_sha, reverse=True)
    scan_truncated = len(ordered) > cfg["max_candidate_details"]
    ordered = ordered[: cfg["max_candidate_details"]]

    details_cache: dict[str, dict[str, Any]] = {}
    candidates: list[Candidate] = []
    for sha in ordered:
        details = client.get(f"/repos/{repo}/commits/{sha}")
        details_cache[sha] = details
        message = details.get("commit", {}).get("message", "")
        date = details.get("commit", {}).get("committer", {}).get("date") or details.get("commit", {}).get("author", {}).get("date") or ""
        files = [f.get("filename", "") for f in details.get("files", []) if f.get("filename")]
        patch = "\n".join(f.get("patch") or "" for f in details.get("files", []))
        score, channels, reasons = score_candidate(
            message=message,
            files=files,
            patch=patch,
            paths=cfg["paths"],
            symbols=cfg["symbols"],
            keywords=cfg["keywords"],
            anchors=cfg["anchors"],
        )
        if score:
            candidates.append(Candidate(
                sha=sha,
                url=details.get("html_url", f"https://github.com/{repo}/commit/{sha}"),
                date=date,
                message=message.splitlines()[0] if message else "",
                score=score,
                channels=channels,
                reasons=reasons,
                files=files,
                discovery=sorted(discovery.get(sha, set())),
            ))
    candidates.sort(key=lambda c: (c.score, c.channels, c.date), reverse=True)

    releases = []
    for release in client.get(f"/repos/{repo}/releases?per_page=30"):
        published = release.get("published_at") or release.get("created_at")
        if published and utc(published) >= submitted:
            releases.append({
                "tag": release.get("tag_name"),
                "name": release.get("name"),
                "published_at": published,
                "url": release.get("html_url"),
            })

    pr = None
    if pr_row is not None:
        head_sha = pr_row.get("head", {}).get("sha")
        head_repo = (pr_row.get("head", {}).get("repo") or {}).get("full_name") or repo
        head_commit_at = None
        if head_sha:
            head = details_cache.get(head_sha) if head_repo == repo else None
            if head is None:
                head = client.get(f"/repos/{head_repo}/commits/{head_sha}")
            head_commit_at = head.get("commit", {}).get("committer", {}).get("date") or head.get("commit", {}).get("author", {}).get("date")
        merged = bool(pr_row.get("merged"))
        pr = {
            "number": pr_row.get("number"),
            "state": pr_row.get("state"),
            "base_ref": pr_row.get("base", {}).get("ref"),
            "merged": merged,
            "merge_commit_sha": pr_row.get("merge_commit_sha") if merged else None,
            "head_sha": head_sha,
            "head_repo": head_repo,
            "head_commit_at": head_commit_at,
            "updated_at": pr_row.get("updated_at"),
            "merged_at": pr_row.get("merged_at"),
            "closed_at": pr_row.get("closed_at"),
            "url": pr_row.get("html_url"),
            "title": pr_row.get("title"),
            **review_snapshot(reviews, head_sha, head_commit_at),
        }

    return ScanResult(
        name=cfg["name"],
        repo=repo,
        submitted_at=cfg["submitted_at"],
        observed_at=now_utc(),
        candidates=candidates,
        releases=releases,
        pr=pr,
        listed_commits=len(general),
        evaluated_candidates=len(ordered),
        path_queries=path_queries,
        api_calls=client.calls,
        scan_truncated=scan_truncated,
        rate_remaining=client.rate_remaining,
        case_fingerprint=case_fingerprint(cfg),
    )
