import os
import time
import requests

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,abstract,year,venue,externalIds,authors,publicationTypes"


def search_papers(query: str, limit: int = 20, max_retries: int = 5) -> list[dict]:
    headers = {}
    api_key = _get_env("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    params = {
        "query": query,
        "limit": limit,
        "fields": FIELDS,
    }

    wait = 10
    for attempt in range(max_retries):
        response = requests.get(BASE_URL, headers=headers, params=params)

        if response.status_code == 429:
            print(f"Rate limited (attempt {attempt + 1}/{max_retries}), waiting {wait}s...")
            time.sleep(wait)
            wait *= 2  # 10s, 20s, 40s, 80s, 160s
            continue

        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    raise RuntimeError("Semantic Scholar API: exceeded max retries due to rate limiting")


if __name__ == "__main__":
    results = search_papers("metformin cancer risk", limit=5)
    print(f"Got {len(results)} papers")
    for paper in results:
        print("-", paper.get("title"), "(", paper.get("year"), ")")

def _get_env(key: str) -> str:
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, "")