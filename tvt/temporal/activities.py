"""Temporal activities: thin wrappers exposing the logic modules' I/O to the workflow."""

import asyncio
import dataclasses
import json
import os
import secrets

from temporalio import activity
from temporalio.exceptions import ApplicationError

from tvt.ai.paragrapher import Paragrapher
from tvt.ai.screenshot_selector import ScreenshotSelector
from tvt.ai.summarizer import Summarizer
from tvt.azure.ai import translate
from tvt.azure.ai import video_to_text
from tvt.azure.ai.auth import openai_auth_headers
from tvt.media import downloader
from tvt.media import screenshots
from tvt.media import uploader
from tvt.temporal.shared import (
    PdfRequest,
    ScreenshotSelectRequest,
    Translation,
    TranslateRequest,
    UploadRequest,
)

MAX_LOG_CHARS = 120

HEARTBEAT_INTERVAL_SECONDS = 10

# gpt-4o helpers wired to Azure OpenAI via Entra auth
summarizer = Summarizer(openai_auth_headers)
paragrapher = Paragrapher(openai_auth_headers)
screenshot_selector = ScreenshotSelector(openai_auth_headers)


async def _run_with_heartbeat(fn, *args, details=()):
    """Run blocking fn in a thread, heartbeating (with details) while it runs."""
    async def _beat():
        while True:
            activity.heartbeat(*details)
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

    beat = asyncio.create_task(_beat())
    try:
        return await asyncio.to_thread(fn, *args)
    finally:
        beat.cancel()


@activity.defn
async def validate_api_key_activity(api_key: str) -> None:
    """Reject the run unless the caller's API key matches the worker's API_KEY."""
    expected = os.environ.get("API_KEY", "")
    if not expected or not secrets.compare_digest(api_key, expected):
        raise ApplicationError("invalid API key", non_retryable=True)
    activity.logger.info("API key validated")


@activity.defn
async def normalize_languages_activity(languages: list[str]) -> list[str]:
    """Map requested language codes to canonical Translator codes; reject
    unknown ones before any expensive work runs."""
    def _normalize() -> list[str]:
        supported = translate.supported_languages()
        normalized, invalid = [], []
        for language in languages:
            try:
                code = translate.normalize_language(language, supported)
                if code not in normalized:
                    normalized.append(code)
            except ValueError:
                invalid.append(language)
        if invalid:
            raise ApplicationError(
                f"unsupported translation language(s): {', '.join(invalid)}",
                non_retryable=True,
            )
        return normalized

    normalized = await asyncio.to_thread(_normalize)
    activity.logger.info(f"Languages {languages} normalized to {normalized}")
    return normalized


@activity.defn
async def download_video_activity(url: str) -> str:
    """Stage the video at url into the videos container; return its blob name."""
    blob_name = await _run_with_heartbeat(downloader.download_video, url)
    activity.logger.info(f"Downloaded {url} to video blob {blob_name}")
    return blob_name


@activity.defn
async def transcribe_video_activity(video_blob_name: str) -> str:
    """Transcribe the staged video blob with Azure Video Indexer.

    Heartbeat details carry the Video Indexer video ID, so a retried attempt
    resumes polling the existing indexing job instead of re-uploading."""
    details = activity.info().heartbeat_details
    video_id = details[0] if details else None

    if video_id is None:
        activity.logger.info(f"Transcribing video blob {video_blob_name}")
        video_id = await _run_with_heartbeat(
            lambda: video_to_text.upload(downloader.open_video(video_blob_name))
        )
        activity.heartbeat(video_id)
    else:
        activity.logger.info(f"Resuming transcription, video ID {video_id}")

    transcript = await _run_with_heartbeat(
        video_to_text.transcript_for, video_id, details=(video_id,)
    )
    activity.logger.info(f"Transcribed {video_blob_name}: {len(transcript)} characters")
    return transcript


@activity.defn
async def extract_screenshots_activity(video_blob_name: str) -> list[str]:
    """Take screenshots of the staged video with ffmpeg; return their scratch blob names."""
    blob_names = await _run_with_heartbeat(screenshots.extract_screenshots, video_blob_name)
    activity.logger.info(f"Extracted screenshots {blob_names}")
    return blob_names


@activity.defn
async def select_screenshot_activity(request: ScreenshotSelectRequest) -> str:
    """Pick the best screenshot with gpt-4o and publish it; return its public URL."""
    def _select() -> str:
        images = [screenshots.scratch_image(name)
                  for name in request.screenshot_blob_names]
        choice = screenshot_selector.choose_best(images)
        chosen = request.screenshot_blob_names[choice]
        return screenshots.promote(chosen, request.public_name)

    url = await _run_with_heartbeat(_select)
    activity.logger.info(f"Best screenshot published to {url}")
    return url


@activity.defn
async def paragraph_transcript_activity(transcript: str) -> str:
    """Insert paragraph breaks with gpt-4o; whitespace-only by construction.
    Falls back to the unmodified transcript if the model won't comply."""
    for attempt in (1, 2):
        try:
            paragraphed = await _run_with_heartbeat(paragrapher.add_paragraphs, transcript)
            activity.logger.info(
                f"Transcript paragraphed: {paragraphed.count(chr(10) * 2) + 1} paragraphs"
            )
            return paragraphed
        except ValueError:
            activity.logger.warning(f"paragraphing altered text on attempt {attempt}")
    activity.logger.warning("falling back to the unparagraphed transcript")
    return transcript


@activity.defn
async def summarize_activity(text: str) -> str:
    """Summarize the transcript with Azure OpenAI."""
    summary = await asyncio.to_thread(summarizer.summarize, text)
    activity.logger.info(f"Summarized {len(text)} characters to {len(summary)}")
    return summary


@activity.defn
async def translate_activity(request: TranslateRequest) -> Translation:
    """Translate the text with Azure Translator."""
    translated = await asyncio.to_thread(
        translate.translate, request.text, request.language
    )
    activity.logger.info(
        f"Translated to {request.language}: {translated[:MAX_LOG_CHARS]!r}"
    )
    return Translation(language=request.language, text=translated)


@activity.defn
async def upload_result_activity(request: UploadRequest) -> str:
    """Upload the result document as JSON to blob storage; return the blob URL."""
    document = dataclasses.asdict(request.result)
    del document["blob_url"]
    del document["pdf_url"]
    json_text = json.dumps(document, ensure_ascii=False, indent=2)

    blob_url = await _run_with_heartbeat(uploader.upload_json, request.blob_name, json_text)
    activity.logger.info(f"Uploaded result to {blob_url}")
    return blob_url


@activity.defn
async def render_pdf_activity(request: PdfRequest) -> str:
    """Render the result through output-template.html and upload the PDF;
    return its blob URL."""
    # imported here: weasyprint needs pango, which the screenshot image omits
    from tvt.media import pdf_renderer

    document = dataclasses.asdict(request.result)
    del document["blob_url"]
    del document["pdf_url"]

    def _render_and_upload() -> str:
        pdf_bytes = pdf_renderer.render_pdf(document, request.workflow_id)
        return pdf_renderer.upload_pdf(request.blob_name, pdf_bytes)

    pdf_url = await _run_with_heartbeat(_render_and_upload)
    activity.logger.info(f"PDF report uploaded to {pdf_url}")
    return pdf_url
