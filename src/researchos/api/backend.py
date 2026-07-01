import os
import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ResearchOS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = {}


class TopicRequest(BaseModel):
    topic: str
    limit: int = 20


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def start_ingestion(request: TopicRequest):
    import threading

    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "topic": request.topic, "step": "starting"}

    def run():
        try:
            jobs[job_id]["step"] = "ingesting"
            from researchos.ingest.run_ingest import ingest
            ingest(request.topic, limit=request.limit, scale=True)

            jobs[job_id]["step"] = "extracting"
            from researchos.extraction.run_extraction import run_extraction
            run_extraction()

            jobs[job_id]["step"] = "crossref"
            from researchos.ingest.run_crossref import enrich_with_crossref
            enrich_with_crossref()

            jobs[job_id]["step"] = "scoring"
            from researchos.scoring.run_scoring import run_scoring
            run_scoring()

            jobs[job_id]["step"] = "embedding"
            from researchos.embeddings.embed_papers import embed_all_papers
            embed_all_papers()

            jobs[job_id]["step"] = "graph"
            from researchos.graph.build_graph import build_paper_nodes
            from researchos.graph.conflict_fingerprint import build_contradiction_edges
            build_paper_nodes()
            build_contradiction_edges()

            jobs[job_id]["status"] = "done"
            jobs[job_id]["step"] = "complete"

        except Exception as e:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return {"job_id": job_id, "status": "started"}


@app.get("/status/{job_id}")
def get_status(job_id: str):
    if job_id not in jobs:
        return {"status": "not_found"}
    return jobs[job_id]


@app.get("/papers/count")
def paper_count():
    from researchos.db import SessionLocal
    from researchos.ingest.models import Paper
    session = SessionLocal()
    total = session.query(Paper).count()
    extracted = session.query(Paper).filter(Paper.extraction_done == True).count()
    scored = session.query(Paper).filter(Paper.scoring_done == True).count()
    session.close()
    return {"total": total, "extracted": extracted, "scored": scored}