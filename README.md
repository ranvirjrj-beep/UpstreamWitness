# UpstreamWitness

UpstreamWitness is a public-code evidence tracker for security researchers, bounty workers, and open-source contributors.

It answers one narrow question:

> After I submitted work, did the upstream repository later change in a materially related way?

UpstreamWitness scans public GitHub activity after a user-defined baseline and ranks candidate commits using independent evidence channels: specific file paths, patch symbols, and textual anchors/keywords. It also records public PR merge/review state, releases, scan coverage, and a deterministic evidence fingerprint.

**UpstreamWitness reports correlation evidence. It does not prove attribution, bounty acceptance, legal entitlement, or payment entitlement.**

## Install from source

Python 3.11+ is required. The runtime has no third-party dependencies.

```bash
python -m pip install -e .
upstreamwitness --version
```

For development/tests:

```bash
python -m pip install -e ".[dev]"
```

## Quickest start: trace a public PR

```bash
upstreamwitness trace-pr https://github.com/owner/repo/pull/123 --out-dir my-trace
```

You can also run the package directly:

```bash
python -m upstreamwitness trace-pr https://github.com/owner/repo/pull/123 --out-dir my-trace
```

Output:

```text
my-trace/
  case.json      sanitized tracking configuration
  report.md      human-readable evidence report
  report.json    machine-readable evidence record
```

The public-PR initializer deliberately copies only public PR metadata, title-derived terms, and changed filenames. It does **not** copy PR body text into the case file.

For a title that is too broad, add a short sanitized concept:

```bash
upstreamwitness trace-pr https://github.com/owner/repo/pull/123 \
  --keyword session-lifecycle \
  --out-dir my-trace
```

Sensitive-looking email addresses, tokens, JWTs, and private-key text are rejected as extra keywords.

## Trace a manual/sanitized case

```bash
upstreamwitness scan \
  --config examples/case.template.json \
  --out report.md \
  --json-out report.json
```

A case can omit `pr_number` and use only a public repository, baseline timestamp, and sanitized fingerprints. This is useful when the original report is private but the upstream repository is public.

## Evidence labels

- `UPSTREAM_CONFIRMED` — the tracked public PR is recorded by GitHub as merged upstream.
- `STRONG_SIGNAL` — strong public overlap across at least two independent evidence channels; manual verification is still required.
- `POSSIBLE_SIGNAL` — meaningful multi-channel overlap that needs manual review.
- `NO_PUBLIC_SIGNAL` — no sufficiently strong signal was found in the configured public scan window.

Textual anchors and keyword overlap count as **one** evidence channel, so repeated wording cannot manufacture independence. Generic files such as `README.md`, changelogs, and lockfiles are deliberately weak path evidence.

## What the report contains

Each Markdown/JSON evidence pack includes:

- baseline and observation time;
- classification and confidence;
- deterministic case and evidence fingerprints;
- public PR merge/review state when applicable;
- review-follow-up logic for a newer head after `CHANGES_REQUESTED`;
- ranked candidate commits and why they matched;
- releases after the baseline;
- API/scan coverage and truncation disclosure;
- interpretation, next action, and explicit limitations.

The fingerprint is a reproducibility aid for the public evidence snapshot. It is **not** a timestamping/notarization service and is not legal proof.

## API limits and privacy

UpstreamWitness public mode refuses private repositories. It never writes `GITHUB_TOKEN` to outputs. Without a token, GitHub's anonymous API limit is small; set a token in your process environment for higher limits:

```bash
export GITHUB_TOKEN=your_token_here
```

Never commit tokens to a config. For private security reports, keep the report and PoC outside UpstreamWitness and provide only sanitized paths/symbols/keywords needed to compare against a **public** upstream repository.

See [docs/PRIVACY.md](docs/PRIVACY.md).

## Demo corpus

The repository ships three public examples:

- Stellar portfolio rebalancer PR #1648 — merged positive control.
- Memanto public security bounty PR #1960 — open/unmerged control.
- Chain.Love PR #3829 — newer contributor fix after a changes-requested review, open/unmerged at the captured baseline.

Run all demos:

```bash
upstreamwitness scan-all --configs demos --out-dir reports
```

Batch mode preserves successful reports even when one case fails and writes `summary.json`.

## Verify locally

```bash
python -m pip install -e ".[dev]"
python -m compileall -q upstreamwitness tests
pytest
```

CI runs the same test suite on Python 3.11, 3.12, and 3.13.

## Project status

`0.1.0-rc.1` — release candidate.

## License

Apache License 2.0. See [LICENSE](LICENSE).
