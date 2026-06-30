import time
from researchos.db import SessionLocal
from researchos.ingest.models import Paper
from researchos.embeddings.embedder import embed_text


def embed_all_papers(batch_size: int = 10):
    session = SessionLocal()

    # fetch all papers that don't have an embedding yet
    papers = session.query(Paper).filter(Paper.embedding == None).all()
    print(f"Found {len(papers)} papers without embeddings.")

    embedded = 0
    skipped = 0

    for i, paper in enumerate(papers):
        # use abstract if available, fall back to title only
        text = paper.abstract or paper.title
        if not text:
            print(f"  Skipping '{paper.title[:60]}' — no text to embed")
            skipped += 1
            continue

        try:
            vector = embed_text(text)
            paper.embedding = vector
            embedded += 1

            # commit in batches to avoid one large transaction
            if embedded % batch_size == 0:
                session.commit()
                print(f"  Embedded {embedded}/{len(papers)}...")

            # Gemini free tier: 1500 requests/day, ~1 req/sec safe rate
            time.sleep(0.5)

        except Exception as e:
            print(f"  Failed on '{paper.title[:60]}': {e}")
            skipped += 1
            continue

    session.commit()
    session.close()
    print(f"\nDone. Embedded: {embedded}, Skipped: {skipped}")


if __name__ == "__main__":
    embed_all_papers()