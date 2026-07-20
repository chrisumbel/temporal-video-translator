"""Start one VideoTranslatorWorkflow run and print its result JSON:
python start.py <video-url> <language> [<language> ...]"""

import asyncio
import dataclasses
import json
import logging
import os
import sys
import uuid
from urllib.parse import urlparse

from temporalio.client import Client

from tvt.log_config import setup_logging
from tvt.temporal.shared import (
    TASK_QUEUE,
    WORKFLOW_ID,
    VideoTranslateParams,
    temporal_namespace,
    temporal_target,
)
from tvt.temporal.workflows import VideoTranslatorWorkflow

logger = setup_logging(logging.INFO)


async def main() -> None:
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} <video-url> <language> [<language> ...]",
              file=sys.stderr)
        sys.exit(1)

    video_url = sys.argv[1]
    languages = sys.argv[2:]

    client = await Client.connect(temporal_target(), namespace=temporal_namespace())
    logger.info(
        f"Starting {VideoTranslatorWorkflow.__name__} for {video_url} "
        f"(languages={languages}) on queue '{TASK_QUEUE}'"
    )

    video_name = os.path.basename(urlparse(video_url).path) or "video"
    result = await client.execute_workflow(
        VideoTranslatorWorkflow.run,
        VideoTranslateParams(
            video_url=video_url,
            languages=languages,
            api_key=os.environ.get("API_KEY", ""),
        ),
        # Unique per run so repeated runs of the same video don't collide.
        id=f"{WORKFLOW_ID}-{video_name}-{uuid.uuid4().hex[:8]}",
        task_queue=TASK_QUEUE,
    )

    print(json.dumps(dataclasses.asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
