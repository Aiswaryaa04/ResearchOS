import os
from neo4j import GraphDatabase
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


def get_driver():
    return GraphDatabase.driver(
        _get_env("NEO4J_URI"),
        auth=(_get_env("NEO4J_USERNAME"), _get_env("NEO4J_PASSWORD"))
    )