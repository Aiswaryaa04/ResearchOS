import time
from researchos.db import SessionLocal
from researchos.ingest.models import Paper
from researchos.extraction.extractor import extract_paper

VALID_METHODOLOGIES = {
    "meta_analysis", "rct", "cohort_study", "case_control",
    "cross_sectional", "case_study", "review", "other"
}
VALID_FUNDING_TYPES = {"industry", "public", "mixed", "none_declared", "unknown"}
VALID_DIRECTIONS = {"protective", "harmful", "neutral", "inconclusive"}


def validate_and_clean(extracted: dict) -> dict:
    """Ensure extracted values conform to our allowed sets."""
    if extracted.get("methodology") not in VALID_METHODOLOGIES:
        extracted["methodology"] = "other"
    if extracted.get("funding_type") not in VALID_FUNDING_TYPES:
        extracted["funding_type"] = "unknown"
    if extracted.get("direction") not in VALID_DIRECTIONS:
        extracted["direction"] = "inconclusive"

    # sample_size must be a positive integer or None
    size = extracted.get("sample_size")
    if size is not None:
        try:
            extracted["sample_size"] = int(size)
            if extracted["sample_size"] <= 0:
                extracted["sample_size"] = None
        except (ValueError, TypeError):
            extracted["sample_size"] = None

    return extracted


def run_extraction():
    session = SessionLocal()

    papers = (
        session.query(Paper)
        .filter(Paper.extraction_done == False)
        .filter(Paper.abstract != None)
        .all()
    )
    print(f"Found {len(papers)} papers to extract.")

    done = 0
    failed = 0

    for paper in papers:
        print(f"  Extracting: {paper.title[:70]}...")

        extracted = extract_paper(paper.title, paper.abstract)

        if not extracted:
            print(f"  FAILED — skipping")
            failed += 1
            continue

        extracted = validate_and_clean(extracted)

        paper.main_claim = extracted.get("main_claim")
        paper.methodology = extracted.get("methodology")
        paper.sample_size = extracted.get("sample_size")
        paper.population = extracted.get("population")
        paper.funding_source = extracted.get("funding_source")
        paper.funding_type = extracted.get("funding_type")
        paper.direction = extracted.get("direction")
        paper.outcome = extracted.get("outcome")
        paper.extraction_done = True

        session.commit()
        done += 1

        # be polite to the API — 1 request per second
        time.sleep(1)

    session.close()
    print(f"\nDone. Extracted: {done}, Failed: {failed}")


if __name__ == "__main__":
    run_extraction()