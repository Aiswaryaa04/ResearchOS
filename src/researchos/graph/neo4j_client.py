import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

def get_driver():
    return GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
    )