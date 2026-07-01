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

def build_citation_edges():
    """Build CITES edges using Semantic Scholar batch API."""
    import requests
    import time
    import os

    session = SessionLocal()
    papers = (
        session.query(Paper)
        .filter(Paper.source == "semantic_scholar")
        .filter(Paper.external_id != None)
        .all()
    )
    paper_map = {p.external_id: p.id for p in papers}
    s2_ids = list(paper_map.keys())
    session.close()

    print(f"Fetching citations for {len(s2_ids)} Semantic Scholar papers...")

    headers = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key

    driver = get_driver()
    edges_created = 0

    # process in batches of 100
    batch_size = 100
    for i in range(0, len(s2_ids), batch_size):
        batch = s2_ids[i:i + batch_size]
        print(f"  Batch {i//batch_size + 1}/{(len(s2_ids) + batch_size - 1)//batch_size}...")

        try:
            resp = requests.post(
                "https://api.semanticscholar.org/graph/v1/paper/batch",
                headers=headers,
                json={"ids": batch},
                params={"fields": "paperId,references"},
                timeout=30,
            )
            if resp.status_code == 429:
                print("  Rate limited, waiting 15s...")
                time.sleep(15)
                continue
            resp.raise_for_status()
            papers_data = resp.json()

        except Exception as e:
            print(f"  Batch error: {e}")
            time.sleep(5)
            continue

        with driver.session() as neo4j:
            for paper_data in papers_data:
                if not paper_data:
                    continue
                citing_s2_id = paper_data.get("paperId")
                if not citing_s2_id or citing_s2_id not in paper_map:
                    continue

                references = paper_data.get("references") or []
                for ref in references:
                    cited_s2_id = ref.get("paperId")
                    if cited_s2_id and cited_s2_id in paper_map:
                        neo4j.run("""
                            MATCH (a:Paper {id: $id_a}), (b:Paper {id: $id_b})
                            MERGE (a)-[:CITES]->(b)
                        """, {
                            "id_a": paper_map[citing_s2_id],
                            "id_b": paper_map[cited_s2_id],
                        })
                        edges_created += 1

        time.sleep(1)  # 1 req/sec with key

    driver.close()
    print(f"Created {edges_created} CITES edges.")

if __name__ == "__main__":
    build_paper_nodes()
    build_citation_edges()
    print("Graph build complete.")