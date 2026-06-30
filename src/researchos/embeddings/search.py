from researchos.db import SessionLocal
from researchos.ingest.models import Paper
from researchos.embeddings.embedder import embed_query


def search_papers(query: str, top_k: int = 5) -> list[dict]:
    """
    Find the most semantically similar papers to a query string.
    Returns a list of dicts with title, year, source, and similarity score.
    """
    query_vector = embed_query(query)

    session = SessionLocal()

    # pgvector's <=> operator = cosine distance (lower = more similar)
    # we cast to string for the raw SQL since SQLAlchemy doesn't know this operator natively
    results = session.execute(
        __import__("sqlalchemy").text("""
            SELECT
                id,
                title,
                year,
                source,
                abstract,
                1 - (embedding <=> CAST(:vec AS vector)) AS similarity
            FROM papers
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:vec AS vector)
            LIMIT :k
        """),
        {"vec": str(query_vector), "k": top_k}
    ).fetchall()

    session.close()

    return [
        {
            "title": r.title,
            "year": r.year,
            "source": r.source,
            "similarity": round(r.similarity, 4),
            "abstract": (r.abstract or "")[:200] + "..." if r.abstract else "No abstract",
        }
        for r in results
    ]


if __name__ == "__main__":
    query = "does metformin protect against colorectal cancer?"
    print(f"Query: {query}\n")
    results = search_papers(query, top_k=5)
    for i, r in enumerate(results, 1):
        print(f"{i}. [{r['similarity']}] ({r['year']}) {r['title']}")
        print(f"   Source: {r['source']}")
        print(f"   {r['abstract']}\n")