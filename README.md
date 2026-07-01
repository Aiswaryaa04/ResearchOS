# ResearchOS

ResearchOS is a scientific consensus intelligence tool. Given a research topic, it fetches papers from Semantic Scholar, PubMed, and arXiv, extracts structured claims using Claude, scores each paper by evidence quality, and surfaces what the literature actually says — including why sources disagree and what hasn't been studied yet.

Live app: https://researchos101.streamlit.app  
Backend API: https://researchos-backend-89nz.onrender.com/docs

---

## What it does

Most literature review tools tell you what papers exist. ResearchOS tells you what the evidence means.

For any biomedical topic, it produces five outputs.

**Papers and claims** — semantic search over ingested papers, ranked by relevance. Each paper shows its methodology, evidence score, direction (protective/harmful/inconclusive), sample size, population, and funding source, all extracted automatically from the abstract.

**Consensus timeline** — how the field's weighted consensus has shifted year by year. A 2019 paper and a 2024 meta-analysis don't carry equal weight; the timeline reflects that.

**Research gap map** — subpopulations with zero studies, outcomes that have never been replicated, co-interventions nobody has tested, and years with no publications on the topic.

**Evidence summary** — a weighted verdict across the corpus. Three case studies and one RCT pointing in opposite directions is not a tie; the RCT wins, and the summary reflects that.

**Conflict fingerprints** — when two papers contradict each other, ResearchOS diagnoses why across four dimensions: methodology gap, population difference, funding bias, and temporal shift.

---

## Core features

### Conflict fingerprinting
When two papers contradict each other, ResearchOS diagnoses why across four dimensions: methodology gap (one used an RCT, the other a case study), population difference (different age groups or comorbidities), funding bias (industry-funded vs independent), and temporal shift (papers more than five years apart where the science may have evolved). This is the output no existing tool produces — not just "these papers disagree" but a structured explanation of the disagreement.

### Consensus timeline
A year-by-year view of how the field's weighted consensus has shifted. Each year's position reflects cumulative evidence up to that point, weighted by study quality. A single landmark meta-analysis shifting a field that was inconclusive for years is visible as a pattern in the chart, not buried in a list of papers.

### Evidence quality scoring
Papers are scored on a hierarchy: meta-analysis at the top, then RCT, cohort study, case-control, cross-sectional, review, and case study. Sample size adds a logarithmic bonus. Industry funding applies a penalty. Preprints are penalized separately. The weighted consensus verdict reflects this scoring — it is not a vote count.

### Research gap map
After mapping what is known, ResearchOS surfaces what has not been studied. Subpopulations with zero papers (elderly patients, pediatric populations, pregnant women, specific ethnic groups), outcomes that appear in only one study and have never been replicated, co-interventions that no study has combined with the primary drug, and years with no publications on the topic.

### Funding bias detection
Paper metadata is parsed and cross-referenced with CrossRef funder data to surface funding patterns across the corpus. When a majority of papers supporting a particular finding were industry-funded while independent studies show no significant effect, that is surfaced in the evidence summary.

---

## How it compares to existing tools

| Feature | ResearchOS | Elicit | Consensus.app | Scite.ai | Semantic Scholar |
|---|---|---|---|---|---|
| Semantic paper search | Yes | Yes | Yes | Yes | Yes |
| Structured claim extraction | Yes | Yes | No | No | No |
| Evidence quality weighting | Yes | No | No | No | No |
| Contradiction detection | Yes | No | Partial | Partial | No |
| Conflict fingerprinting (why papers disagree) | Yes | No | No | No | No |
| Consensus timeline | Yes | No | No | No | No |
| Research gap detection | Yes | No | No | No | No |
| Funding bias surface | Yes | No | No | No | No |
| Citation relationship graph | Yes | No | No | Yes | Yes |
| Live topic ingestion | Yes | No | No | No | No |

---

## Architecture

```
User enters research topic
        |
        v
Streamlit Frontend (Streamlit Community Cloud)
        |
        | POST /ingest
        v
FastAPI Backend (Render)
        |
        |-- Step 1: Ingestion
        |     Semantic Scholar API  (up to 100 papers per query)
        |     PubMed / NCBI API     (up to 100 papers per query)
        |     arXiv API             (title search)
        |     8 query variations per topic for 500+ paper coverage
        |     --> Papers stored in Postgres (Neon + pgvector)
        |
        |-- Step 2: Structured Extraction
        |     Claude API (claude-sonnet-4-6)
        |     Abstract --> JSON: claim, methodology, sample_size,
        |                        population, funding_type, direction, outcome
        |     Parallel execution: 5 papers simultaneously
        |     --> Extracted fields stored in Postgres
        |
        |-- Step 3: CrossRef Enrichment
        |     CrossRef API (DOI-level funder metadata)
        |     Updates funding_source and funding_type fields
        |     --> 1274 papers enriched per run
        |
        |-- Step 4: Evidence Scoring
        |     Methodology hierarchy: meta-analysis (7) > RCT (6) >
        |     cohort (5) > case-control (4) > cross-sectional (3) >
        |     review (2) > case-study (1)
        |     + Sample size bonus (logarithmic, capped at 0.5)
        |     + Funding penalty (industry: -0.5)
        |     + Preprint penalty (-0.5)
        |     --> evidence_score (0.4-8.0) stored in Postgres
        |
        |-- Step 5: Embeddings
        |     Gemini text-embedding-001 (3072 dimensions)
        |     Sequential with rate limiting (0.7s between calls)
        |     --> pgvector column in Postgres
        |
        |-- Step 6: Knowledge Graph
        |     Neo4j Aura: 908 paper nodes
        |     CITES edges: batch API, 408 citation relationships
        |     CONTRADICTS edges: 4-dimension conflict fingerprints
        |     --> Neo4j Aura (cloud)
        |
Streamlit polls /status every 3 seconds
        |
        v
Results across 5 tabs:
    Papers & Claims     -- semantic search, extracted intelligence
    Consensus Timeline  -- evidence-weighted year-by-year chart
    Research Gaps       -- unstudied populations and outcomes
    Evidence Summary    -- weighted verdict, methodology breakdown
    Conflict Fingerprints -- contradiction diagnosis from Neo4j
```

---

## Deployment architecture

```
Streamlit Community Cloud
    serves the frontend (app.py)
    reads secrets from Streamlit secrets manager
    polls the Render backend for pipeline status

Render (free tier web service)
    serves the FastAPI backend (backend.py)
    runs the full ingestion pipeline as a background thread
    spins down after 15 minutes of inactivity (50 second cold start)

Neon (serverless Postgres, free tier)
    stores all paper data, extracted fields, evidence scores, embeddings
    pgvector extension for cosine similarity search
    accessible from both Render and Streamlit Cloud

Neo4j Aura (free tier)
    908 paper nodes with all metadata
    408 CITES edges from Semantic Scholar citation data
    CONTRADICTS edges with 4-dimension conflict fingerprint labels

All secrets stored in:
    Streamlit secrets manager (for the frontend)
    Render environment variables (for the backend)
    Local .env file (for local development, never committed)
```

---

## Stack

Postgres with pgvector on Neon for paper storage and vector search. Neo4j Aura for the knowledge graph. Claude by Anthropic for structured extraction. Gemini for embeddings. Semantic Scholar, PubMed, and arXiv APIs for ingestion. CrossRef API for funding metadata enrichment. FastAPI on Render for the background pipeline worker. Streamlit on Streamlit Community Cloud for the frontend.

---

## Running locally

Clone the repo and install dependencies:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Start Postgres with pgvector (for local development only):

```bash
docker compose up -d
```

Initialize the database:

```bash
PYTHONPATH=src python -m researchos.ingest.init_db
PYTHONPATH=src python -m researchos.embeddings.migrate_add_embedding
PYTHONPATH=src python -m researchos.extraction.migrate_add_extraction
PYTHONPATH=src python -m researchos.scoring.migrate_add_scoring
```

Run the full pipeline on a topic:

```bash
PYTHONPATH=src python -m researchos.ingest.run_ingest "your topic here" --scale
PYTHONPATH=src python -m researchos.extraction.run_extraction
PYTHONPATH=src python -m researchos.ingest.run_crossref
PYTHONPATH=src python -m researchos.scoring.run_scoring
PYTHONPATH=src python -m researchos.embeddings.embed_papers
PYTHONPATH=src python -m researchos.graph.build_graph
PYTHONPATH=src python -m researchos.graph.conflict_fingerprint
```

Start the backend and frontend in separate terminals:

```bash
PYTHONPATH=src uvicorn researchos.api.backend:app --port 8000
PYTHONPATH=src .venv/bin/streamlit run src/researchos/api/app.py
```

---

## API keys needed

Semantic Scholar (free, request at semanticscholar.org/product/api), NCBI for PubMed (free, ncbi.nlm.nih.gov/account), Anthropic for Claude (paid per use, approximately $0.01 per paper extracted), Google AI Studio for Gemini embeddings (free tier, 1500 requests per day), Neo4j Aura (free tier, up to 200k nodes and 400k relationships), CrossRef (no key needed, just include your email in requests).

---

## Project structure

```
src/researchos/
    ingest/
        semantic_scholar.py   Semantic Scholar API client with exponential backoff
        pubmed.py             PubMed NCBI API client, XML parsing
        arxiv.py              arXiv API client with retry logic
        run_ingest.py         Multi-source ingestion with query expansion for 500+ papers
        run_crossref.py       CrossRef DOI-level funding enrichment
        models.py             SQLAlchemy Paper model with all fields
        init_db.py            Database table creation

    embeddings/
        embedder.py           Gemini text-embedding-001 (3072 dimensions)
        embed_papers.py       Sequential embedding with rate limit handling
        migrate_add_embedding.py  Adds pgvector column to papers table
        search.py             Cosine similarity search via pgvector

    extraction/
        extractor.py          Claude API structured extraction (8 fields per paper)
        run_extraction.py     Parallel extraction with 5 concurrent Claude calls
        migrate_add_extraction.py  Adds extraction columns to papers table

    scoring/
        scorer.py             Evidence hierarchy scoring with sample size and funding modifiers
        run_scoring.py        Applies scores to all extracted papers
        migrate_add_scoring.py  Adds scoring columns to papers table

    graph/
        neo4j_client.py       Neo4j Aura connection wrapper
        build_graph.py        Paper nodes + batch citation edges via S2 API
        conflict_fingerprint.py  4-dimension contradiction detection and edge creation
        query_graph.py        Graph query functions for contradiction retrieval

    analysis/
        timeline.py           Evidence-weighted year-by-year consensus computation
        gaps.py               Subpopulation and outcome gap detection

    api/
        backend.py            FastAPI with background pipeline execution
        app.py                Streamlit frontend with 5-tab results view
        worker.py             Pipeline orchestration helper
```

---

