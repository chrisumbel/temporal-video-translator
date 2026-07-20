"""Shared Azure Blob Storage access for the tvttranslations account."""

import logging
import os

from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv

from tvt.azure import entra

load_dotenv()

STORAGE_ACCOUNT_NAME = os.environ["STORAGE_ACCOUNT_NAME"]

logger = logging.getLogger(__name__)


def _blob_client(container, blob_name):
    account_url = f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
    service = BlobServiceClient(account_url, credential=entra.credential())
    return service.get_blob_client(container=container, blob=blob_name)


def upload_blob(container, blob_name, data, content_type=None):
    """Upload data (bytes, str, or readable stream) as the blob; return its URL."""
    blob = _blob_client(container, blob_name)
    settings = ContentSettings(content_type=content_type) if content_type else None
    blob.upload_blob(data, overwrite=True, content_settings=settings)
    logger.info("Uploaded blob %s/%s", container, blob_name)
    return blob.url


def open_blob(container, blob_name):
    """Return a readable stream over the blob's content."""
    return _blob_client(container, blob_name).download_blob()
