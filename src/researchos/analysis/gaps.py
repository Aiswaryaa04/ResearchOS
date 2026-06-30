from collections import Counter
from researchos.db import SessionLocal
from researchos.ingest.models import Paper


# subpopulations we want to check coverage for
SUBPOPULATIONS = [
    "elderly", "older adults", "over 75", "pediatric", "children",
    "pregnant", "pregnancy", "male", "female", "women", "men",
    "asian", "black", "hispanic", "african american",
    "obese", "obesity", "renal", "kidney", "liver",
    "type 1 diabetes", "type 2 diabetes",
]

# co-interventions / combinations we want to check
CO_INTERVENTIONS = [
    "insulin", "statin", "aspirin", "chemotherapy",
    "radiotherapy", "immunotherapy", "surgery",
]


def detect_gaps() -> dict:
    """
    Scan all extracted papers and surface research gaps:
    - Subpopulations with no or few studies
    - Co-interventions that haven't been studied
    - Outcomes with only one study (unreplicated)
    - Years with no publications (temporal gaps)
    """
    session = SessionLocal()
    papers = session.query(Paper).filter(Paper.extraction_done == True).all()
    session.close()

    all_text = " ".join([
        ((p.population or "") + " " + (p.abstract or "") + " " + (p.title or "")).lower()
        for p in papers
    ])

    # 1. subpopulation coverage
    subpop_coverage = {}
    for subpop in SUBPOPULATIONS:
        count = all_text.count(subpop.lower())
        subpop_coverage[subpop] = count

    unstudied_subpops = [s for s, c in subpop_coverage.items() if c == 0]
    understudied_subpops = [s for s, c in subpop_coverage.items() if 0 < c <= 2]

    # 2. co-intervention coverage
    co_coverage = {}
    for co in CO_INTERVENTIONS:
        count = all_text.count(co.lower())
        co_coverage[co] = count

    unstudied_combos = [c for c, n in co_coverage.items() if n == 0]

    # 3. unreplicated outcomes
    outcome_counts = Counter(
        p.outcome.lower().strip()
        for p in papers
        if p.outcome
    )
    unreplicated = [
        outcome for outcome, count in outcome_counts.items()
        if count == 1
    ]

    # 4. temporal gaps
    years_with_papers = set(p.year for p in papers if p.year)
    if years_with_papers:
        all_years = set(range(min(years_with_papers), max(years_with_papers) + 1))
        missing_years = sorted(all_years - years_with_papers)
    else:
        missing_years = []

    return {
        "total_papers": len(papers),
        "unstudied_subpopulations": unstudied_subpops,
        "understudied_subpopulations": understudied_subpops,
        "unstudied_co_interventions": unstudied_combos,
        "unreplicated_outcomes": unreplicated[:10],  # top 10
        "temporal_gaps": missing_years,
        "subpop_coverage": subpop_coverage,
        "co_coverage": co_coverage,
    }


if __name__ == "__main__":
    gaps = detect_gaps()

    print(f"\nResearch Gap Report ({gaps['total_papers']} papers analyzed)\n")

    print("UNSTUDIED SUBPOPULATIONS (0 papers):")
    for s in gaps["unstudied_subpopulations"]:
        print(f"  • {s}")

    print("\nUNDERSTUDIED SUBPOPULATIONS (1-2 papers):")
    for s in gaps["understudied_subpopulations"]:
        print(f"  • {s} ({gaps['subpop_coverage'][s]} paper(s))")

    print("\nUNSTUDIED CO-INTERVENTIONS:")
    for c in gaps["unstudied_co_interventions"]:
        print(f"  • {c}")

    print("\nUNREPLICATED OUTCOMES (only 1 study):")
    for o in gaps["unreplicated_outcomes"]:
        print(f"  • {o}")

    if gaps["temporal_gaps"]:
        print(f"\nTEMPORAL GAPS (years with no papers): {gaps['temporal_gaps']}")