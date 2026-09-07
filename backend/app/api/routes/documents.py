from fastapi import APIRouter, Depends, UploadFile

from app.auth.entra import CurrentUser, get_current_user, require_role
from app.config import get_settings
from app.ingestion.indexer import ingest_document
from app.models.schemas import IngestResponse, IngestTextRequest
from app.services import blob_storage

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/ingest-text", response_model=IngestResponse)
async def ingest_text(body: IngestTextRequest, user: CurrentUser = Depends(require_role("ingest"))) -> IngestResponse:
    """Ingest raw text directly (demo/testing path)."""
    count = await ingest_document(document_id=body.document_id, source=body.source, text=body.text)
    return IngestResponse(document_id=body.document_id, chunks_indexed=count)


@router.post("/upload", response_model=IngestResponse)
async def upload_and_ingest(file: UploadFile, user: CurrentUser = Depends(require_role("ingest"))) -> IngestResponse:
    """Upload a text/markdown file to Blob Storage and index it in the same call."""
    settings = get_settings()
    content = await file.read()
    await blob_storage.upload_document(settings.azure_storage_container_documents, file.filename, content, file.content_type or "text/plain")
    count = await ingest_document(document_id=file.filename, source=file.filename, text=content.decode("utf-8", errors="ignore"))
    return IngestResponse(document_id=file.filename, chunks_indexed=count)


@router.get("/", response_model=list[str])
async def list_documents(user: CurrentUser = Depends(get_current_user)) -> list[str]:
    settings = get_settings()
    return [name async for name in blob_storage.list_documents(settings.azure_storage_container_documents)]
