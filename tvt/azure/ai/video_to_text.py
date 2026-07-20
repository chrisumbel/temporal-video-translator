"""Extract speech from a video and transcribe it using Azure AI Video Indexer."""

import logging
import os
import time

import requests
from dotenv import load_dotenv

from tvt.azure import entra

logger = logging.getLogger(__name__)

load_dotenv()

SUBSCRIPTION_ID = os.environ["AZURE_SUBSCRIPTION_ID"]
RESOURCE_GROUP = os.environ["AZURE_RESOURCE_GROUP"]
ACCOUNT_NAME = os.environ["VIDEO_INDEXER_ACCOUNT_NAME"]
ACCOUNT_ID = os.environ["VIDEO_INDEXER_ACCOUNT_ID"]
LOCATION = os.environ["AZURE_LOCATION"]

ARM_API_VERSION = "2024-01-01"
API_BASE = f"https://api.videoindexer.ai/{LOCATION}/Accounts/{ACCOUNT_ID}"

POLL_INTERVAL_SECONDS = 15


def _get_access_token():
    """Get a Video Indexer access token via the ARM generateAccessToken API."""
    logger.info("Acquiring ARM token via DefaultAzureCredential")
    arm_token = entra.bearer_token(entra.ARM_SCOPE)

    uri = (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.VideoIndexer/accounts/{ACCOUNT_NAME}"
        f"/generateAccessToken?api-version={ARM_API_VERSION}"
    )
    response = requests.post(
        uri,
        headers={"Authorization": f"Bearer {arm_token}"},
        json={"permissionType": "Contributor", "scope": "Account"},
    )
    response.raise_for_status()
    logger.info("Video Indexer access token acquired")
    return response.json()["accessToken"]


def _upload_video(access_token, video_stream):
    """Upload the video stream for indexing and return the video ID."""
    logger.info("Uploading video for indexing")
    response = requests.post(
        f"{API_BASE}/Videos",
        params={
            "accessToken": access_token,
            "name": f"video-to-text-{int(time.time())}",
            "privacy": "Private",
            "streamingPreset": "NoStreaming",
        },
        files={"file": ("video", video_stream)},
    )
    response.raise_for_status()
    video_id = response.json()["id"]
    logger.info("Upload complete, video ID: %s", video_id)
    return video_id


def _wait_for_index(access_token, video_id):
    """Poll until indexing completes and return the video index insights."""
    while True:
        response = requests.get(
            f"{API_BASE}/Videos/{video_id}/Index",
            params={"accessToken": access_token},
        )
        response.raise_for_status()
        index = response.json()

        state = index["state"]
        if state == "Processed":
            logger.info("Indexing complete for video %s", video_id)
            return index
        if state == "Failed":
            raise RuntimeError(f"Video indexing failed: {index.get('failureMessage', 'unknown error')}")

        progress = index.get("videos", [{}])[0].get("processingProgress", "")
        logger.info("Indexing state: %s %s", state, progress)
        time.sleep(POLL_INTERVAL_SECONDS)


def upload(video_stream):
    """Upload an encoded video stream for indexing; return its video ID."""
    return _upload_video(_get_access_token(), video_stream)


def transcript_for(video_id):
    """Wait for an uploaded video's indexing to finish; return its transcript."""
    index = _wait_for_index(_get_access_token(), video_id)

    transcript = index["videos"][0]["insights"].get("transcript", [])
    logger.info("Transcript extracted: %d lines", len(transcript))
    return " ".join(line["text"] for line in transcript if line.get("text"))


def video_to_speech(video_stream):
    """Transcribe the speech in an encoded video stream to a string."""
    return transcript_for(upload(video_stream))
