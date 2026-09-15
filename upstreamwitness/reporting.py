from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .model import ScanResult
from .util import utc
from .version import SCHEMA_VERSION, VERSION


def _timeline(result: ScanResult) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = [(result.submitted_at, "BASELINE", "Submission/report baseline")]
    if result.pr:
        p = result.pr
        if p.get("latest_changes_requested_at"):
            rows.append((p["latest_changes_requested_at"], "REVIEW", "Changes requested"))
        if p.get("head_commit_at"):
            rows.append((p["head_commit_at"], "PR HEAD", f"Current head `{str(p.get('head_sha'))[:8]}`"))
        if p.get("latest_approval_at"):
            rows.append((p["latest_approval_at"], "REVIEW", "Approval recorded"))
        if p.get("merged_at"):
            rows.append((p["merged_at"], "MERGE", f"Tracked PR merged as `{str(p.get('merge_commit_sha'))[:8]}`"))
    for candidate in result.candidates[:8]:
        if candidate.date:
            rows.append((candidate.date, "CANDIDATE", f"`{candidate.sha[:8]}` score {candidate.score}/{candidate.channels}: {candidate.message}"))
    for release in result.releases[:8]:
        if release.get("published_at"):
            rows.append((release["published_at"], "RELEASE", str(release.get("name") or release.get("tag") or "release")))
    return sorted(rows, key=lambda row: utc(row[0]))


def report(result: ScanResult) -> str:
    lines = [
        f"# UpstreamWitness evidence report — {result.name}", "",
        f"- Repository: `{result.repo}`",
        f"- Baseline: `{result.submitted_at}`",
        f"- Observed at: `{result.observed_at}`",
        f"- Verdict: **{result.classification}**",
        f"- Confidence: **{result.confidence}**",
        f"- Case fingerprint: `{result.case_fingerprint}`",
        f"- Evidence fingerprint: `{result.evidence_fingerprint}`", "",
        "## Executive finding", "", result.executive_finding, "",
        "> UpstreamWitness reports public-code correlation evidence. Correlation is not proof of attribution, bounty acceptance, legal entitlement, or payment entitlement. Human verification remains required.", "",
    ]
    if result.pr:
        p = result.pr
        lines += [
            "## Public PR state", "",
            f"- PR #{p['number']}: [{p['title']}]({p['url']})",
            f"- State: **{p['state']}**",
            f"- Base branch: `{p['base_ref']}`",
            f"- Merged: **{p['merged']}**",
            f"- Merged at: `{p['merged_at']}`",
            f"- Merge commit: `{p['merge_commit_sha']}`",
            f"- Current head: `{p['head_sha']}` at `{p['head_commit_at']}`",
            f"- Latest review: **{p['latest_review_state']}** at `{p['latest_review_submitted_at']}`",
            f"- Latest changes-requested review: `{p['latest_changes_requested_at']}`",
            f"- Latest approval: `{p['latest_approval_at']}`",
            f"- Latest approval commit: `{p['latest_approval_commit']}`",
            f"- Newer head exists after changes-requested review: **{p['changes_requested_followed_by_new_head']}**",
            f"- Approval applies to current head: **{p['approval_on_current_head']}**", "",
        ]
        if p.get("changes_requested_followed_by_new_head") and not p.get("approval_on_current_head"):
            lines += ["**Review interpretation:** a newer contributor head exists after the latest recorded `CHANGES_REQUESTED` review. The older review may no longer describe the current code, but re-approval/merge is not implied.", ""]

    lines += ["## Evidence timeline", "", "| Time (UTC) | Event | Evidence |", "| --- | --- | --- |"]
    for timestamp, event, evidence in _timeline(result):
        escaped_evidence = evidence.replace("|", "\\|")
        lines.append(f"| `{timestamp}` | {event} | {escaped_evidence} |")
    lines.append("")

    lines += ["## Candidate upstream changes", ""]
    if not result.candidates:
        lines += ["No candidate public commit met the minimum evidence threshold in the evaluated set.", ""]
    else:
        for c in result.candidates[:15]:
            lines += [
                f"### Score {c.score} / {c.channels} channels — `{c.sha[:8]}` — {c.message}", "",
                f"- Date: `{c.date}`", f"- Commit: {c.url}",
                f"- Discovered via: {', '.join(c.discovery) or 'n/a'}",
                f"- Reasons: {'; '.join(c.reasons)}",
                f"- Files: {', '.join(c.files[:12]) or 'n/a'}", "",
            ]

    lines += ["## Releases after baseline", ""]
    if not result.releases:
        lines += ["No GitHub release was found after the baseline in the fetched release window.", ""]
    else:
        for release in result.releases:
            label = release.get("name") or release.get("tag") or "release"
            lines.append(f"- [{label}]({release['url']}) — `{release['published_at']}`")
        lines.append("")

    lines += [
        "## Scan coverage", "",
        f"- Default-branch commits listed after baseline: **{result.listed_commits}**",
        f"- Candidate commit details evaluated: **{result.evaluated_candidates}**",
        f"- Exact-path history queries: **{result.path_queries}**",
        f"- GitHub API calls used: **{result.api_calls}**",
        f"- Candidate-detail cap reached: **{result.scan_truncated}**",
        f"- Last observed API rate-limit remaining: **{result.rate_remaining if result.rate_remaining is not None else 'unknown'}**", "",
        "## Interpretation and next action", "", result.next_action, "",
        "## Limits", "",
        "- The scan observes public GitHub data only; private branches, private remediation, off-GitHub work, and future changes are outside scope.",
        "- A related-looking patch does not prove who caused it or whether a bounty/program accepted a report.",
        "- `NO_PUBLIC_SIGNAL` means no sufficiently strong signal was found in the configured public scan window; it is not proof that nothing happened.",
        "- Very large GitHub commits may have API-truncated file/patch detail; manually inspect the linked commit when a decision is high-stakes.",
        "- If `Candidate-detail cap reached` is true, tighten tracked paths/anchors or rerun with a higher capped setting before relying on the result.", "",
    ]
    return "\n".join(lines)


def result_payload(result: ScanResult) -> dict[str, Any]:
    payload = asdict(result)
    payload.update({
        "schema_version": SCHEMA_VERSION,
        "engine_version": VERSION,
        "classification": result.classification,
        "confidence": result.confidence,
        "top_score": result.top_score,
        "top_channels": result.top_channels,
        "executive_finding": result.executive_finding,
        "next_action": result.next_action,
        "evidence_fingerprint": result.evidence_fingerprint,
    })
    return payload


def result_json(result: ScanResult) -> str:
    return json.dumps(result_payload(result), indent=2, sort_keys=True)


def write_result(result: ScanResult, *, markdown: Path | None = None, json_path: Path | None = None) -> None:
    if markdown is not None:
        markdown.parent.mkdir(parents=True, exist_ok=True)
        markdown.write_text(report(result) + "\n", encoding="utf-8")
    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(result_json(result) + "\n", encoding="utf-8")
