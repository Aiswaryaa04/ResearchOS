import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=_get_env("ANTHROPIC_API_KEY"))

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
    """Send a paper to Claude and get back structured extraction."""
    if not abstract:
        return None

    prompt = EXTRACTION_PROMPT.format(title=title, abstract=abstract)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ],
            system=SYSTEM_PROMPT,
        )

        raw = message.content[0].text.strip()

        # strip markdown code fences if Claude adds them despite instructions
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


if __name__ == "__main__":
    title = "Metformin's role in lowering colorectal cancer risk among individuals with diabetes"
    abstract = """Background: Metformin, utilized to manage hyperglycemia, has been linked to a 
    reduced risk of colorectal cancer (CRC) among individuals with diabetes. We examined this 
    association in a cohort of 12,000 diabetic patients followed for 10 years. 
    Results: Metformin users showed a 23% reduced risk of CRC compared to non-users (HR 0.77, 
    95% CI 0.65-0.91). The association was stronger in patients with longer duration of use.
    Funding: Supported by NIH grant R01CA123456."""

    result = extract_paper(title, abstract)
    print(json.dumps(result, indent=2))