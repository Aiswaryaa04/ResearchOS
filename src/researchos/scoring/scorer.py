import math

# Base scores per methodology tier
METHODOLOGY_SCORES = {
    "meta_analysis":    7.0,
    "rct":              6.0,
    "cohort_study":     5.0,
    "case_control":     4.0,
    "cross_sectional":  3.0,
    "review":           2.0,
    "case_study":       1.0,
    "other":            1.0,
}

# Human-readable tier labels
METHODOLOGY_TIERS = {
    "meta_analysis":    "Tier 1",
    "rct":              "Tier 2",
    "cohort_study":     "Tier 3",
    "case_control":     "Tier 4",
    "cross_sectional":  "Tier 5",
    "review":           "Tier 6",
    "case_study":       "Tier 7",
    "other":            "Tier 7",
}

# Funding type penalties
FUNDING_PENALTIES = {
    "industry":       -0.5,
    "mixed":          -0.25,
    "public":          0.0,
    "none_declared":  -0.1,   # slight penalty for non-disclosure
    "unknown":        -0.1,
}

MAX_SAMPLE_BONUS = 0.5   # cap so sample size never overrides methodology tier
SAMPLE_BONUS_SCALE = 10000  # n=10000 gives roughly half the max bonus


def compute_score(
    methodology: str | None,
    sample_size: int | None,
    funding_type: str | None,
    is_preprint: bool = False,
) -> tuple[float, str]:
    """
    Compute an evidence score and tier label for a paper.
    Returns (score, tier) tuple.
    Score range: roughly 0.4 to 8.0
    """
    # base score from methodology
    base = METHODOLOGY_SCORES.get(methodology or "other", 1.0)
    tier = METHODOLOGY_TIERS.get(methodology or "other", "Tier 7")

    # sample size bonus: logarithmic scale so large samples help but don't dominate
    # log10(100) = 2, log10(10000) = 4, log10(100000) = 5
    sample_bonus = 0.0
    if sample_size and sample_size > 0:
        sample_bonus = min(
            MAX_SAMPLE_BONUS,
            MAX_SAMPLE_BONUS * math.log10(sample_size) / math.log10(SAMPLE_BONUS_SCALE)
        )

    # funding penalty
    funding_penalty = FUNDING_PENALTIES.get(funding_type or "unknown", -0.1)

    # preprint penalty
    preprint_penalty = -0.5 if is_preprint else 0.0

    score = base + sample_bonus + funding_penalty + preprint_penalty

    # clamp to reasonable range
    score = max(0.1, round(score, 3))

    return score, tier


if __name__ == "__main__":
    # test a few cases to verify the scoring logic makes sense
    test_cases = [
        ("meta_analysis", 5000,  "public",       False),
        ("rct",           1200,  "industry",     False),
        ("cohort_study",  50000, "public",       False),
        ("case_study",    1,     "none_declared",False),
        ("rct",           200,   "public",       True),   # preprint RCT
        ("other",         None,  "unknown",      False),
    ]

    print(f"{'Methodology':<20} {'N':>8} {'Funding':<15} {'Preprint':<10} {'Score':>7} {'Tier'}")
    print("-" * 75)
    for method, n, funding, preprint in test_cases:
        score, tier = compute_score(method, n, funding, preprint)
        print(f"{method:<20} {str(n):>8} {funding:<15} {str(preprint):<10} {score:>7} {tier}")