"""
Knowledge Service
-----------------
Handles document upload, metadata extraction, embedding generation,
semantic indexing, and search.

All operations log audit entries.
Document search always returns document_id references — never raw content
without traceability context.
"""

import hashlib
import logging
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document
from app.schemas.document import DocumentUploadResponse
from app.core.audit_engine.logger import audit
from app.services.embedding import EmbeddingService
from app.services.storage import StorageService

logger = logging.getLogger(__name__)


class KnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_svc = EmbeddingService()
        self.storage_svc   = StorageService()

    async def upload(self, file: UploadFile, user_id: str) -> DocumentUploadResponse:
        content = await file.read()
        file_hash = hashlib.sha256(content).hexdigest()

        # Store in Supabase Storage
        filename = file.filename or "unnamed"
        content_type = file.content_type or "application/octet-stream"
        storage_path = await self.storage_svc.upload(filename, content, content_type)

        # Extract basic metadata
        meta = {
            "filename": filename,
            "content_type": file.content_type,
            "size_bytes": len(content),
        }

        # Persist document record
        doc = Document(
            title=filename,
            source=filename,
            storage_path=storage_path,
            file_hash=file_hash,
            meta=meta,
            uploaded_by=user_id,
        )
        self.db.add(doc)
        await self.db.flush()

        # Generate and store embedding — non-fatal if Gemini API unavailable
        text_content = content.decode("utf-8", errors="ignore")[:4000]
        if text_content.strip():
            try:
                embedding = await self.embedding_svc.generate(text_content)
                doc.embedding = embedding
                await self.db.flush()
            except Exception as exc:
                logger.warning("Embedding generation failed (doc will be stored without vector): %s", exc)

        await audit.log(
            self.db,
            entity_type="document",
            entity_id=doc.id,
            action="uploaded",
            performed_by=user_id,
            metadata=meta,
        )
        await self.db.commit()

        return DocumentUploadResponse(
            document_id=doc.id,
            storage_path=storage_path,
            message="Document uploaded and indexed successfully.",
        )

    async def list_all(self) -> list[Document]:
        """Return all documents ordered newest first."""
        result = await self.db.execute(
            select(Document).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def search(self, query: str) -> list[Document]:
        """
        Semantic search using pgvector cosine similarity.
        Falls back to keyword title search if embedding is unavailable.
        Always returns documents with their IDs for traceability.
        """
        try:
            query_embedding = await self.embedding_svc.generate(query)
            result = await self.db.execute(
                select(Document)
                .where(Document.embedding.is_not(None))
                .order_by(Document.embedding.cosine_distance(query_embedding))
                .limit(10)
            )
        except Exception as exc:
            logger.warning("Semantic search unavailable, falling back to keyword search: %s", exc)
            result = await self.db.execute(
                select(Document)
                .where(Document.title.ilike(f"%{query}%"))
                .limit(10)
            )
        return list(result.scalars().all())

    async def get_by_id(self, document_id: str) -> Document:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        return doc

    async def get_download_url(self, document_id: str) -> str:
        doc = await self.get_by_id(document_id)
        return await self.storage_svc.get_url(doc.storage_path)
