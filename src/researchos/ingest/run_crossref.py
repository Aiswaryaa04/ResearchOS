import time
from researchos.db import SessionLocal
from researchos.ingest.models import Paper
from researchos.ingest.crossref import get_crossref_metadata


def enrich_with_crossref():
    session = SessionLocal()

    papers = (
        session.query(Paper)
        .filter(Paper.doi != None)
        .filter(Paper.doi != "")
        .all()
    )

    print(f"Found {len(papers)} papers with DOIs to enrich.")
    enriched = 0
    skipped = 0

    for paper in papers:
        metadata = get_crossref_metadata(paper.doi)

        if not metadata:
            skipped += 1
            continue

        # only update funding if CrossRef has better info than what we extracted
        if metadata["funder_names"] and paper.funding_type in ("unknown", "none_declared"):
            paper.funding_source = ", ".join(metadata["funder_names"][:3])
            paper.funding_type = metadata["funding_type"]

        session.commit()
        enriched += 1

        # CrossRef asks for polite rate limiting
        time.sleep(0.2)

    session.close()
    print(f"Enriched: {enriched}, Skipped (no DOI data): {skipped}")


if __name__ == "__main__":
    enrich_with_crossref()