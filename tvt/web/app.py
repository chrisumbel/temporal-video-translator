"""Flask UI to submit VideoTranslatorWorkflow runs and follow their progress.

Serves the form, starts workflows (like start.py), and exposes a status API
the page polls: step-by-step activity progress from workflow history, then
the final result document. Run: gunicorn -b 0.0.0.0:5000 web:app
"""

import asyncio
import logging
import os
import uuid
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request
from temporalio.client import Client

from tvt.azure.ai import translate
from tvt.temporal.shared import (
    TASK_QUEUE,
    WORKFLOW_ID,
    VideoTranslateParams,
    temporal_namespace,
    temporal_target,
)
from tvt.temporal.workflows import VideoTranslatorWorkflow

app = Flask(__name__)
logger = logging.getLogger(__name__)

DEFAULT_LANGUAGES = ["fr", "es", "de", "ja", "ko", "zh-Hans"]

TERMINAL_BAD = ("FAILED", "TERMINATED", "TIMED_OUT", "CANCELED")

_supported_cache = None


def _language_choices():
    """Defaults first (checked in the UI), then the rest of the Translator's
    supported codes; falls back to just the defaults if the fetch fails."""
    global _supported_cache
    if _supported_cache is None:
        try:
            _supported_cache = translate.supported_languages()
        except Exception:
            logger.exception("could not fetch Translator languages")
            return list(DEFAULT_LANGUAGES)
    rest = sorted(code for code in _supported_cache if code not in DEFAULT_LANGUAGES)
    return DEFAULT_LANGUAGES + rest


async def _client():
    return await Client.connect(temporal_target(), namespace=temporal_namespace())


@app.get("/")
def index():
    return render_template(
        "index.html", languages=_language_choices(), defaults=DEFAULT_LANGUAGES
    )


@app.post("/api/runs")
def start_run():
    body = request.get_json(force=True)
    video_url = (body.get("video_url") or "").strip()
    languages = body.get("languages") or []
    if not video_url or not languages:
        return jsonify({"error": "video_url and at least one language are required"}), 400

    video_name = os.path.basename(urlparse(video_url).path) or "video"
    workflow_id = f"{WORKFLOW_ID}-{video_name}-{uuid.uuid4().hex[:8]}"

    async def _start():
        client = await _client()
        await client.start_workflow(
            VideoTranslatorWorkflow.run,
            VideoTranslateParams(
                video_url=video_url,
                languages=languages,
                api_key=os.environ.get("API_KEY", ""),
            ),
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )

    asyncio.run(_start())
    logger.info("started %s for %s (%s)", workflow_id, video_url, languages)
    return jsonify({"workflow_id": workflow_id})


def _failure_message(failure):
    """Deepest cause message in a failure chain."""
    while failure.HasField("cause"):
        failure = failure.cause
    return failure.message


async def _run_status(workflow_id):
    client = await _client()
    handle = client.get_workflow_handle(workflow_id)
    desc = await handle.describe()
    status = desc.status.name if desc.status else "UNKNOWN"

    # activity checklist from history; retries in flight appear via describe
    steps, by_scheduled_id, error = [], {}, None
    async for event in handle.fetch_history_events():
        if event.HasField("activity_task_scheduled_event_attributes"):
            step = {
                "activity": event.activity_task_scheduled_event_attributes.activity_type.name,
                "state": "scheduled",
            }
            by_scheduled_id[event.event_id] = step
            steps.append(step)
        elif event.HasField("activity_task_completed_event_attributes"):
            sid = event.activity_task_completed_event_attributes.scheduled_event_id
            by_scheduled_id.get(sid, {})["state"] = "completed"
        elif event.HasField("activity_task_failed_event_attributes"):
            attrs = event.activity_task_failed_event_attributes
            by_scheduled_id.get(attrs.scheduled_event_id, {})["state"] = "failed"
            error = _failure_message(attrs.failure)
        elif event.HasField("workflow_execution_failed_event_attributes"):
            error = _failure_message(
                event.workflow_execution_failed_event_attributes.failure
            )
        elif event.HasField("workflow_execution_terminated_event_attributes"):
            attrs = event.workflow_execution_terminated_event_attributes
            error = f"terminated: {attrs.reason or 'no reason given'}"

    for pending in desc.raw_description.pending_activities:
        for step in steps:
            if step["activity"] == pending.activity_type.name and step["state"] in (
                "scheduled", "failed",
            ):
                step["state"] = "running"
                step["attempt"] = pending.attempt

    payload = {"workflow_id": workflow_id, "status": status, "steps": steps}
    if status == "COMPLETED":
        payload["result"] = await handle.result()
    elif status in TERMINAL_BAD:
        payload["error"] = error or status
    return payload


@app.get("/api/runs/<workflow_id>")
def run_status(workflow_id):
    return jsonify(asyncio.run(_run_status(workflow_id)))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
