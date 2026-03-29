"""
Knowledge Service
-----------------
Handles document upload, metadata extraction, embedding generation,
chunk indexing, and hybrid search.

All operations log audit entries.
Document search always returns document_id references — never raw content
without traceability context.
"""

import hashlib
import logging
import re
from collections import defaultdict
from collections.abc import Sequence

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.engine import Row
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.models.document import Document
from app.models.knowledge_chunk import KnowledgeChunk
from app.schemas.document import DocumentUploadResponse
from app.core.audit_engine.logger import audit
from app.services.embedding import EmbeddingService
from app.services.storage import StorageService
from app.config.settings import settings

logger = logging.getLogger(__name__)
_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


class KnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_svc = EmbeddingService()
        self.storage_svc   = StorageService()

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(_TOKEN_RE.findall((text or "").lower()))

    def _keyword_overlap_score(self, query: str, chunk_text: str) -> float:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return 0.0
        chunk_tokens = self._tokenize(chunk_text)
        if not chunk_tokens:
            return 0.0
        return len(query_tokens & chunk_tokens) / len(query_tokens)

    def _split_text_into_chunks(self, text: str) -> list[str]:
        normalized = " ".join((text or "").split())
        if not normalized:
            return []

        size = max(200, settings.KNOWLEDGE_CHUNK_SIZE_CHARS)
        overlap = max(0, min(settings.KNOWLEDGE_CHUNK_OVERLAP_CHARS, size - 1))
        step = max(1, size - overlap)

        chunks: list[str] = []
        start = 0
        while start < len(normalized) and len(chunks) < settings.KNOWLEDGE_MAX_CHUNKS_PER_DOCUMENT:
            chunk = normalized[start : start + size].strip()
            if chunk:
                chunks.append(chunk)
            start += step
        return chunks

    async def _rank_documents_from_chunk_rows(
        self,
        *,
        query: str,
        rows: Sequence[Row[tuple[KnowledgeChunk, Document, float]]],
        keyword_weight: float,
        limit: int,
    ) -> list[Document]:
        if not rows:
            return []

        weight = max(0.0, min(1.0, keyword_weight))
        per_doc: dict[str, dict] = defaultdict(lambda: {
            "doc": None,
            "best_score": 0.0,
            "chunk_hits": set(),
        })

        for row in rows:
            chunk = row[0]
            doc = row[1]
            distance = row[2]
            vector_score = 1.0 / (1.0 + max(float(distance), 0.0))
            keyword_score = self._keyword_overlap_score(query, chunk.chunk_text)
            combined = (1.0 - weight) * vector_score + (weight * keyword_score)

            key = str(doc.id)
            bucket = per_doc[key]
            bucket["doc"] = doc
            bucket["best_score"] = max(bucket["best_score"], combined)
            bucket["chunk_hits"].add(chunk.chunk_index)

        ranked: list[tuple[float, Document]] = []
        for bucket in per_doc.values():
            diversity_bonus = min(len(bucket["chunk_hits"]), 3) * 0.01
            ranked.append((bucket["best_score"] + diversity_bonus, bucket["doc"]))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [doc for _, doc in ranked[:limit]]

    async def retrieve_documents(self, query: str, *, limit: int | None = None) -> tuple[list[Document], str]:
        """
        Retrieve documents from chunk-level evidence with hybrid reranking.
        Falls back from semantic chunks -> keyword chunks -> title match.
        """
        top_docs = limit or settings.RETRIEVAL_TOP_K_DOCUMENTS
        clean_query = (query or "").strip()
        if not clean_query:
            return [], "empty_query"

        try:
            query_embedding = await self.embedding_svc.generate(clean_query)
            distance = KnowledgeChunk.embedding.cosine_distance(query_embedding).label("distance")
            semantic_result = await self.db.execute(
                select(KnowledgeChunk, Document, distance)
                .join(Document, Document.id == KnowledgeChunk.document_id)
                .where(KnowledgeChunk.embedding.is_not(None))
                .order_by(distance.asc())
                .limit(settings.RETRIEVAL_TOP_K_CHUNKS)
            )
            semantic_rows = list(semantic_result.all())
            docs = await self._rank_documents_from_chunk_rows(
                query=clean_query,
                rows=semantic_rows,
                keyword_weight=settings.RETRIEVAL_KEYWORD_WEIGHT,
                limit=top_docs,
            )
            if docs:
                return docs, "semantic_hybrid_chunks"
        except Exception as exc:
            logger.warning("Semantic chunk retrieval unavailable, falling back to keyword retrieval: %s", exc)

        try:
            ts_query = func.plainto_tsquery("english", clean_query)
            ts_vector = func.to_tsvector("english", KnowledgeChunk.chunk_text)
            rank = func.ts_rank_cd(ts_vector, ts_query).label("rank")
            keyword_result = await self.db.execute(
                select(KnowledgeChunk, Document, rank)
                .join(Document, Document.id == KnowledgeChunk.document_id)
                .where(ts_vector.op("@@")(ts_query))
                .order_by(rank.desc())
                .limit(settings.RETRIEVAL_TOP_K_CHUNKS)
            )
            keyword_rows = list(keyword_result.all())
            docs = await self._rank_documents_from_chunk_rows(
                query=clean_query,
                rows=keyword_rows,
                keyword_weight=1.0,
                limit=top_docs,
            )
            if docs:
                return docs, "keyword_chunks"
        except Exception as exc:
            logger.warning("Keyword tsvector retrieval failed, falling back to ILIKE: %s", exc)

        fallback_result = await self.db.execute(
            select(Document)
            .outerjoin(KnowledgeChunk, KnowledgeChunk.document_id == Document.id)
            .where(
                or_(
                    Document.title.ilike(f"%{clean_query}%"),
                    KnowledgeChunk.chunk_text.ilike(f"%{clean_query}%"),
                )
            )
            .limit(top_docs)
        )
        docs = list(fallback_result.scalars().unique().all())
        return docs, "fallback_keyword"

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

        # Generate chunk embeddings — non-fatal if Gemini API unavailable
        text_content = content.decode("utf-8", errors="ignore")
        if text_content.strip():
            chunks = self._split_text_into_chunks(text_content)
            embedded_count = 0
            for index, chunk_text in enumerate(chunks):
                embedding = None
                try:
                    embedding = await self.embedding_svc.generate(chunk_text)
                    embedded_count += 1
                    if doc.embedding is None:
                        # Keep document-level embedding for backward compatibility.
                        doc.embedding = embedding
                except Exception as exc:
                    logger.warning(
                        "Chunk embedding failed for %s[%s] (continuing): %s",
                        filename,
                        index,
                        exc,
                    )

                self.db.add(
                    KnowledgeChunk(
                        document_id=doc.id,
                        chunk_index=index,
                        chunk_text=chunk_text,
                        embedding=embedding,
                    )
                )

            meta["chunk_count"] = len(chunks)
            meta["embedded_chunk_count"] = embedded_count
            doc.meta = meta
            await self.db.flush()

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

    async def list_all(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> list[Document]:
        """Return documents with standardized pagination and sorting."""
        sort_columns = {
            "created_at": Document.created_at,
            "title": Document.title,
            "version": Document.version,
        }
        column = sort_columns.get(sort_by, Document.created_at)
        order_expr = column.asc() if sort_order == "asc" else column.desc()

        result = await self.db.execute(
            select(Document)
            .order_by(order_expr)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def search(self, query: str) -> list[Document]:
        """
        Chunk-first hybrid retrieval (vector + keyword).
        Returns document IDs for full traceability.
        """
        docs, _mode = await self.retrieve_documents(query, limit=settings.RETRIEVAL_TOP_K_DOCUMENTS)
        return docs

    async def get_by_id(self, document_id: str) -> Document:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
        return doc

    async def get_download_url(self, document_id: str) -> str:
        doc = await self.get_by_id(document_id)
        return await self.storage_svc.get_url(doc.storage_path)
