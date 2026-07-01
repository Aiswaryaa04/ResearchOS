import streamlit as st
import plotly.graph_objects as go
import sys
import os
import threading
from collections import defaultdict, Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../..","src"))

from researchos.ingest.run_ingest import ingest
from researchos.extraction.run_extraction import run_extraction
from researchos.scoring.run_scoring import run_scoring
from researchos.embeddings.embed_papers import embed_all_papers
from researchos.embeddings.search import search_papers
from researchos.analysis.timeline import build_consensus_timeline
from researchos.analysis.gaps import detect_gaps
from researchos.db import SessionLocal
from researchos.ingest.models import Paper

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ResearchOS",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .hero {
        text-align: center;
        padding: 60px 20px 40px 20px;
    }
    .hero h1 {
        font-size: 3rem;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    .hero p {
        font-size: 1.1rem;
        color: #64748b;
        max-width: 600px;
        margin: 0 auto 2rem auto;
        line-height: 1.6;
    }
    .stTextInput input {
        font-size: 1.1rem !important;
        padding: 1rem 1.2rem !important;
        border-radius: 12px !important;
        border: 2px solid #e2e8f0 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
    }
    .stTextInput input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 4px 20px rgba(99,102,241,0.15) !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.75rem 2rem !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(99,102,241,0.3) !important;
    }
    [data-testid="metric-container"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem;
    }
    .badge-protective { background:#dcfce7; color:#166534; padding:2px 10px; border-radius:20px; font-size:0.8rem; font-weight:600; }
    .badge-harmful { background:#fee2e2; color:#991b1b; padding:2px 10px; border-radius:20px; font-size:0.8rem; font-weight:600; }
    .badge-inconclusive { background:#fef9c3; color:#854d0e; padding:2px 10px; border-radius:20px; font-size:0.8rem; font-weight:600; }
    .section-header { font-size:1.4rem; font-weight:700; color:#0f172a; margin-bottom:0.25rem; }
    .section-sub { font-size:0.95rem; color:#64748b; margin-bottom:1.5rem; }
    hr { border:none; border-top:1px solid #e2e8f0; margin:1.5rem 0; }
</style>
""", unsafe_allow_html=True)

# ── session state ─────────────────────────────────────────────────────────────
if "stage" not in st.session_state:
    st.session_state.stage = "landing"  # landing | processing | results
if "topic" not in st.session_state:
    st.session_state.topic = ""
if "query" not in st.session_state:
    st.session_state.query = ""
if "results" not in st.session_state:
    st.session_state.results = []
if "pipeline_done" not in st.session_state:
    st.session_state.pipeline_done = False

# ── DB stats ──────────────────────────────────────────────────────────────────
session = SessionLocal()
total_papers = session.query(Paper).count()
extracted = session.query(Paper).filter(Paper.extraction_done == True).count()
session.close()

# ══════════════════════════════════════════════════════════════════════════════
# LANDING PAGE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.stage == "landing":
    st.markdown("""
    <div class="hero">
        <h1>🔬 ResearchOS</h1>
        <p>Scientific consensus intelligence — discover what the literature says,
        why experts disagree, and whether the debate is settled.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        topic = st.text_input(
            "",
            placeholder="e.g. SSRIs and treatment-resistant depression",
            label_visibility="collapsed",
            key="topic_input",
        )
        top_k = st.slider("Papers to analyze", 5, 20, 10)
        start = st.button("🔍 Research this topic", use_container_width=True)

        if start and topic:
            st.session_state.topic = topic
            st.session_state.top_k = top_k
            st.session_state.stage = "processing"
            st.session_state.pipeline_done = False
            st.rerun()
        elif start and not topic:
            st.warning("Please enter a research topic first.")

    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📄 Papers indexed", f"{total_papers:,}")
    c2.metric("🧠 Claims extracted", f"{extracted:,}")
    c3.metric("📡 Data sources", "3")
    c4.metric("🔬 Topics covered", "Any topic")

    st.markdown("---")
    st.markdown("### What ResearchOS does differently")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        st.markdown("**🧬 Conflict Fingerprinting**")
        st.caption("Diagnoses *why* papers disagree — methodology, population, funding bias, or temporal shift.")
    with f2:
        st.markdown("**📈 Consensus Timeline**")
        st.caption("Shows how scientific opinion has shifted year by year, weighted by evidence quality.")
    with f3:
        st.markdown("**⚖️ Evidence Scoring**")
        st.caption("Meta-analyses outweigh case studies. Results weighted by study design, not paper count.")
    with f4:
        st.markdown("**🗺️ Research Gap Map**")
        st.caption("Surfaces unstudied populations, unreplicated outcomes, and co-intervention gaps.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# PROCESSING PAGE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.stage == "processing":
    import time
    import requests as http_requests

    topic = st.session_state.topic
    top_k = st.session_state.get("top_k", 10)

    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

    st.markdown(f"""
    <div class="hero">
        <h1>🔬 ResearchOS</h1>
        <p>Researching: <strong>{topic}</strong></p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        status_box = st.empty()
        progress = st.progress(0)

        # start the job if we haven't yet
        if "job_id" not in st.session_state:
            try:
                resp = http_requests.post(
                    f"{BACKEND_URL}/ingest",
                    json={"topic": topic, "limit": top_k},
                    timeout=60,
                )
                st.session_state.job_id = resp.json()["job_id"]
            except Exception as e:
                st.warning("⏳ Backend is waking up (this takes ~50 seconds on free tier). Please click 'Research this topic' again.")
                st.session_state.stage = "landing"
                st.rerun()

        # poll for status
        step_progress = {
            "starting": 5,
            "ingesting": 20,
            "extracting": 50,
            "scoring": 70,
            "embedding": 85,
            "complete": 100,
        }
        step_labels = {
            "starting": "Starting pipeline...",
            "ingesting": "📡 Fetching papers from Semantic Scholar, PubMed, arXiv...",
            "extracting": "🧠 Extracting claims with Claude AI...",
            "scoring": "⚖️ Scoring evidence quality...",
            "embedding": "🔢 Building semantic embeddings...",
            "complete": "✅ Done! Loading results...",
        }

        try:
            resp = http_requests.get(
                f"{BACKEND_URL}/status/{st.session_state.job_id}",
                timeout=30,
            )
            job = resp.json()
            step = job.get("step", "starting")
            job_status = job.get("status", "running")

            progress.progress(step_progress.get(step, 5))
            status_box.markdown(f"**{step_labels.get(step, 'Processing...')}**")

            if job_status == "done":
                del st.session_state.job_id
                st.session_state.query = f"what does the research say about {topic}?"
                st.session_state.results = []
                st.session_state.stage = "results"
                st.rerun()
            elif job_status == "error":
                st.error(f"Pipeline failed: {job.get('error')}")
                del st.session_state.job_id
                st.session_state.stage = "landing"
            else:
                time.sleep(3)
                st.rerun()

        except Exception as e:
            st.error(f"Backend connection error: {e}")
            st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# RESULTS PAGE
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.stage == "results":
    query = st.session_state.query
    top_k = st.session_state.get("top_k", 10)

    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("### 🔬 ResearchOS")
        st.caption(f"Topic: *{st.session_state.topic}*")
    with col2:
        if st.button("← New topic"):
            st.session_state.stage = "landing"
            st.session_state.results = []
            st.session_state.pipeline_done = False
            st.rerun()

    st.markdown("---")

    # semantic search input
    query = st.text_input(
        "Ask a specific question about this topic:",
        value=st.session_state.query,
        key="search_query"
    )
    if query != st.session_state.query:
        st.session_state.query = query
        st.session_state.results = []

    if not st.session_state.results:
        with st.spinner("Searching..."):
            st.session_state.results = search_papers(query, top_k=top_k)

    results = st.session_state.results

    if not results:
        st.warning("No relevant papers found. Try rephrasing your question.")
        st.stop()

    # evidence verdict banner
    session = SessionLocal()
    all_scored = session.query(Paper).filter(Paper.scoring_done == True).all()
    session.close()

    direction_scores = defaultdict(float)
    direction_counts = Counter()
    for p in all_scored:
        if p.direction and p.evidence_score:
            direction_scores[p.direction] += p.evidence_score
            direction_counts[p.direction] += 1

    total_score = sum(direction_scores.values())
    if total_score > 0:
        top_direction = max(direction_scores, key=direction_scores.get)
        top_pct = direction_scores[top_direction] / total_score
        color = {"protective": "#dcfce7", "harmful": "#fee2e2", "inconclusive": "#fef9c3"}.get(top_direction, "#f1f5f9")
        text_color = {"protective": "#166534", "harmful": "#991b1b", "inconclusive": "#854d0e"}.get(top_direction, "#475569")
        icon = {"protective": "🟢", "harmful": "🔴", "inconclusive": "🟡"}.get(top_direction, "⚪")
        st.markdown(f"""
        <div style="background:{color}; border-radius:12px; padding:1rem 1.5rem; margin-bottom:1.5rem;">
            <span style="font-size:1.1rem; font-weight:700; color:{text_color};">
                {icon} Evidence-weighted verdict: {top_direction.title()} ({top_pct:.0%} of weighted evidence)
            </span>
            <span style="color:{text_color}; font-size:0.9rem; margin-left:1rem;">
                Based on {sum(direction_counts.values())} papers across 3 sources
            </span>
        </div>
        """, unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📄 Papers & Claims",
        "📈 Consensus Timeline",
        "🗺️ Research Gaps",
        "⚖️ Evidence Summary",
        "🔥 Conflict Fingerprints",

    ])

    # ── TAB 1 ────────────────────────────────────────────────────────────────
    with tab1:
        st.markdown(f'<div class="section-header">Top {len(results)} papers</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Ranked by semantic similarity to your question.</div>', unsafe_allow_html=True)

        for i, r in enumerate(results, 1):
            direction = r.get("direction") or "unknown"
            score = r.get("evidence_score") or 0
            methodology = (r.get("methodology") or "unknown").replace("_", " ").title()
            year = r.get("year") or "?"
            source = (r.get("source") or "").replace("_", " ").title()
            similarity = r.get("similarity", 0)
            icon = {"protective": "🟢", "harmful": "🔴", "inconclusive": "🟡", "neutral": "🟡"}.get(direction, "⚪")

            with st.expander(f"{icon}  {r['title']} ({year})"):
                mc1, mc2, mc3, mc4, mc5 = st.columns(5)
                mc1.metric("Evidence Score", f"{score:.1f} / 8")
                mc2.metric("Study Type", methodology)
                mc3.metric("Direction", direction.title())
                mc4.metric("Relevance", f"{similarity:.0%}")
                mc5.metric("Source", source)

                if r.get("abstract"):
                    st.markdown("**Abstract:**")
                    st.markdown(f"> {r['abstract'][:600]}{'...' if len(r.get('abstract','')) > 600 else ''}")

                session = SessionLocal()
                paper = session.query(Paper).filter(Paper.id == r.get("id")).first()
                session.close()

                if paper and paper.extraction_done:
                    st.markdown("---")
                    st.markdown("**🧠 Extracted Intelligence**")
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        st.markdown(f"**Main claim:** {paper.main_claim or 'N/A'}")
                        st.markdown(f"**Population:** {paper.population or 'N/A'}")
                        st.markdown(f"**Sample size:** {f'{paper.sample_size:,}' if paper.sample_size else 'Not reported'}")
                    with ec2:
                        st.markdown(f"**Outcome measured:** {paper.outcome or 'N/A'}")
                        funding_flag = "⚠️ Industry funded" if paper.funding_type == "industry" else paper.funding_type or "unknown"
                        st.markdown(f"**Funding:** {funding_flag} — {paper.funding_source or 'not specified'}")
                        st.markdown(f"**Preprint:** {'⚠️ Yes' if paper.is_preprint else '✅ No'}")

    # ── TAB 2 ────────────────────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="section-header">How has scientific consensus shifted?</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Evidence-weighted consensus over time.</div>', unsafe_allow_html=True)

        keyword = st.text_input("Filter by outcome keyword", value="", key="timeline_filter")
        timeline = build_consensus_timeline(outcome_keyword=keyword if keyword else None)

        if not timeline:
            st.warning("Not enough data for a timeline yet.")
        else:
            years = [t["year"] for t in timeline]
            confidence = [t["confidence"] for t in timeline]
            consensus = [t["consensus"] for t in timeline]
            papers_per_year = [t["papers_this_year"] for t in timeline]
            color_map = {"protective": "#22c55e", "harmful": "#ef4444", "inconclusive": "#f59e0b"}
            bar_colors = [color_map.get(c, "#94a3b8") for c in consensus]

            fig = go.Figure()
            fig.add_trace(go.Bar(x=years, y=papers_per_year, name="Papers published", marker_color="#e0e7ff", yaxis="y2"))
            fig.add_trace(go.Scatter(
                x=years, y=confidence, mode="lines+markers",
                name="Consensus confidence",
                line=dict(width=3, color="#6366f1"),
                marker=dict(size=14, color=bar_colors, line=dict(width=2, color="white")),
            ))
            fig.update_layout(
                title="Weighted Scientific Consensus Over Time",
                xaxis_title="Year",
                yaxis=dict(title="Confidence", range=[0, 1.1]),
                yaxis2=dict(title="Papers published", overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                height=420, plot_bgcolor="white", paper_bgcolor="white",
                xaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig, use_container_width=True)

            for entry in reversed(timeline):
                icon = {"protective": "🟢", "harmful": "🔴", "inconclusive": "🟡"}.get(entry["consensus"], "⚪")
                c1, c2, c3 = st.columns([1, 3, 2])
                c1.markdown(f"**{entry['year']}**")
                c2.markdown(f"{icon} {entry['consensus'].title()} — {entry['confidence']:.0%} confidence")
                c3.markdown(f"{entry['papers_this_year']} paper(s)")

    # ── TAB 3 ────────────────────────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="section-header">What hasn\'t been studied?</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Automatically detected gaps in the literature.</div>', unsafe_allow_html=True)

        with st.spinner("Mapping gaps..."):
            gaps = detect_gaps()

        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Unstudied populations", len(gaps["unstudied_subpopulations"]))
        g2.metric("Understudied populations", len(gaps["understudied_subpopulations"]))
        g3.metric("Unstudied co-interventions", len(gaps["unstudied_co_interventions"]))
        g4.metric("Unreplicated outcomes", len(gaps["unreplicated_outcomes"]))

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🚨 Unstudied populations")
            for s in gaps["unstudied_subpopulations"]:
                st.markdown(f"- {s}")
            st.markdown("#### ⚠️ Understudied populations")
            for s in gaps["understudied_subpopulations"]:
                st.markdown(f"- {s} *(only {gaps['subpop_coverage'][s]} paper(s))*")
        with col2:
            st.markdown("#### 🔬 Unstudied co-interventions")
            for c in gaps["unstudied_co_interventions"]:
                st.markdown(f"- {c}")
            st.markdown("#### 📋 Unreplicated outcomes")
            for o in gaps["unreplicated_outcomes"]:
                st.markdown(f"- {o}")

        if gaps["temporal_gaps"]:
            st.info(f"**📅 Temporal gaps** — no papers found for: {gaps['temporal_gaps']}")

    # ── TAB 4 ────────────────────────────────────────────────────────────────
    with tab4:
        st.markdown('<div class="section-header">Evidence-weighted consensus</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Each paper\'s contribution weighted by study quality.</div>', unsafe_allow_html=True)

        protective_pct = direction_scores.get("protective", 0) / total_score if total_score else 0
        harmful_pct = direction_scores.get("harmful", 0) / total_score if total_score else 0
        inconclusive_pct = (direction_scores.get("inconclusive", 0) + direction_scores.get("neutral", 0)) / total_score if total_score else 0

        vc1, vc2, vc3 = st.columns(3)
        vc1.metric("🟢 Protective", f"{protective_pct:.0%}", f"{direction_counts.get('protective', 0)} papers")
        vc2.metric("🔴 Harmful", f"{harmful_pct:.0%}", f"{direction_counts.get('harmful', 0)} papers")
        vc3.metric("🟡 Inconclusive", f"{inconclusive_pct:.0%}", f"{direction_counts.get('inconclusive', 0) + direction_counts.get('neutral', 0)} papers")

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Study type breakdown**")
            methodology_counts = Counter(p.methodology for p in all_scored if p.methodology)
            fig2 = go.Figure(go.Bar(
                x=[m.replace("_", " ").title() for m in methodology_counts.keys()],
                y=list(methodology_counts.values()),
                marker_color="#6366f1", marker_opacity=0.8,
            ))
            fig2.update_layout(height=320, plot_bgcolor="white", paper_bgcolor="white",
                               xaxis=dict(showgrid=False), yaxis=dict(title="Papers", gridcolor="#f1f5f9"),
                               margin=dict(t=20, b=20))
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            st.markdown("**Funding source distribution**")
            funding_counts = Counter(p.funding_type for p in all_scored if p.funding_type)
            colors_funding = {"public": "#22c55e", "industry": "#ef4444", "mixed": "#f59e0b",
                              "none_declared": "#94a3b8", "unknown": "#cbd5e1"}
            fig3 = go.Figure(go.Pie(
                labels=list(funding_counts.keys()),
                values=list(funding_counts.values()),
                hole=0.5,
                marker_colors=[colors_funding.get(k, "#94a3b8") for k in funding_counts.keys()],
            ))
            fig3.update_layout(height=320, paper_bgcolor="white", margin=dict(t=20, b=20))
            st.plotly_chart(fig3, use_container_width=True)

        st.markdown("---")
        st.markdown("**Top papers by evidence score**")
        top_papers = sorted(all_scored, key=lambda p: p.evidence_score or 0, reverse=True)[:5]
        for p in top_papers:
            tc1, tc2, tc3 = st.columns([4, 1, 1])
            tc1.markdown(f"**{p.title[:80]}{'...' if len(p.title) > 80 else ''}**")
            tc2.markdown(f"Score: **{p.evidence_score:.1f}**")
            tc3.markdown(f"{(p.methodology or 'other').replace('_', ' ').title()}")

# ── TAB 5: Conflict Fingerprints ─────────────────────────────────────────
    with tab5:
        st.markdown('<div class="section-header">Why do papers disagree?</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Contradictions diagnosed across 4 dimensions: methodology gap, population difference, funding bias, and temporal shift.</div>', unsafe_allow_html=True)

        try:
            from researchos.graph.query_graph import get_contradictions
            contradictions = get_contradictions(min_dimensions=2)

            if not contradictions:
                contradictions = get_contradictions(min_dimensions=1)

            if not contradictions:
                st.info("No contradictions detected yet. Run more topics to build the graph.")
            else:
                st.metric("Total contradictions detected", len(contradictions))
                st.markdown("---")

                # show top 20 most interesting
                for i, c in enumerate(contradictions[:20], 1):
                    dims = c.get("dimension_count", 0)
                    color = "🔴" if dims >= 3 else "🟠" if dims >= 2 else "🟡"

                    with st.expander(f"{color} Contradiction #{i} — {dims} dimension(s) — {c.get('year_a')} vs {c.get('year_b')}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown(f"**Paper A ({c.get('year_a')})**")
                            st.markdown(f"*{c.get('paper_a', 'Unknown')}*")
                            st.markdown(f"Method: `{c.get('method_a')}` | Score: `{c.get('score_a')}`")

                        with col2:
                            st.markdown(f"**Paper B ({c.get('year_b')})**")
                            st.markdown(f"*{c.get('paper_b', 'Unknown')}*")
                            st.markdown(f"Method: `{c.get('method_b')}` | Score: `{c.get('score_b')}`")

                        st.markdown("**Why they disagree:**")
                        for reason in (c.get("reasons") or []):
                            st.markdown(f"- {reason}")

                        dims_active = []
                        if c.get("methodology_gap"):
                            dims_active.append("⚗️ Methodology gap")
                        if c.get("population_difference"):
                            dims_active.append("👥 Population difference")
                        if c.get("funding_bias"):
                            dims_active.append("💰 Funding bias")
                        if c.get("temporal_shift"):
                            dims_active.append("📅 Temporal shift")

                        if dims_active:
                            st.markdown("**Active dimensions:** " + " | ".join(dims_active))

        except Exception as e:
            st.warning(f"Knowledge graph not available: {e}")
            st.info("The conflict fingerprinting engine requires Neo4j to be connected.")