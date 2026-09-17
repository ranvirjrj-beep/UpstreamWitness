# UpstreamWitness

**Know what changed upstream after you submitted a fix, bounty, security report, or open-source contribution.**

UpstreamWitness is an open-source CLI that turns public GitHub activity into a reproducible evidence report.

It answers one narrow question:

> After I submitted work, did the upstream repository later change in a materially related way?

This is useful when you are waiting on a maintainer, bounty program, security team, or project owner and want to separate **public evidence** from guesswork.

**UpstreamWitness reports correlation evidence. It does not prove attribution, bounty acceptance, legal entitlement, or payment entitlement.**

## Try it in 60 seconds

Python 3.11+ is required. The runtime has no third-party dependencies.

Install directly from GitHub:

```bash
python -m pip install "git+https://github.com/ranvirjrj-beep/UpstreamWitness.git"
upstreamwitness --version
```

Then trace any public GitHub PR:

```bash
upstreamwitness trace-pr https://github.com/owner/repo/pull/123 --out-dir my-trace
```

You get:

```text
my-trace/
  case.json      sanitized tracking configuration
  report.md      human-readable evidence report
  report.json    machine-readable evidence record
```

The report tells you whether the public record shows:

- the tracked PR merged upstream;
- strong or possible multi-channel overlap with later commits;
- releases after your baseline;
- relevant public review/merge chronology;
- no meaningful public signal in the scanned window;
- exactly which files, symbols, and textual anchors contributed to the result.

## Who this is for

Use UpstreamWitness if you are a:

- security researcher tracking public remediation after a private report;
- bounty worker waiting to see whether related code lands upstream;
- OSS contributor following what happened after a PR or proposed fix;
- maintainer who wants a reproducible public evidence pack instead of screenshots and memory.

## Want to test it on a real case?

**We are actively looking for early users.**

If you have a **public GitHub PR** or a sanitized public-repository case, open an issue using the **Public trace request** template. Do not include private vulnerability details, secrets, tokens, customer data, private PoCs, or confidential report text.

A useful early-user report is simple:

1. the public PR/repository URL;
2. a short sanitized concept if the PR title is too broad;
3. what result was useful, confusing, or missing.

Real cases will drive the next release.

## Quickest start: trace a public PR

```bash
upstreamwitness trace-pr https://github.com/owner/repo/pull/123 --out-dir my-trace
```

You can also run the package directly:

```bash
python -m upstreamwitness trace-pr https://github.com/owner/repo/pull/123 --out-dir my-trace
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

`0.1.0-rc.1` — release candidate. Early-user feedback is welcome.

## License

Apache License 2.0. See [LICENSE](LICENSE).
