from dataclasses import dataclass
from urllib.parse import urlparse

import requests


class SearchError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SearchHit:
    query: str
    rank: int
    title: str
    url: str
    snippet: str
    engine: str
    score: float


class SearXNGProvider:
    def __init__(
        self,
        base_url,
        user_agent,
        timeout=15,
        results_per_query=5,
        engines="yep",
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.user_agent = user_agent
        self.timeout = timeout
        self.results_per_query = results_per_query
        self.engines = (engines or "").strip()

    def search(self, query):
        if not self.base_url:
            raise SearchError("search_not_configured")
        params = {
            "q": query,
            "format": "json",
            "language": "en",
            "safesearch": 1,
            "categories": "general",
        }
        if self.engines:
            params["engines"] = self.engines
        try:
            response = requests.get(
                "{0}/search".format(self.base_url),
                params=params,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/json",
                },
                timeout=self.timeout,
            )
        except requests.Timeout:
            raise SearchError("search_timeout")
        except requests.RequestException:
            raise SearchError("search_unreachable")

        if response.status_code != 200:
            raise SearchError("search_http_{0}".format(response.status_code))
        try:
            payload = response.json()
        except ValueError:
            raise SearchError("search_invalid_json")
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            raise SearchError("search_invalid_payload")

        hits = []
        for rank, item in enumerate(results[: self.results_per_query], start=1):
            if not isinstance(item, dict):
                continue
            url = (item.get("url") or "").strip()
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                continue
            title = (item.get("title") or "").strip()
            snippet = (item.get("content") or "").strip()
            try:
                score = float(item.get("score") or 0)
            except (TypeError, ValueError):
                score = 0.0
            hits.append(
                SearchHit(
                    query=query,
                    rank=rank,
                    title=title[:512],
                    url=url[:1024],
                    snippet=snippet[:2000],
                    engine=(item.get("engine") or "")[:64],
                    score=score,
                )
            )
        return hits
