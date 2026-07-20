"""Pick the best screenshot with gpt-4o vision and promote it to the public container."""

import base64
import json
import logging
import os

import requests
from dotenv import load_dotenv

from tvt.azure import blob_store
from tvt.azure import summarizer

load_dotenv()

SCRATCH_SCREENSHOT_CONTAINER = os.environ["SCRATCH_SCREENSHOT_CONTAINER"]
SCREENSHOT_CONTAINER = os.environ["SCREENSHOT_CONTAINER"]

logger = logging.getLogger(__name__)

# The selection rules, applied in priority order. Tweak freely.
SELECTION_RULES = """Pick the best screenshot using these rules, in priority order:
1. Prefer the image showing the clearest, most prominent human: a visible face
   beats a distant or partial figure; in focus beats blurry.
2. If no image contains a human, pick an image with the clearest depiction of a machine.
3. If no image contains a human or a machine, then pick an image that contains a planet, natural scene, or geographic depiction. 
4. If none of the above, pick the image with the most visual contrast.
Respond with JSON: {"choice": <zero-based index>, "reason": "<one sentence>"}"""


def choose_best(screenshot_blob_names):
    """Ask gpt-4o vision which screenshot is best; return its index."""
    content = [{"type": "input_text",
                "text": (f"Here are {len(screenshot_blob_names)} screenshots, in order. "
                         "Reply with your JSON verdict.")}]
    for blob_name in screenshot_blob_names:
        image = blob_store.open_blob(SCRATCH_SCREENSHOT_CONTAINER, blob_name).readall()
        b64 = base64.b64encode(image).decode()
        content.append({"type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{b64}"})

    response = requests.post(
        f"{summarizer.OPENAI_V1_BASE}/responses",
        headers=summarizer.auth_headers(),
        json={
            "model": summarizer.DEPLOYMENT,
            "instructions": SELECTION_RULES,
            "input": [{"role": "user", "content": content}],
            "text": {"format": {"type": "json_object"}},
        },
    )
    response.raise_for_status()
    verdict = json.loads(summarizer.output_text(response.json()))

    choice = int(verdict["choice"])
    if not 0 <= choice < len(screenshot_blob_names):
        raise ValueError(f"model chose out-of-range screenshot {choice}")
    logger.info("Chose screenshot %d: %s", choice, verdict.get("reason", ""))
    return choice


def promote(scratch_blob_name, public_name):
    """Copy a scratch screenshot into the public container; return its URL."""
    image = blob_store.open_blob(SCRATCH_SCREENSHOT_CONTAINER, scratch_blob_name).readall()
    return blob_store.upload_blob(SCREENSHOT_CONTAINER, public_name, image,
                                  content_type="image/jpeg")
