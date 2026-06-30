from sqlalchemy import text
from researchos.db import engine

if __name__ == "__main__":
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE papers
                ADD COLUMN IF NOT EXISTS evidence_score FLOAT,
                ADD COLUMN IF NOT EXISTS evidence_tier VARCHAR(20),
                ADD COLUMN IF NOT EXISTS scoring_done BOOLEAN DEFAULT FALSE;
        """))
        conn.commit()
    print("Scoring columns added.")