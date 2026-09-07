"""Uploads scripts/sample_docs/*.md to Blob Storage and indexes them into
Azure AI Search, so there's real, queryable content to demo the chat and
agent endpoints against immediately after `azd up` / a fresh deploy.

Usage:
    python scripts/seed_sample_data.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402
from app.ingestion.indexer import ingest_document  # noqa: E402
from app.services import blob_storage  # noqa: E402

# Lives under backend/app/data so it ships inside the Docker image and can
# double as the corpus for local DEMO_MODE retrieval (app/rag/demo.py) --
# one set of sample content for both the live-Azure seed script and the
# zero-Azure-cost demo path.
SAMPLE_DOCS_DIR = Path(__file__).resolve().parents[1] / "backend" / "app" / "data" / "sample_docs"


async def main() -> None:
    settings = get_settings()
    for path in sorted(SAMPLE_DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        print(f"Uploading {path.name} to blob storage...")
        await blob_storage.upload_document(settings.azure_storage_container_documents, path.name, text.encode("utf-8"), "text/markdown")

        print(f"Indexing {path.name}...")
        count = await ingest_document(document_id=path.stem, source=path.name, text=text)
        print(f"  -> {count} chunks indexed.")

    print("Done. Try: POST /api/chat/completions {\"question\": \"What is the PTO policy?\"}")


if __name__ == "__main__":
    asyncio.run(main())
