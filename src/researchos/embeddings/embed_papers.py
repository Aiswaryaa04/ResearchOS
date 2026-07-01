import time
from researchos.db import SessionLocal
from researchos.ingest.models import Paper
from researchos.embeddings.embedder import embed_text


def embed_single(paper_id: str, text: str) -> tuple[str, list | None]:
    """Embed a single paper with retry logic."""
    wait = 5
    for attempt in range(4):
        try:
            vector = embed_text(text)
            return paper_id, vector
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                wait *= 2
                continue
            print(f"  Failed: {e}")
            return paper_id, None
    return paper_id, None


def embed_all_papers():
    """
    Embed paper abstracts sequentially with rate limiting.
    Gemini free tier: 100 requests/minute → 0.7s delay between requests.
    """
    session = SessionLocal()
    papers = session.query(Paper).filter(Paper.embedding == None).all()
    paper_data = [
        (p.id, p.abstract or p.title)
        for p in papers
        if (p.abstract or p.title)
    ]
    session.close()

    total = len(paper_data)
    print(f"Found {total} papers without embeddings.")

    if total == 0:
        return

    done = 0
    skipped = 0

    for paper_id, text in paper_data:
        pid, vector = embed_single(paper_id, text)

        if vector is None:
            skipped += 1
            done += 1
            continue

        s = SessionLocal()
        paper = s.query(Paper).filter(Paper.id == paper_id).first()
        if paper:
            paper.embedding = vector
            s.commit()
        s.close()

        done += 1
        if done % 50 == 0:
            print(f"  Progress: {done}/{total} (skipped: {skipped})")

        # stay under 100 requests/minute
        time.sleep(0.7)

    print(f"\nDone. Embedded: {done - skipped}, Skipped: {skipped}")


if __name__ == "__main__":
    embed_all_papers()