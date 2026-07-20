"""Pick the best screenshot from candidate images with gpt-4o vision.

Provider-neutral: operates on raw image bytes with auth_headers injected via
the constructor; storage concerns (fetching candidates, publishing the
winner) stay with the caller."""

import base64
import json
import logging

import requests

from tvt.ai import summarizer

logger = logging.getLogger(__name__)

# The selection rules, applied in priority order. Tweak freely.
SELECTION_RULES = """Pick the best screenshot using these rules, in priority order:
1. Prefer the image showing the clearest, most prominent human: a visible face
   beats a distant or partial figure; in focus beats blurry.
2. If no image contains a human, pick an image with the clearest depiction of a machine.
3. If no image contains a human or a machine, then pick an image that contains a planet, natural scene, or geographic depiction.
4. If none of the above, pick the image with the most visual contrast.
Respond with JSON: {"choice": <zero-based index>, "reason": "<one sentence>"}"""


class ScreenshotSelector:
    def __init__(self, auth_headers):
        self.auth_headers = auth_headers

    def choose_best(self, images):
        """Ask gpt-4o vision which of the JPEG byte strings is best; return its index."""
        content = [{"type": "input_text",
                    "text": (f"Here are {len(images)} screenshots, in order. "
                             "Reply with your JSON verdict.")}]
        for image in images:
            b64 = base64.b64encode(image).decode()
            content.append({"type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{b64}"})

        response = requests.post(
            f"{summarizer.OPENAI_V1_BASE}/responses",
            headers=self.auth_headers(),
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
        if not 0 <= choice < len(images):
            raise ValueError(f"model chose out-of-range screenshot {choice}")
        logger.info("Chose screenshot %d: %s", choice, verdict.get("reason", ""))
        return choice
