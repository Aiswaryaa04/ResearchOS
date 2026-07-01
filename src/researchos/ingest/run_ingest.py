import sys
import time

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
        "is_preprint": True,
        "authors": raw.get("authors") or [],
        "raw_metadata": raw,
    }

def save_papers(session, papers: list[dict]):
    inserted = 0
    skipped = 0
    for fields in papers:
        # skip papers with no abstract and no title — nothing to work with
        if not fields.get("abstract") and not fields.get("title"):
            skipped += 1
            continue
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

def expand_queries(query: str) -> list[str]:
    words = query.strip().split()
    queries = [query]

    if len(words) >= 3:
        queries.append(" ".join(words[:2]))
        queries.append(" ".join(words[1:]))

    base = words[0] if words else query
    queries.extend([
        f"{base} clinical trial",
        f"{base} meta-analysis",
        f"{base} systematic review",
        f"{base} cohort study",
        f"{base} randomized controlled trial",
    ])

    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)

    return unique


def ingest(query: str, limit: int = 20, scale: bool = False):
    session = SessionLocal()
    total_inserted = 0
    total_skipped = 0

    queries = expand_queries(query) if scale else [query]
    per_query_limit = 100 if scale else limit

    sources = [
        ("Semantic Scholar", s2_search, parse_s2_paper),
        ("PubMed", pubmed_search, parse_pubmed_paper),
        ("arXiv", arxiv_search, parse_arxiv_paper),
    ]

    for q in queries:
        print(f"\nQuery: '{q}'")
        for name, search_fn, parse_fn in sources:
            # arXiv needs longer gaps to avoid rate limiting
            if name == "arXiv" and scale:
                time.sleep(20)
            try:
                raw_papers = search_fn(q, limit=per_query_limit)
                parsed = [parse_fn(r) for r in raw_papers]
                inserted, skipped = save_papers(session, parsed)
                print(f"  {name}: {inserted} inserted, {skipped} skipped")
                total_inserted += inserted
                total_skipped += skipped
                time.sleep(1)
            except Exception as e:
                print(f"  {name}: FAILED — {e}")
                continue

    session.close()
    print(f"\nTotal inserted: {total_inserted}, Total skipped: {total_skipped}")

    session = SessionLocal()
    total = session.query(Paper).count()
    session.close()
    print(f"Total papers in database: {total}")


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "metformin cancer risk"
    scale = "--scale" in sys.argv
    ingest(query, scale=scale)