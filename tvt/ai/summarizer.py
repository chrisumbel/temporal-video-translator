"""Summarize long text to about 200 words with gpt-4o.

Provider-neutral: the constructor takes auth_headers, a zero-arg callable
returning the HTTP headers that authenticate to the OpenAI-compatible
endpoint."""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

DEPLOYMENT = os.environ["OPENAI_DEPLOYMENT"]

OPENAI_ENDPOINT = os.environ["OPENAI_ENDPOINT"]
# the v1 surface (Responses API); no per-request api-version needed
OPENAI_V1_BASE = f"{OPENAI_ENDPOINT}/openai/v1"

logger = logging.getLogger(__name__)


def output_text(response_json):
    """Collect the output_text parts of a Responses API response."""
    return "".join(
        part["text"]
        for item in response_json["output"] if item["type"] == "message"
        for part in item["content"] if part["type"] == "output_text"
    )


class Summarizer:
    def __init__(self, auth_headers):
        self.auth_headers = auth_headers

    def summarize(self, text):
        """Summarize a long string into a roughly 150 word summary."""
        logger.info("Summarizing %d characters with %s", len(text), DEPLOYMENT)
        response = requests.post(
            f"{OPENAI_V1_BASE}/responses",
            headers=self.auth_headers(),
            json={
                "model": DEPLOYMENT,
                "instructions": (
                    "Summarize the text provided by the user in about 150 words. Less is fine if the text is short."
                    "Write plain prose only: no LaTeX, Markdown, code formatting, or "
                    "other markup. Express mathematical notation in words "
                    "(e.g. 'A x = 0', 'x squared', not '\\( A \\mathbf{x} = 0 \\)')."
                ),
                "input": text,
            },
        )
        response.raise_for_status()
        return output_text(response.json())
