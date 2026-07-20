"""Temporal workflow orchestrating one pass: download, transcribe, summarize +
translate (concurrent), then upload the result JSON to blob storage."""

import asyncio
import posixpath
from datetime import timedelta
from urllib.parse import urlparse

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from tvt.temporal.activities import (
        download_video_activity,
        extract_screenshots_activity,
        normalize_languages_activity,
        paragraph_transcript_activity,
        render_pdf_activity,
        select_screenshot_activity,
        summarize_activity,
        transcribe_video_activity,
        translate_activity,
        upload_result_activity,
        validate_api_key_activity,
    )
    from tvt.temporal.shared import (
        PdfRequest,
        SCREENSHOT_TASK_QUEUE,
        SUMMARIZE_TASK_QUEUE,
        TRANSCRIBE_TASK_QUEUE,
        TRANSLATE_TASK_QUEUE,
        ScreenshotSelectRequest,
        TranslateRequest,
        UploadRequest,
        VideoTranslateParams,
        VideoTranslateResult,
    )


@workflow.defn
class VideoTranslatorWorkflow:
    @workflow.run
    async def run(self, params: VideoTranslateParams) -> VideoTranslateResult:
        workflow.logger.info(
            f"Starting video-translator run for {params.video_url} "
            f"(languages={params.languages})"
        )

        # Step 0: reject runs without a valid API key before doing any work
        await workflow.execute_activity(
            validate_api_key_activity,
            params.api_key,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )

        # Normalize language codes (jp -> ja) and reject unknown ones before
        # spending on transcription
        languages = await workflow.execute_activity(
            normalize_languages_activity,
            params.languages,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        # Step 1: download into blob storage
        video_blob_name = await workflow.execute_activity(
            download_video_activity,
            params.video_url,
            start_to_close_timeout=timedelta(minutes=15),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        video_name = posixpath.basename(urlparse(params.video_url).path) or "video"
        video_stem = posixpath.splitext(video_name)[0]

        # Step 2: transcribe, and in parallel screenshot + pick the best shot.
        # Indexing is slow; generous timeout, few retries.
        transcribe_future = workflow.execute_activity(
            transcribe_video_activity,
            video_blob_name,
            task_queue=TRANSCRIBE_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=120),
            # dead workers are detected in minutes, not the full hour above
            heartbeat_timeout=timedelta(minutes=2),
            retry_policy=RetryPolicy(maximum_attempts=4),
        )

        async def best_screenshot() -> str:
            screenshot_blob_names = await workflow.execute_activity(
                extract_screenshots_activity,
                video_blob_name,
                task_queue=SCREENSHOT_TASK_QUEUE,
                start_to_close_timeout=timedelta(minutes=15),
                heartbeat_timeout=timedelta(minutes=1),
                retry_policy=RetryPolicy(maximum_attempts=4),
            )
            # selection runs on the summarize queue: it shares the gpt-4o quota
            return await workflow.execute_activity(
                select_screenshot_activity,
                ScreenshotSelectRequest(
                    screenshot_blob_names=screenshot_blob_names,
                    public_name=f"{video_stem}.jpg",
                ),
                task_queue=SUMMARIZE_TASK_QUEUE,
                start_to_close_timeout=timedelta(minutes=5),
                heartbeat_timeout=timedelta(minutes=1),
                retry_policy=RetryPolicy(maximum_attempts=4),
            )

        transcript, screenshot_url = await asyncio.gather(
            transcribe_future, best_screenshot()
        )

        # Break the transcript into paragraphs (whitespace-only, verified;
        # falls back to the raw transcript if the model changes any words)
        transcript = await workflow.execute_activity(
            paragraph_transcript_activity,
            transcript,
            task_queue=SUMMARIZE_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=8),
        )

        # Step 3: summarize + translate concurrently
        text_retry = RetryPolicy(maximum_attempts=4)
        summary_future = workflow.execute_activity(
            summarize_activity,
            transcript,
            task_queue=SUMMARIZE_TASK_QUEUE,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=text_retry,
        )
        translation_futures = [
            workflow.execute_activity(
                translate_activity,
                TranslateRequest(text=transcript, language=language),
                task_queue=TRANSLATE_TASK_QUEUE,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=text_retry,
            )
            for language in languages
        ]
        summary, *translations = await asyncio.gather(
            summary_future, *translation_futures
        )

        result = VideoTranslateResult(
            video_url=params.video_url,
            transcript=transcript,
            summary=summary,
            translations=list(translations),
            screenshot_url=screenshot_url,
        )

        # Step 4: upload the result JSON, prefixed with the workflow ID
        # (video-translator-jfk.mp4-1234abcd-jfk.json)
        workflow_id = workflow.info().workflow_id
        result.blob_url = await workflow.execute_activity(
            upload_result_activity,
            UploadRequest(blob_name=f"{workflow_id}-{video_stem}.json", result=result),
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=4),
        )

        # Step 5: render the PDF report from the same document
        result.pdf_url = await workflow.execute_activity(
            render_pdf_activity,
            PdfRequest(
                blob_name=f"{workflow_id}-{video_stem}.pdf",
                workflow_id=workflow_id,
                result=result,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(minutes=1),
            retry_policy=RetryPolicy(maximum_attempts=4),
        )

        workflow.logger.info(
            f"Run complete: {len(transcript)} transcript characters, "
            f"{len(translations)} translation(s), uploaded to {result.blob_url}, "
            f"PDF at {result.pdf_url}."
        )
        return result
