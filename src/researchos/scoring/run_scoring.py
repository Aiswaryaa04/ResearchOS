from researchos.db import SessionLocal
from researchos.ingest.models import Paper
from researchos.scoring.scorer import compute_score


def run_scoring():
    session = SessionLocal()

    papers = (
        session.query(Paper)
        .filter(Paper.extraction_done == True)
        .filter(Paper.scoring_done == False)
        .all()
    )
    print(f"Found {len(papers)} papers to score.")

    for paper in papers:
        score, tier = compute_score(
            methodology=paper.methodology,
            sample_size=paper.sample_size,
            funding_type=paper.funding_type,
            is_preprint=paper.is_preprint or False,
        )
        paper.evidence_score = score
        paper.evidence_tier = tier
        paper.scoring_done = True

    session.commit()
    session.close()
    print("Scoring complete.")


if __name__ == "__main__":
    run_scoring()