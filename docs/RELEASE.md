# Release discipline

UpstreamWitness releases must preserve two things: technical reproducibility and the public/private boundary.

## Before creating a release

1. Work from `main` in this public repository only. Do not import Git history from an internal/private repository.
2. Confirm the release version is consistent in `pyproject.toml` and `upstreamwitness/version.py`.
3. Run the public CI matrix on Python 3.11, 3.12, and 3.13.
4. Require install, compile, deterministic tests, CLI smoke, and the live public-PR initializer smoke to pass.
5. Review the final diff for credentials, private disclosure text, personal data, local filesystem paths, or proprietary source material.
6. Confirm `LICENSE`, `SECURITY.md`, `docs/PRIVACY.md`, and the correlation-not-proof language remain intact.
7. For a release candidate, use a prerelease tag such as `v0.1.0-rc.1` and mark the GitHub Release as a pre-release.

## Release notes

Release notes should state what changed, what was tested, and any known limitations. Do not claim that UpstreamWitness can prove attribution, bounty acceptance, legal entitlement, or payment entitlement.

## After release

Verify the tag/release points at the intended `main` commit, CI is green on that commit, and the repository remains public while any internal/private working repositories remain separate.
