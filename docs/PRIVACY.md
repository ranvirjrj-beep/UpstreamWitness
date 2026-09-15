# Privacy model

UpstreamWitness is designed to work from **sanitized metadata plus public GitHub activity**.

## Do not put these in case files

- confidential report bodies or private PoCs;
- credentials, API keys, cookies, bearer tokens, or private keys;
- customer/user data;
- private repository URLs or proprietary source excerpts;
- personal contact details that are not already intended for publication.

For a private vulnerability report against a public project, keep the report outside the tool. A minimal case normally needs only the public upstream repository, report/submission timestamp, relevant public file paths or symbol names, and short sanitized concepts.

## Public-PR helper

`python -m upstreamwitness init-pr` and `python -m upstreamwitness trace-pr` use public PR metadata and changed filenames. They intentionally do not copy the PR body into the generated case configuration.

## Repository boundary

The release candidate is public-repository-only. UpstreamWitness checks repository metadata and refuses a private repository rather than silently processing it.

## Generated reports

Reports can include public commit titles, filenames, PR/release links, and public timestamps. Treat reports as local files unless you intentionally choose to share them.
