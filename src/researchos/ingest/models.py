import uuid
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, JSON
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from researchos.db import Base


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False)
    external_id = Column(String, nullable=False)
    doi = Column(String, nullable=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text, nullable=True)
    year = Column(Integer, nullable=True)
    venue = Column(String, nullable=True)
    is_preprint = Column(Boolean, default=False)
    authors = Column(JSON, nullable=True)
    raw_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    embedding = Column(Vector(3072), nullable=True)