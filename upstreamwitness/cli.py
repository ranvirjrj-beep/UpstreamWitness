from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pr import build_case, trace_public_pr, write_case
from .reporting import report, write_result
from .scanner import scan
from .version import VERSION


def main() -> int:
    parser = argparse.ArgumentParser(prog="upstreamwitness")
    parser.add_argument("--version", action="version", version=f"UpstreamWitness {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan_p = sub.add_parser("scan", help="scan one case config")
    scan_p.add_argument("--config", required=True)
    scan_p.add_argument("--out")
    scan_p.add_argument("--json-out")

    all_p = sub.add_parser("scan-all", help="scan every JSON config in a directory")
    all_p.add_argument("--configs", required=True)
    all_p.add_argument("--out-dir", required=True)

    init_p = sub.add_parser("init-pr", help="create a sanitized case from a public GitHub PR")
    init_p.add_argument("pr_url")
    init_p.add_argument("--out", required=True)
    init_p.add_argument("--keyword", action="append", default=[])

    trace_p = sub.add_parser("trace-pr", help="create a sanitized case and scan it in one command")
    trace_p.add_argument("pr_url")
    trace_p.add_argument("--out-dir", default="upstreamwitness-report")
    trace_p.add_argument("--keyword", action="append", default=[])

    args = parser.parse_args()

    if args.command == "scan":
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        result = scan(config)
        if args.out or args.json_out:
            write_result(result, markdown=Path(args.out) if args.out else None, json_path=Path(args.json_out) if args.json_out else None)
        else:
            print(report(result))
        return 0

    if args.command == "init-pr":
        case = build_case(args.pr_url, extra_keywords=args.keyword)
        write_case(case, Path(args.out))
        print(f"Wrote sanitized case config: {args.out}")
        return 0

    if args.command == "trace-pr":
        result = trace_public_pr(args.pr_url, Path(args.out_dir), extra_keywords=args.keyword)
        print(f"{result.classification} ({result.confidence}) — fingerprint {result.evidence_fingerprint[:12]} — evidence written to {args.out_dir}")
        return 0

    configs = sorted(Path(args.configs).glob("*.json"))
    if not configs:
        raise SystemExit("No JSON configs found")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    failures = 0
    for config_path in configs:
        try:
            result = scan(json.loads(config_path.read_text(encoding="utf-8")))
            write_result(result, markdown=out_dir / f"{config_path.stem}.md", json_path=out_dir / f"{config_path.stem}.json")
            summary.append({"case": config_path.name, "classification": result.classification, "confidence": result.confidence, "fingerprint": result.evidence_fingerprint})
            print(f"{config_path.name}: {result.classification} ({result.confidence})")
        except Exception as exc:
            failures += 1
            error = {"case": config_path.name, "error": str(exc)}
            summary.append(error)
            (out_dir / f"{config_path.stem}.error.json").write_text(json.dumps(error, indent=2) + "\n", encoding="utf-8")
            print(f"{config_path.name}: ERROR: {exc}")
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 1 if failures else 0
