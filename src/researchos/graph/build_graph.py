import os
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


def build_citation_edges():
    """
    Build CITES edges in Neo4j using Semantic Scholar citation data.
    Only papers from Semantic Scholar have citation data available.
    """
    import requests
    import time

    session = SessionLocal()
    papers = (
        session.query(Paper)
        .filter(Paper.source == "semantic_scholar")
        .filter(Paper.external_id != None)
        .all()
    )
    paper_ids = [(p.id, p.external_id) for p in papers]
    session.close()

    print(f"Fetching citations for {len(paper_ids)} Semantic Scholar papers...")

    driver = get_driver()
    edges_created = 0
    skipped = 0

    with driver.session() as neo4j:
        for internal_id, s2_id in paper_ids:
            try:
                url = f"https://api.semanticscholar.org/graph/v1/paper/{s2_id}/references"
                headers = {}
                api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
                if api_key:
                    headers["x-api-key"] = api_key

                response = requests.get(
                    url,
                    headers=headers,
                    params={"fields": "paperId", "limit": 50},
                    timeout=10,
                )

                if response.status_code == 429:
                    print(f"  Rate limited, waiting 10s...")
                    time.sleep(10)
                    continue

                if response.status_code != 200:
                    skipped += 1
                    continue

                data = response.json()
                references = data.get("data", [])

                for ref in references:
                    cited_paper = ref.get("citedPaper", {})
                    cited_s2_id = cited_paper.get("paperId")
                    if not cited_s2_id:
                        continue

                    # only create edge if cited paper is also in our graph
                    result = neo4j.run(
                        "MATCH (b:Paper {external_id: $cited_id}) RETURN b.id LIMIT 1",
                        {"cited_id": cited_s2_id}
                    ).single()

                    if result:
                        neo4j.run("""
                            MATCH (a:Paper {id: $id_a}), (b:Paper {id: $id_b})
                            MERGE (a)-[:CITES]->(b)
                        """, {
                            "id_a": internal_id,
                            "id_b": result["b.id"],
                        })
                        edges_created += 1

                time.sleep(1)  # 1 req/sec with API key

            except Exception as e:
                print(f"  Error for {s2_id}: {e}")
                skipped += 1
                continue

    driver.close()
    print(f"Created {edges_created} CITES edges, skipped {skipped} papers.")


if __name__ == "__main__":
    build_paper_nodes()
    build_citation_edges()
    print("Graph build complete.")