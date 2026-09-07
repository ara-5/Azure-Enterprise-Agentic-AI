from app.ingestion.chunking import chunk_text, to_index_documents


def test_chunk_text_single_paragraph_stays_one_chunk():
    text = "This is a short paragraph well under the chunk size."
    chunks = chunk_text(text, chunk_size_tokens=400)
    assert chunks == [text]


def test_chunk_text_splits_long_content():
    paragraph = "word " * 100
    text = "\n\n".join([paragraph] * 10)  # ~1000 tokens total
    chunks = chunk_text(text, chunk_size_tokens=300, overlap_tokens=30)
    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_to_index_documents_produces_required_fields():
    docs = to_index_documents(document_id="doc-1", source="doc-1.md", text="Hello world.\n\nMore content here.", last_updated_iso="")
    assert len(docs) >= 1
    for doc in docs:
        assert doc["document_id"] == "doc-1"
        assert doc["source"] == "doc-1.md"
        assert doc["id"].startswith("doc-1-")
        assert "content" in doc
