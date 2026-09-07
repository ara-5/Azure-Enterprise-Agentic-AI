from fastapi import APIRouter, Depends

from app.agents.demo_orchestrator import run_agent_turn_demo
from app.agents.orchestrator import run_agent_turn
from app.auth.entra import CurrentUser, get_current_user
from app.config import get_settings
from app.models.schemas import AgentChatRequest, AgentChatResponse, ChatRequest, ChatResponse
from app.rag.demo import answer_question_demo
from app.rag.pipeline import answer_question

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/completions", response_model=ChatResponse)
async def chat_completions(body: ChatRequest, user: CurrentUser = Depends(get_current_user)) -> ChatResponse:
    """Plain RAG: always retrieves, then answers grounded in the top-k chunks.

    DEMO_MODE=true (the default) serves this from app/rag/demo.py -- local
    keyword retrieval over the bundled sample docs, no Azure OpenAI/AI Search
    required. Set DEMO_MODE=false to use the real pipeline (app/rag/pipeline.py).
    """
    if get_settings().demo_mode:
        result = answer_question_demo(body.question, top_k=body.top_k)
    else:
        result = await answer_question(
            body.question,
            route="/api/chat/completions",
            user_id=user.object_id,
            top_k=body.top_k,
            filter_expr=body.filter_expr,
        )
    return ChatResponse(answer=result.answer, citations=result.citations, retrieval_score=result.retrieval_score)


@router.post("/agent", response_model=AgentChatResponse)
async def agent_chat(body: AgentChatRequest, user: CurrentUser = Depends(get_current_user)) -> AgentChatResponse:
    """Agentic path: the model decides whether/which tools to call (Semantic Kernel).

    DEMO_MODE=true serves this from app/agents/demo_orchestrator.py -- rule-based
    tool routing instead of model-chosen, so the tool-calling UX is still visible
    with no Azure OpenAI required.
    """
    if get_settings().demo_mode:
        answer = await run_agent_turn_demo(body.question)
    else:
        answer = await run_agent_turn(body.question, user_id=user.object_id)
    return AgentChatResponse(answer=answer)
