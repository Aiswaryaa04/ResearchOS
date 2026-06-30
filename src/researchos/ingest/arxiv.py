import time
import requests
import xml.etree.ElementTree as ET

ARXIV_URL = "http://export.arxiv.org/api/query"

# XML namespace used throughout arXiv's Atom feed
ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def search_papers(query: str, limit: int = 20) -> list[dict]:
    """Search arXiv and return parsed paper dicts."""
    # arXiv title search: space-separated terms, no AND keyword needed
    words = query.strip().split()
    search_query = " ".join(f"ti:{w}" for w in words)

    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": limit,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    response = requests.get(ARXIV_URL, params=params)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    papers = []

    for entry in root.findall(f"{ATOM}entry"):
        parsed = _parse_entry(entry)
        if parsed:
            papers.append(parsed)

    return papers

def _parse_entry(entry) -> dict | None:
    """Parse a single arXiv Atom entry into our standard dict shape."""

    def find_text(tag):
        el = entry.find(f"{ATOM}{tag}")
        return el.text.strip() if el is not None and el.text else None

    title = find_text("title")
    if not title:
        return None

    # arXiv ID lives in the <id> tag as a URL, e.g.
    # http://arxiv.org/abs/2301.12345v1 — we extract just the ID part
    raw_id = find_text("id") or ""
    arxiv_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id

    abstract = find_text("summary")

    # published date looks like "2023-01-30T00:00:00Z"
    published = find_text("published") or ""
    year = int(published[:4]) if len(published) >= 4 else None

    # authors
    authors = [
        (a.find(f"{ATOM}name").text or "").strip()
        for a in entry.findall(f"{ATOM}author")
        if a.find(f"{ATOM}name") is not None
    ]

    # DOI — arXiv sometimes includes one if the paper was also published
    doi = None
    doi_el = entry.find(f"{ARXIV_NS}doi")
    if doi_el is not None and doi_el.text:
        doi = doi_el.text.strip()

    # journal ref — if the paper was published somewhere, arXiv lists it
    venue = None
    venue_el = entry.find(f"{ARXIV_NS}journal_ref")
    if venue_el is not None and venue_el.text:
        venue = venue_el.text.strip()

    return {
        "arxiv_id": arxiv_id,
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "year": year,
        "venue": venue,
        "authors": authors,
    }


if __name__ == "__main__":
    results = search_papers("metformin cancer risk", limit=5)
    print(f"Got {len(results)} papers")
    for paper in results:
        print("-", paper.get("title"), "(", paper.get("year"), ")")