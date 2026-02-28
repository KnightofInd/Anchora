from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector

from app.core.database import Base
from app.config.settings import settings

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.decision import DecisionReference


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str]     = mapped_column(String(512), nullable=False)
    version: Mapped[int]   = mapped_column(Integer, default=1, nullable=False)
    source: Mapped[str]    = mapped_column(String(1024), nullable=True)   # original filename / URL
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=True)  # Supabase Storage path
    file_hash: Mapped[str] = mapped_column(String(64), nullable=True)     # SHA-256 for integrity
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    # Traceability: which user uploaded
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    uploader: Mapped["User"] = relationship("User", back_populates="documents")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Vector embedding for semantic search (pgvector)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(settings.EMBEDDING_DIMENSIONS), nullable=True
    )

    # Reverse relationship to decision references
    decision_references: Mapped[list["DecisionReference"]] = relationship(
        "DecisionReference", back_populates="document"
    )

    def __repr__(self) -> str:
        return f"<Document {self.title} v{self.version}>"
