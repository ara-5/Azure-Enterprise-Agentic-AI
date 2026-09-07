
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)
    filter_expr: str | None = None


class Citation(BaseModel):
    source: str | None = None
    document_id: str | None = None
    score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieval_score: float


class AgentChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)


class AgentChatResponse(BaseModel):
    answer: str


class IngestTextRequest(BaseModel):
    document_id: str
    source: str
    text: str


class IngestResponse(BaseModel):
    document_id: str
    chunks_indexed: int


class CostSummaryResponse(BaseModel):
    month_to_date_usd: float
    monthly_budget_usd: float
    percent_of_budget: float


class HealthResponse(BaseModel):
    status: str
    app_env: str
    demo_mode: bool
