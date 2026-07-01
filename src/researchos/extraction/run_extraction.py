import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    if extracted.get("methodology") not in VALID_METHODOLOGIES:
        extracted["methodology"] = "other"
    if extracted.get("funding_type") not in VALID_FUNDING_TYPES:
        extracted["funding_type"] = "unknown"
    if extracted.get("direction") not in VALID_DIRECTIONS:
        extracted["direction"] = "inconclusive"
    size = extracted.get("sample_size")
    if size is not None:
        try:
            extracted["sample_size"] = int(size)
            if extracted["sample_size"] <= 0:
                extracted["sample_size"] = None
        except (ValueError, TypeError):
            extracted["sample_size"] = None
    return extracted


def process_paper(paper_id: str, title: str, abstract: str) -> tuple[str, dict | None]:
    """Extract a single paper — runs in a thread."""
    extracted = extract_paper(title, abstract)
    if extracted:
        extracted = validate_and_clean(extracted)
    return paper_id, extracted


def run_extraction(max_workers: int = 5):
    """
    Extract structured data from paper abstracts using parallel Claude API calls.
    max_workers=5 means 5 papers processed simultaneously.
    Claude's API handles concurrent requests fine at this volume.
    """
    session = SessionLocal()
    papers = (
        session.query(Paper)
        .filter(Paper.extraction_done == False)
        .filter(Paper.abstract != None)
        .all()
    )
    # load what we need and close session — threads will open their own
    paper_data = [(p.id, p.title, p.abstract) for p in papers]
    session.close()

    total = len(paper_data)
    print(f"Found {total} papers to extract.")

    if total == 0:
        return

    done = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process_paper, pid, title, abstract): pid
            for pid, title, abstract in paper_data
        }

        for future in as_completed(futures):
            paper_id, extracted = future.result()

            if not extracted:
                failed += 1
                done += 1
                if done % 50 == 0:
                    print(f"  Progress: {done}/{total} (failed: {failed})")
                continue

            # each thread gets its own session to avoid conflicts
            s = SessionLocal()
            paper = s.query(Paper).filter(Paper.id == paper_id).first()
            if paper:
                paper.main_claim = extracted.get("main_claim")
                paper.methodology = extracted.get("methodology")
                paper.sample_size = extracted.get("sample_size")
                paper.population = extracted.get("population")
                paper.funding_source = extracted.get("funding_source")
                paper.funding_type = extracted.get("funding_type")
                paper.direction = extracted.get("direction")
                paper.outcome = extracted.get("outcome")
                paper.extraction_done = True
                s.commit()
            s.close()

            done += 1
            if done % 50 == 0:
                print(f"  Progress: {done}/{total} (failed: {failed})")

    print(f"\nDone. Extracted: {done - failed}, Failed: {failed}")


if __name__ == "__main__":
    run_extraction(max_workers=5)