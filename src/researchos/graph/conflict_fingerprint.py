from researchos.graph.neo4j_client import get_driver


def fingerprint_contradiction(paper_a: dict, paper_b: dict) -> dict:
    """
    Given two papers that contradict each other (opposite directions),
    diagnose WHY they contradict across 4 dimensions.
    Returns a fingerprint dict describing the contradiction.
    """
    reasons = []
    dimensions = {}

    # 1. METHODOLOGY GAP
    # Score difference > 2 means meaningfully different evidence tiers
    score_a = paper_a.get("evidence_score", 0) or 0
    score_b = paper_b.get("evidence_score", 0) or 0
    method_a = paper_a.get("methodology", "other")
    method_b = paper_b.get("methodology", "other")

    if abs(score_a - score_b) >= 2.0:
        dimensions["methodology_gap"] = True
        reasons.append(
            f"Methodology mismatch: '{method_a}' (score {score_a}) "
            f"vs '{method_b}' (score {score_b})"
        )
    else:
        dimensions["methodology_gap"] = False

    # 2. POPULATION DIFFERENCE
    # Simple heuristic: if population strings share fewer than 2 words, they're different
    pop_a = set((paper_a.get("population") or "").lower().split())
    pop_b = set((paper_b.get("population") or "").lower().split())
    # remove common stopwords that don't signal population similarity
    stopwords = {"with", "in", "of", "the", "a", "an", "and", "or", "patients", "study"}
    pop_a -= stopwords
    pop_b -= stopwords
    overlap = pop_a & pop_b

    if len(overlap) < 2 and pop_a and pop_b:
        dimensions["population_difference"] = True
        reasons.append(
            f"Different populations: '{paper_a.get('population', 'unknown')}' "
            f"vs '{paper_b.get('population', 'unknown')}'"
        )
    else:
        dimensions["population_difference"] = False

    # 3. FUNDING BIAS
    fund_a = paper_a.get("funding_type", "unknown")
    fund_b = paper_b.get("funding_type", "unknown")

    if (fund_a == "industry" and fund_b == "public") or \
       (fund_a == "public" and fund_b == "industry"):
        dimensions["funding_bias"] = True
        reasons.append(
            f"Funding conflict: one industry-funded ('{fund_a}'), "
            f"other independent ('{fund_b}')"
        )
    else:
        dimensions["funding_bias"] = False

    # 4. TEMPORAL SHIFT
    year_a = paper_a.get("year", 0) or 0
    year_b = paper_b.get("year", 0) or 0

    if abs(year_a - year_b) >= 5:
        dimensions["temporal_shift"] = True
        reasons.append(
            f"Temporal gap: {year_a} vs {year_b} "
            f"({abs(year_a - year_b)} years apart — science may have evolved)"
        )
    else:
        dimensions["temporal_shift"] = False

    return {
        "dimensions": dimensions,
        "reasons": reasons,
        "dimension_count": sum(dimensions.values()),
    }


def build_contradiction_edges():
    """
    Find all pairs of papers with opposite directions and
    create CONTRADICTS edges in Neo4j with fingerprint labels.
    """
    driver = get_driver()

    with driver.session() as neo4j:
        # find all pairs where one says "protective" and other says "harmful"
        pairs = neo4j.run("""
            MATCH (a:Paper), (b:Paper)
            WHERE a.id < b.id
              AND a.outcome <> ''
              AND b.outcome <> ''
              AND (
                (a.direction = 'protective' AND b.direction = 'harmful') OR
                (a.direction = 'harmful' AND b.direction = 'protective')
              )
            RETURN a, b
        """).data()

        print(f"Found {len(pairs)} contradicting paper pairs.")
        edges_created = 0

        for pair in pairs:
            pa = dict(pair["a"])
            pb = dict(pair["b"])

            fingerprint = fingerprint_contradiction(pa, pb)

            neo4j.run("""
                MATCH (a:Paper {id: $id_a}), (b:Paper {id: $id_b})
                CREATE (a)-[r:CONTRADICTS {
                    methodology_gap: $methodology_gap,
                    population_difference: $population_difference,
                    funding_bias: $funding_bias,
                    temporal_shift: $temporal_shift,
                    dimension_count: $dimension_count,
                    reasons: $reasons
                }]->(b)
            """, {
                "id_a": pa["id"],
                "id_b": pb["id"],
                "methodology_gap": fingerprint["dimensions"]["methodology_gap"],
                "population_difference": fingerprint["dimensions"]["population_difference"],
                "funding_bias": fingerprint["dimensions"]["funding_bias"],
                "temporal_shift": fingerprint["dimensions"]["temporal_shift"],
                "dimension_count": fingerprint["dimension_count"],
                "reasons": fingerprint["reasons"],
            })
            edges_created += 1

        print(f"Created {edges_created} CONTRADICTS edges.")

    driver.close()


if __name__ == "__main__":
    build_contradiction_edges()