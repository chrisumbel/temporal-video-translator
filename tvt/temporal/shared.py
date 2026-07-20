"""Shared config + JSON-serializable dataclasses crossing the workflow/activity boundary."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


# Temporal connection / queue config

TASK_QUEUE = os.environ.get("TEMPORAL_TASK_QUEUE", "video-translator")
WORKFLOW_ID = os.environ.get("TEMPORAL_WORKFLOW_ID", "video-translator")

# Azure-bound stages get their own queues so concurrency can be capped per
# resource quota. Caps are per worker process; N replicas allow N x cap.
TRANSCRIBE_TASK_QUEUE = os.environ.get("TEMPORAL_TRANSCRIBE_TASK_QUEUE", "video-translator-transcribe")
SUMMARIZE_TASK_QUEUE = os.environ.get("TEMPORAL_SUMMARIZE_TASK_QUEUE", "video-translator-summarize")
TRANSLATE_TASK_QUEUE = os.environ.get("TEMPORAL_TRANSLATE_TASK_QUEUE", "video-translator-translate")
SCREENSHOT_TASK_QUEUE = os.environ.get("TEMPORAL_SCREENSHOT_TASK_QUEUE", "video-translator-screenshot")

MAX_CONCURRENT_TRANSCRIBE = int(os.environ.get("MAX_CONCURRENT_TRANSCRIBE", "3"))
MAX_CONCURRENT_SUMMARIZE = int(os.environ.get("MAX_CONCURRENT_SUMMARIZE", "2"))
MAX_CONCURRENT_TRANSLATE = int(os.environ.get("MAX_CONCURRENT_TRANSLATE", "4"))
MAX_CONCURRENT_SCREENSHOT = int(os.environ.get("MAX_CONCURRENT_SCREENSHOT", "2"))

# Which worker pools this process hosts (comma list); default is all of them
WORKER_QUEUES = os.environ.get(
    "WORKER_QUEUES", "main,transcribe,summarize,translate,screenshot"
)


def temporal_target() -> str:
    return os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")


def temporal_namespace() -> str:
    return os.environ.get("TEMPORAL_NAMESPACE", "default")


# Workflow / activity payloads

@dataclass
class VideoTranslateParams:
    """Workflow input: video URL, target language codes, and the caller's API key."""
    video_url: str
    languages: list[str] = field(default_factory=list)
    api_key: str = ""


@dataclass
class TranslateRequest:
    """Translation activity input: text and one target language."""
    text: str
    language: str


@dataclass
class Translation:
    """One completed translation."""
    language: str
    text: str


@dataclass
class ScreenshotSelectRequest:
    """Screenshot-selection activity input: candidate scratch blobs and the
    public name for the winner."""
    screenshot_blob_names: list[str]
    public_name: str


@dataclass
class VideoTranslateResult:
    """Workflow result: transcript, summary, translations, best screenshot URL,
    and the blob URLs of the uploaded JSON and PDF report."""
    video_url: str
    transcript: str
    summary: str
    translations: list[Translation] = field(default_factory=list)
    screenshot_url: str | None = None
    blob_url: str | None = None
    pdf_url: str | None = None


@dataclass
class PdfRequest:
    """PDF-render activity input: result document, destination blob name, and
    the workflow ID shown on the report."""
    blob_name: str
    workflow_id: str
    result: VideoTranslateResult


@dataclass
class UploadRequest:
    """Upload activity input: result document and destination blob name."""
    blob_name: str
    result: VideoTranslateResult
