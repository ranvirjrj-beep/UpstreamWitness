# Contributing

Contributions are welcome.

Before opening a PR:

1. keep runtime dependencies in the Python standard library unless there is a compelling reason to change that policy;
2. add or update deterministic tests for scoring/review logic;
3. do not add private disclosures, credentials, personal data, or non-public case material;
4. preserve the distinction between correlation and attribution/acceptance/payment;
5. run:

```bash
python -m compileall -q upstreamwitness tests
pytest
```

Changes that increase recall must include false-positive tests. A single wording match must never become a strong verdict by itself.
