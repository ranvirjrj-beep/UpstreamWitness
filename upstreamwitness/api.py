from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .version import VERSION

API = "https://api.github.com"


class GitHubAPI:
    """Small GitHub REST client with request-count and rate-limit metadata."""

    def __init__(self, token: str | None = None):
        self.token = token if token is not None else os.environ.get("GITHUB_TOKEN")
        self.calls = 0
        self.rate_remaining: int | None = None
        self.rate_reset: int | None = None

    def get(self, path: str) -> Any:
        self.calls += 1
        req = urllib.request.Request(API + path)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", f"UpstreamWitness/{VERSION}")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                remaining = resp.headers.get("X-RateLimit-Remaining")
                reset = resp.headers.get("X-RateLimit-Reset")
                self.rate_remaining = int(remaining) if remaining and remaining.isdigit() else None
                self.rate_reset = int(reset) if reset and reset.isdigit() else None
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
            reset = exc.headers.get("X-RateLimit-Reset") if exc.headers else None
            self.rate_remaining = int(remaining) if remaining and remaining.isdigit() else self.rate_remaining
            self.rate_reset = int(reset) if reset and reset.isdigit() else self.rate_reset
            body = exc.read().decode("utf-8", errors="replace")
            hint = ""
            if exc.code in {403, 429}:
                hint = " GitHub API rate limit may be exhausted; set GITHUB_TOKEN for a higher limit."
            raise RuntimeError(f"GitHub API {exc.code}: {body[:500]}.{hint}") from exc
