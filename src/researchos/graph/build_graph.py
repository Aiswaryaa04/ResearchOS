from researchos.db import SessionLocal
from researchos.ingest.models import Paper
from researchos.graph.neo4j_client import get_driver


def build_paper_nodes():
    """Create a Neo4j node for every paper in Postgres."""
    session = SessionLocal()
    papers = session.query(Paper).filter(Paper.extraction_done == True).all()
    session.close()

    driver = get_driver()
    with driver.session() as neo4j:
        # clear existing nodes first so re-runs are safe
        neo4j.run("MATCH (p:Paper) DETACH DELETE p")

        for paper in papers:
            neo4j.run("""
                CREATE (p:Paper {
                    id: $id,
                    title: $title,
                    year: $year,
                    source: $source,
                    methodology: $methodology,
                    sample_size: $sample_size,
                    direction: $direction,
                    funding_type: $funding_type,
                    evidence_score: $evidence_score,
                    evidence_tier: $evidence_tier,
                    population: $population,
                    outcome: $outcome,
                    main_claim: $main_claim,
                    is_preprint: $is_preprint
                })
            """, {
                "id": paper.id,
                "title": paper.title,
                "year": paper.year or 0,
                "source": paper.source,
                "methodology": paper.methodology or "other",
                "sample_size": paper.sample_size or 0,
                "direction": paper.direction or "inconclusive",
                "funding_type": paper.funding_type or "unknown",
                "evidence_score": paper.evidence_score or 0.0,
                "evidence_tier": paper.evidence_tier or "Tier 7",
                "population": paper.population or "",
                "outcome": paper.outcome or "",
                "main_claim": paper.main_claim or "",
                "is_preprint": paper.is_preprint or False,
            })

        result = neo4j.run("MATCH (p:Paper) RETURN count(p) as count")
        count = result.single()["count"]
        print(f"Created {count} Paper nodes in Neo4j.")

    driver.close()


if __name__ == "__main__":
    build_paper_nodes()