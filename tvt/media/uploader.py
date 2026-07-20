"""Upload workflow result JSON to Azure Blob Storage."""

import logging
import os

from dotenv import load_dotenv

from tvt.azure import blob_store

load_dotenv()

STORAGE_CONTAINER = os.environ["STORAGE_CONTAINER"]

logger = logging.getLogger(__name__)


def upload_json(blob_name, json_text):
    """Upload a JSON string to the container as blob_name and return its URL."""
    logger.info("Uploading %d bytes to %s/%s", len(json_text), STORAGE_CONTAINER, blob_name)
    return blob_store.upload_blob(
        STORAGE_CONTAINER, blob_name, json_text, content_type="application/json"
    )
