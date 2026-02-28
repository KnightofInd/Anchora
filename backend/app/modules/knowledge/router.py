from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.document import DocumentRead, DocumentUploadResponse
from app.modules.knowledge.service import KnowledgeService

router = APIRouter()


@router.get("/", response_model=list[DocumentRead])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all uploaded documents, newest first."""
    return await KnowledgeService(db).list_all()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await KnowledgeService(db).upload(file, current_user["user_id"])


@router.get("/search", response_model=list[DocumentRead])
async def search_documents(
    q: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await KnowledgeService(db).search(q)


@router.get("/{document_id}/download")
async def get_document_url(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Returns a short-lived signed URL for direct file download."""
    url = await KnowledgeService(db).get_download_url(document_id)
    return {"url": url}


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await KnowledgeService(db).get_by_id(document_id)
