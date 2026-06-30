from collections import defaultdict
from researchos.db import SessionLocal
from researchos.ingest.models import Paper


def build_consensus_timeline(outcome_keyword: str = None) -> list[dict]:
    """
    For each year in the corpus, compute the weighted consensus direction.
    Returns a list of yearly snapshots sorted by year.
    """
    session = SessionLocal()
    query = session.query(Paper).filter(
        Paper.extraction_done == True,
        Paper.direction != None,
        Paper.year != None,
        Paper.evidence_score != None,
    )
    papers = query.all()
    session.close()

    if outcome_keyword:
        keyword = outcome_keyword.lower()
        papers = [
            p for p in papers
            if keyword in (p.outcome or "").lower()
            or keyword in (p.title or "").lower()
        ]

    # group papers by year
    by_year = defaultdict(list)
    for paper in papers:
        by_year[paper.year].append(paper)

    timeline = []
    running_protective = 0.0
    running_harmful = 0.0
    running_inconclusive = 0.0

    for year in sorted(by_year.keys()):
        year_papers = by_year[year]

        # weight each paper's direction vote by its evidence score
        protective_weight = sum(
            p.evidence_score for p in year_papers
            if p.direction == "protective"
        )
        harmful_weight = sum(
            p.evidence_score for p in year_papers
            if p.direction == "harmful"
        )
        inconclusive_weight = sum(
            p.evidence_score for p in year_papers
            if p.direction in ("inconclusive", "neutral")
        )

        running_protective += protective_weight
        running_harmful += harmful_weight
        running_inconclusive += inconclusive_weight

        total = running_protective + running_harmful + running_inconclusive
        if total == 0:
            continue

        # cumulative consensus up to this year
        consensus = "inconclusive"
        confidence = 0.0

        if running_protective > running_harmful and running_protective > running_inconclusive:
            consensus = "protective"
            confidence = round(running_protective / total, 3)
        elif running_harmful > running_protective and running_harmful > running_inconclusive:
            consensus = "harmful"
            confidence = round(running_harmful / total, 3)
        else:
            consensus = "inconclusive"
            confidence = round(running_inconclusive / total, 3)

        timeline.append({
            "year": year,
            "consensus": consensus,
            "confidence": confidence,
            "papers_this_year": len(year_papers),
            "protective_weight": round(protective_weight, 2),
            "harmful_weight": round(harmful_weight, 2),
            "inconclusive_weight": round(inconclusive_weight, 2),
            "paper_titles": [p.title for p in year_papers],
        })

    return timeline


if __name__ == "__main__":
    timeline = build_consensus_timeline()
    print(f"\nConsensus Timeline ({len(timeline)} years)\n")
    print(f"{'Year':<6} {'Consensus':<15} {'Confidence':>10} {'Papers':>7}")
    print("-" * 45)
    for entry in timeline:
        print(
            f"{entry['year']:<6} "
            f"{entry['consensus']:<15} "
            f"{entry['confidence']:>10} "
            f"{entry['papers_this_year']:>7}"
        )