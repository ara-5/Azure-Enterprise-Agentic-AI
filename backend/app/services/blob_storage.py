"""Azure Blob Storage access -- document ingestion source and the durable
sink for cost-tracking exports. Auth is Managed Identity in Azure
(Storage Blob Data Contributor role, granted in infra/modules/identity.bicep);
locally it falls back to a connection string if provided, else the same
DefaultAzureCredential chain as everything else.
"""
import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from functools import lru_cache

from azure.storage.blob.aio import BlobServiceClient

from app.config import get_settings
from app.core.azure_credential import get_credential

logger = logging.getLogger(__name__)


@lru_cache
def _client() -> BlobServiceClient:
    settings = get_settings()
    if settings.azure_storage_connection_string:
        return BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)
    return BlobServiceClient(account_url=settings.azure_storage_account_url, credential=get_credential())


async def upload_document(container: str, blob_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    client = _client()
    container_client = client.get_container_client(container)
    if not await container_client.exists():
        await container_client.create_container()
    blob_client = container_client.get_blob_client(blob_name)
    await blob_client.upload_blob(data, overwrite=True, content_type=content_type)
    logger.info("Uploaded blob %s/%s (%d bytes)", container, blob_name, len(data))
    return blob_client.url


async def list_documents(container: str) -> AsyncIterator[str]:
    client = _client()
    container_client = client.get_container_client(container)
    if not await container_client.exists():
        return
    async for blob in container_client.list_blobs():
        yield blob.name


async def download_document(container: str, blob_name: str) -> bytes:
    client = _client()
    blob_client = client.get_container_client(container).get_blob_client(blob_name)
    stream = await blob_client.download_blob()
    return await stream.readall()


async def append_jsonl_record(container: str, blob_name_prefix: str, record: dict) -> None:
    """Append-friendly cost/usage log: one JSON object per line, partitioned by day."""
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    blob_name = f"{blob_name_prefix}/{date_str}.jsonl"
    client = _client()
    container_client = client.get_container_client(container)
    if not await container_client.exists():
        await container_client.create_container()
    append_client = container_client.get_blob_client(blob_name)

    line = (json.dumps(record) + "\n").encode("utf-8")
    try:
        if not await append_client.exists():
            await append_client.upload_blob(b"", blob_type="AppendBlob")
        await append_client.append_block(line)
    except Exception:  # pragma: no cover - append blobs need the right blob type from creation
        logger.exception("Failed to append cost record to %s", blob_name)
