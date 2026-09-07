"""DEMO_MODE is the default, so these hit the real /api/chat endpoints
end-to-end through TestClient with no Azure mocking required -- the local
keyword-retrieval fallback (app/rag/demo.py, app/agents/demo_orchestrator.py)
makes that possible."""
from fastapi.testclient import TestClient

from app.main import app
from app.rag.demo import answer_question_demo, search_demo

client = TestClient(app)


def test_search_demo_finds_relevant_chunk_for_pto_question():
    hits = search_demo("How many days of PTO do employees get?")
    assert hits
    assert any("hr-handbook" in h["source"] for h in hits)


def test_search_demo_returns_nothing_for_unrelated_query():
    hits = search_demo("zzz qqq nonexistent gibberish xyzzy")
    assert hits == []


def test_answer_question_demo_cites_source_and_flags_demo_mode():
    result = answer_question_demo("What is the remote work policy?")
    assert "Demo mode" in result.answer
    assert result.citations
    assert result.citations[0]["source"] == "hr-handbook.md"


def test_chat_completions_endpoint_uses_demo_mode_by_default():
    response = client.post("/api/chat/completions", json={"question": "What is the PTO policy?"})
    assert response.status_code == 200
    body = response.json()
    assert "Demo mode" in body["answer"]
    assert body["citations"]


def test_agent_chat_endpoint_routes_cost_questions_to_cost_tool():
    response = client.post("/api/chat/agent", json={"question": "What is our current AI spend this month?"})
    assert response.status_code == 200
    assert "CostLookup" in response.json()["answer"]


def test_agent_chat_endpoint_routes_knowledge_questions_to_search_tool():
    response = client.post("/api/chat/agent", json={"question": "What is the incident response SLA?"})
    assert response.status_code == 200
    assert "KnowledgeBase" in response.json()["answer"]
