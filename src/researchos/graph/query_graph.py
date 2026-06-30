from researchos.graph.neo4j_client import get_driver


def get_contradictions(topic: str = None, min_dimensions: int = 1) -> list[dict]:
    """
    Return all contradiction pairs, optionally filtered by topic keyword.
    min_dimensions filters for contradictions with at least N dimensions active.
    """
    driver = get_driver()

    with driver.session() as neo4j:
        query = """
            MATCH (a:Paper)-[r:CONTRADICTS]->(b:Paper)
            WHERE r.dimension_count >= $min_dim
            RETURN
                a.title AS paper_a,
                b.title AS paper_b,
                a.year AS year_a,
                b.year AS year_b,
                a.methodology AS method_a,
                b.methodology AS method_b,
                a.evidence_score AS score_a,
                b.evidence_score AS score_b,
                r.methodology_gap AS methodology_gap,
                r.population_difference AS population_difference,
                r.funding_bias AS funding_bias,
                r.temporal_shift AS temporal_shift,
                r.dimension_count AS dimension_count,
                r.reasons AS reasons
            ORDER BY r.dimension_count DESC, (score_a + score_b) DESC
        """

        results = neo4j.run(query, {"min_dim": min_dimensions}).data()

    driver.close()

    if topic:
        topic_lower = topic.lower()
        results = [
            r for r in results
            if topic_lower in (r["paper_a"] or "").lower()
            or topic_lower in (r["paper_b"] or "").lower()
        ]

    return results


def print_contradictions(topic: str = None):
    results = get_contradictions(topic)
    if not results:
        print("No contradictions found.")
        return

    print(f"\nFound {len(results)} contradiction(s):\n")
    for i, r in enumerate(results, 1):
        print(f"{'='*70}")
        print(f"Contradiction #{i} ({r['dimension_count']} dimensions)")
        print(f"  A ({r['year_a']}, {r['method_a']}, score={r['score_a']}): {r['paper_a']}")
        print(f"  B ({r['year_b']}, {r['method_b']}, score={r['score_b']}): {r['paper_b']}")
        print(f"  Why they disagree:")
        for reason in (r["reasons"] or []):
            print(f"    • {reason}")
        print()


if __name__ == "__main__":
    print_contradictions()