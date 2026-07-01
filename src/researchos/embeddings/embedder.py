import os
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 3072


def _get_env(key: str) -> str:
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, "")


def get_client():
    from google import genai
    return genai.Client(api_key=_get_env("GEMINI_API_KEY"))


def embed_text(text: str) -> list[float]:
    from google.genai import types
    client = get_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return response.embeddings[0].values


def embed_query(query: str) -> list[float]:
    from google.genai import types
    client = get_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return response.embeddings[0].values


if __name__ == "__main__":
    vec = embed_text("Metformin reduces cancer risk in diabetic patients.")
    print(f"Embedding dimension: {len(vec)}")
    print(f"First 5 values: {vec[:5]}")