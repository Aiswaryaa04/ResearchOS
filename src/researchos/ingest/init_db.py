from researchos.db import engine, Base
from researchos.ingest.models import Paper

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    print("Tables created.")