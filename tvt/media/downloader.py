"""Stage videos from URLs into the private videos blob container, keeping workers stateless."""

import logging
import os
import uuid
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from tvt.azure import blob_store

load_dotenv()

VIDEO_CONTAINER = os.environ["STORAGE_VIDEO_CONTAINER"]

logger = logging.getLogger(__name__)


def download_video(url):
    """Copy the video at url into the videos container; return its blob name."""
    basename = os.path.basename(urlparse(url).path) or "video"
    blob_name = f"{uuid.uuid4().hex}-{basename}"

    logger.info("Downloading %s to blob %s/%s", url, VIDEO_CONTAINER, blob_name)
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        blob_store.upload_blob(VIDEO_CONTAINER, blob_name, response.raw)

    logger.info("Downloaded %s: %d bytes", url, video_size(blob_name))
    return blob_name


def open_video(blob_name):
    """Return a readable stream over a staged video's content."""
    return blob_store.open_blob(VIDEO_CONTAINER, blob_name)


def video_size(blob_name):
    """Return a staged video's size in bytes."""
    return blob_store.open_blob(VIDEO_CONTAINER, blob_name).properties.size
