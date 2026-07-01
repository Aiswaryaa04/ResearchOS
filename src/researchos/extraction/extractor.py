import os
import json
from dotenv import load_dotenv

load_dotenv()


def _get_env(key: str) -> str:
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, "")


def get_client():
    import anthropic
    return anthropic.Anthropic(api_key=_get_env("ANTHROPIC_API_KEY"))


SYSTEM_PROMPT = """You are a scientific literature analyst. 
Your job is to extract structured information from paper abstracts.
Always respond with valid JSON only. No explanation, no markdown, just the JSON object."""

EXTRACTION_PROMPT = """Extract the following fields from this paper abstract.
Return ONLY a JSON object with these exact keys:

- main_claim: one sentence summarizing the paper's primary finding (string)
- methodology: one of exactly these values: "meta_analysis", "rct", "cohort_study", "case_control", "cross_sectional", "case_study", "review", "other"
- sample_size: number of participants/subjects as an integer, or null if not mentioned
- population: description of the study population (string, e.g. "adult diabetic patients in the US")
- funding_source: who funded the study, or null if not mentioned (string)
- funding_type: one of exactly these values: "industry", "public", "mixed", "none_declared", "unknown"
- direction: one of exactly these values: "protective", "harmful", "neutral", "inconclusive"
- outcome: the specific health outcome being measured (string, e.g. "colorectal cancer incidence")

Paper title: {title}
Abstract: {abstract}

JSON response:"""


def extract_paper(title: str, abstract: str) -> dict | None:
    if not abstract:
        return None

    prompt = EXTRACTION_PROMPT.format(title=title, abstract=abstract)

    try:
        client = get_client()
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
        )

        raw = message.content[0].text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)

    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  API error: {e}")
        return None