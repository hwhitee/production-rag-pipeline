from uuid import UUID

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    document_id: UUID
    filename: str
    chunks_created: int


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class Source(BaseModel):
    document_id: UUID
    filename: str
    content: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
