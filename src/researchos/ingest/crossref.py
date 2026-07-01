import time
import requests


def get_crossref_metadata(doi: str) -> dict | None:
    """
    Fetch funding and publisher metadata for a paper by DOI from CrossRef.
    Returns a dict with funder info or None if not found.
    """
    if not doi:
        return None

    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        # CrossRef asks you to identify yourself in the User-Agent
        "User-Agent": "ResearchOS/1.0 (mailto:avelu3@uic.edu)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json().get("message", {})

        funders = data.get("funder", [])
        funder_names = [f.get("name") for f in funders if f.get("name")]

        # classify funding type from funder names
        industry_keywords = [
            "pharma", "inc.", "ltd", "corporation", "gmbh",
            "pfizer", "roche", "novartis", "astrazeneca", "merck",
            "bayer", "sanofi", "abbvie", "johnson", "lilly",
        ]
        public_keywords = [
            "national", "nih", "nsf", "wellcome", "medical research council",
            "government", "ministry", "department", "university", "cancer research uk",
            "european", "horizon", "charity", "foundation",
        ]

        funding_type = "unknown"
        if funder_names:
            names_lower = " ".join(funder_names).lower()
            is_industry = any(k in names_lower for k in industry_keywords)
            is_public = any(k in names_lower for k in public_keywords)
            if is_industry and is_public:
                funding_type = "mixed"
            elif is_industry:
                funding_type = "industry"
            elif is_public:
                funding_type = "public"
            else:
                funding_type = "none_declared"

        return {
            "funder_names": funder_names,
            "funding_type": funding_type,
            "publisher": data.get("publisher"),
            "is_retracted": data.get("update-to") is not None,
        }

    except Exception as e:
        print(f"  CrossRef error for DOI {doi}: {e}")
        return None


if __name__ == "__main__":
    # test with a known DOI
    result = get_crossref_metadata("10.1056/NEJMoa2034577")
    print(result)