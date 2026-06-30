import sys

from researchos.db import SessionLocal
from researchos.ingest.models import Paper
from researchos.ingest.semantic_scholar import search_papers as s2_search
from researchos.ingest.pubmed import search_papers as pubmed_search
from researchos.ingest.arxiv import search_papers as arxiv_search


def parse_s2_paper(raw: dict) -> dict:
    external_ids = raw.get("externalIds") or {}
    publication_types = raw.get("publicationTypes") or []
    return {
        "source": "semantic_scholar",
        "external_id": raw.get("paperId") or external_ids.get("DOI") or raw.get("title", ""),
        "doi": external_ids.get("DOI"),
        "title": raw.get("title") or "Untitled",
        "abstract": raw.get("abstract"),
        "year": raw.get("year"),
        "venue": raw.get("venue"),
        "is_preprint": "Preprint" in publication_types if publication_types else False,
        "authors": [a.get("name") for a in (raw.get("authors") or [])],
        "raw_metadata": raw,
    }


def parse_pubmed_paper(raw: dict) -> dict:
    return {
        "source": "pubmed",
        "external_id": raw.get("pmid") or raw.get("title", ""),
        "doi": raw.get("doi"),
        "title": raw.get("title") or "Untitled",
        "abstract": raw.get("abstract"),
        "year": raw.get("year"),
        "venue": raw.get("venue"),
        "is_preprint": False,
        "authors": raw.get("authors") or [],
        "raw_metadata": raw,
    }


def parse_arxiv_paper(raw: dict) -> dict:
    return {
        "source": "arxiv",
        "external_id": raw.get("arxiv_id") or raw.get("title", ""),
        "doi": raw.get("doi"),
        "title": raw.get("title") or "Untitled",
        "abstract": raw.get("abstract"),
        "year": raw.get("year"),
        "venue": raw.get("venue"),
        "is_preprint": True,  # arXiv is a preprint server by definition
        "authors": raw.get("authors") or [],
        "raw_metadata": raw,
    }


def save_papers(session, papers: list[dict]):
    inserted = 0
    skipped = 0
    for fields in papers:
        exists = (
            session.query(Paper)
            .filter_by(source=fields["source"], external_id=fields["external_id"])
            .first()
        )
        if exists:
            skipped += 1
            continue
        paper = Paper(**fields)
        session.add(paper)
        inserted += 1
    session.commit()
    return inserted, skipped


def ingest(query: str, limit: int = 20):
    session = SessionLocal()
    total_inserted = 0
    total_skipped = 0

    sources = [
        ("Semantic Scholar", s2_search, parse_s2_paper),
        ("PubMed", pubmed_search, parse_pubmed_paper),
        ("arXiv", arxiv_search, parse_arxiv_paper),
    ]

    for name, search_fn, parse_fn in sources:
        print(f"\nFetching from {name}...")
        try:
            raw_papers = search_fn(query, limit=limit)
            parsed = [parse_fn(r) for r in raw_papers]
            inserted, skipped = save_papers(session, parsed)
            print(f"{name}: {inserted} inserted, {skipped} skipped")
            total_inserted += inserted
            total_skipped += skipped
        except Exception as e:
            print(f"{name}: FAILED — {e}")

    session.close()
    print(f"\nTotal inserted: {total_inserted}, Total skipped: {total_skipped}")


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "metformin cancer risk"
    ingest(query, limit=20)