from sqlalchemy import text
from researchos.db import engine

if __name__ == "__main__":
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE papers
                ADD COLUMN IF NOT EXISTS main_claim TEXT,
                ADD COLUMN IF NOT EXISTS methodology VARCHAR(50),
                ADD COLUMN IF NOT EXISTS sample_size INTEGER,
                ADD COLUMN IF NOT EXISTS population TEXT,
                ADD COLUMN IF NOT EXISTS funding_source TEXT,
                ADD COLUMN IF NOT EXISTS funding_type VARCHAR(20),
                ADD COLUMN IF NOT EXISTS direction VARCHAR(20),
                ADD COLUMN IF NOT EXISTS outcome TEXT,
                ADD COLUMN IF NOT EXISTS extraction_done BOOLEAN DEFAULT FALSE;
        """))
        conn.commit()
    print("Extraction columns added.")