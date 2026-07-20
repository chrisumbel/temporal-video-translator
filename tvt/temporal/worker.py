"""Temporal worker hosting VideoTranslatorWorkflow and its activities: python worker.py

One process runs one Worker per task queue so each Azure-bound stage gets its
own concurrency cap. WORKER_QUEUES (comma list of roles) selects which pools
this process hosts, so deployments can split roles across containers.
"""

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

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
from tvt.log_config import setup_logging
from tvt.temporal.shared import (
    MAX_CONCURRENT_SCREENSHOT,
    MAX_CONCURRENT_SUMMARIZE,
    MAX_CONCURRENT_TRANSCRIBE,
    MAX_CONCURRENT_TRANSLATE,
    SCREENSHOT_TASK_QUEUE,
    SUMMARIZE_TASK_QUEUE,
    TASK_QUEUE,
    TRANSCRIBE_TASK_QUEUE,
    TRANSLATE_TASK_QUEUE,
    WORKER_QUEUES,
    temporal_namespace,
    temporal_target,
)
from tvt.temporal.workflows import VideoTranslatorWorkflow

logger = setup_logging(logging.INFO)


def _build_workers(client: Client) -> list[Worker]:
    # main: the workflow plus storage-bound activities; the rest are
    # per-resource pools, each capped to its Azure quota
    builders = {
        "main": lambda: Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[VideoTranslatorWorkflow],
            activities=[validate_api_key_activity, normalize_languages_activity,
                        download_video_activity, upload_result_activity,
                        render_pdf_activity],
        ),
        "transcribe": lambda: Worker(
            client,
            task_queue=TRANSCRIBE_TASK_QUEUE,
            activities=[transcribe_video_activity],
            max_concurrent_activities=MAX_CONCURRENT_TRANSCRIBE,
        ),
        "summarize": lambda: Worker(
            client,
            task_queue=SUMMARIZE_TASK_QUEUE,
            activities=[summarize_activity, select_screenshot_activity,
                        paragraph_transcript_activity],
            max_concurrent_activities=MAX_CONCURRENT_SUMMARIZE,
        ),
        "translate": lambda: Worker(
            client,
            task_queue=TRANSLATE_TASK_QUEUE,
            activities=[translate_activity],
            max_concurrent_activities=MAX_CONCURRENT_TRANSLATE,
        ),
        "screenshot": lambda: Worker(
            client,
            task_queue=SCREENSHOT_TASK_QUEUE,
            activities=[extract_screenshots_activity],
            max_concurrent_activities=MAX_CONCURRENT_SCREENSHOT,
        ),
    }
    roles = [role.strip() for role in WORKER_QUEUES.split(",") if role.strip()]
    return [builders[role]() for role in roles]


async def main():
    client = await Client.connect(temporal_target(), namespace=temporal_namespace())
    logger.info(
        f"Worker connecting to Temporal at {temporal_target()} "
        f"(namespace={temporal_namespace()})"
    )

    workers = _build_workers(client)
    queues = [w.task_queue for w in workers]
    logger.info(f"Worker started; polling task queues {queues}")
    await asyncio.gather(*(w.run() for w in workers))


if __name__ == "__main__":
    asyncio.run(main())
