from sqlalchemy import text
from researchos.db import engine
from researchos.embeddings.embedder import EMBEDDING_DIM

if __name__ == "__main__":
    with engine.connect() as conn:
        conn.execute(text(
            f"ALTER TABLE papers ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIM});"
        ))
        conn.commit()
    print(f"Added embedding column (vector({EMBEDDING_DIM})) to papers table.")