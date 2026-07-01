from researchos.ingest.run_ingest import ingest
from researchos.extraction.run_extraction import run_extraction
from researchos.scoring.run_scoring import run_scoring
from researchos.embeddings.embed_papers import embed_all_papers


def run_full_pipeline(topic: str, limit: int = 20):
    """Full pipeline as a single background job."""
    print(f"[worker] Starting pipeline for: {topic}")
    ingest(topic, limit=limit)
    print("[worker] Ingestion done")
    run_extraction()
    print("[worker] Extraction done")
    run_scoring()
    print("[worker] Scoring done")
    embed_all_papers()
    print("[worker] Embeddings done")
    print(f"[worker] Pipeline complete for: {topic}")