import hashlib
import io
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pypdf import PdfReader
from sqlalchemy import select

from src.api.dependencies import DbSession, TenantId
from src.api.schemas import ChatRequest, ChatResponse, IngestResponse, Source
from src.core.config import settings
from src.db.models import Document, DocumentChunk
from src.ingestion.chunker import chunk_text
from src.llm import LLMClient

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_text(filename: str, content: bytes) -> str:
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="Upload a UTF-8 text or PDF file") from exc


@router.post("/documents", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    tenant_id: TenantId,
    db: DbSession,
    upload: Annotated[UploadFile, File()],
) -> IngestResponse:
    filename = upload.filename or "upload.txt"
    if not filename.lower().endswith((".txt", ".md", ".pdf")):
        raise HTTPException(status_code=415, detail="Supported file types: .txt, .md, .pdf")
    content = await upload.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds configured upload limit")
    text = _extract_text(filename, content).strip()
    chunks = chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Document contains no extractable text")
    if len(chunks) > settings.max_chunks_per_document:
        raise HTTPException(status_code=413, detail="Document exceeds configured chunk limit")
    try:
        embeddings = await LLMClient().embed(chunks)
        document = Document(
            tenant_id=tenant_id,
            filename=filename[:255],
            sha256=hashlib.sha256(content).hexdigest(),
        )
        db.add(document)
        await db.flush()
        db.add_all(
            [
                DocumentChunk(
                    document_id=document.id,
                    tenant_id=tenant_id,
                    content=chunk,
                    embedding=embedding,
                )
                for chunk, embedding in zip(chunks, embeddings, strict=True)
            ]
        )
        await db.commit()
        return IngestResponse(
            document_id=document.id, filename=document.filename, chunks_created=len(chunks)
        )
    except Exception:
        await db.rollback()
        logger.exception("Document ingestion failed for tenant %s", tenant_id)
        raise HTTPException(status_code=502, detail="Document processing failed") from None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, tenant_id: TenantId, db: DbSession) -> ChatResponse:
    try:
        client = LLMClient()
        query_embedding = (await client.embed([request.query]))[0]
        top_k = request.top_k or settings.retrieval_top_k
        statement = (
            select(DocumentChunk, Document.filename)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(DocumentChunk.tenant_id == tenant_id, Document.tenant_id == tenant_id)
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        rows = (await db.execute(statement)).all()
        sources = [
            Source(
                document_id=chunk.document_id,
                filename=filename,
                content=chunk.content,
                score=1.0 / (rank + 1),
            )
            for rank, (chunk, filename) in enumerate(rows)
        ]
        answer = (
            await client.answer(request.query, [source.content for source in sources])
            if sources
            else "No relevant documents were found."
        )
        return ChatResponse(answer=answer, sources=sources)
    except Exception as exc:
        logger.exception("Chat request failed for tenant %s", tenant_id)
        raise HTTPException(status_code=502, detail="Retrieval or generation failed") from exc


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID, tenant_id: TenantId, db: DbSession) -> None:
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id)
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await db.delete(document)
    await db.commit()
