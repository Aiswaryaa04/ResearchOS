import os
import time
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def _get_params(extra: dict) -> dict:
    """Base params included in every NCBI request."""
    params = {
        "api_key": os.environ.get("NCBI_API_KEY", ""),
        "tool": "researchos",
        "email": "avelu3@uic.edu",
    }
    params.update(extra)
    return params


def _search_pmids(query: str, limit: int) -> list[str]:
    """Step 1: get a list of PMIDs matching the query."""
    params = _get_params({
        "db": "pubmed",
        "term": query,
        "retmax": limit,
        "retmode": "json",
    })
    response = requests.get(ESEARCH_URL, params=params)
    response.raise_for_status()
    data = response.json()
    return data["esearchresult"]["idlist"]


def _fetch_papers(pmids: list[str]) -> list[dict]:
    """Step 2: fetch full metadata for a list of PMIDs, parse XML into dicts."""
    params = _get_params({
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    })
    response = requests.get(EFETCH_URL, params=params)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    papers = []

    for article in root.findall(".//PubmedArticle"):
        papers.append(_parse_article(article))

    return papers


def _parse_article(article) -> dict:
    """Extract fields we care about from a PubmedArticle XML element."""

    def find_text(path):
        el = article.find(path)
        return el.text.strip() if el is not None and el.text else None

    # title
    title = find_text(".//ArticleTitle")

    # abstract (may have multiple sections)
    abstract_parts = article.findall(".//AbstractText")
    abstract = " ".join(
        (p.text or "") for p in abstract_parts if p.text
    ).strip() or None

    # year
    year_el = article.find(".//PubDate/Year")
    year = int(year_el.text) if year_el is not None and year_el.text else None

    # journal/venue
    venue = find_text(".//Journal/Title")

    # DOI
    doi = None
    for id_el in article.findall(".//ArticleId"):
        if id_el.get("IdType") == "doi":
            doi = id_el.text
            break

    # PMID
    pmid = find_text(".//PMID")

    # authors
    authors = []
    for author in article.findall(".//Author"):
        last = find_text(".//LastName") 
        fore = find_text(".//ForeName")
        if last:
            authors.append(f"{fore} {last}".strip() if fore else last)

    # publication types
    pub_types = [
        pt.text for pt in article.findall(".//PublicationType") if pt.text
    ]

    return {
        "pmid": pmid,
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "year": year,
        "venue": venue,
        "authors": authors,
        "publication_types": pub_types,
    }


def search_papers(query: str, limit: int = 20) -> list[dict]:
    """Search PubMed and return parsed paper dicts."""
    pmids = _search_pmids(query, limit)
    if not pmids:
        return []
    time.sleep(0.5)  # be polite between esearch and efetch
    return _fetch_papers(pmids)


if __name__ == "__main__":
    results = search_papers("metformin cancer risk", limit=5)
    print(f"Got {len(results)} papers")
    for paper in results:
        print("-", paper.get("title"), "(", paper.get("year"), ")")