#!/usr/bin/env python3
"""Summarize long text to about 200 words using Azure OpenAI."""

import logging
import os
import sys

import requests
from dotenv import load_dotenv

from tvt.azure import entra

load_dotenv()

DEPLOYMENT = os.environ["OPENAI_DEPLOYMENT"]

OPENAI_ENDPOINT = os.environ["OPENAI_ENDPOINT"]
# the v1 surface (Responses API); no per-request api-version needed
OPENAI_V1_BASE = f"{OPENAI_ENDPOINT}/openai/v1"

logger = logging.getLogger(__name__)


def auth_headers():
    """Entra bearer auth headers for Azure OpenAI data-plane calls."""
    return {"Authorization": f"Bearer {entra.bearer_token(entra.COGNITIVE_SCOPE)}"}


def output_text(response_json):
    """Collect the output_text parts of a Responses API response."""
    return "".join(
        part["text"]
        for item in response_json["output"] if item["type"] == "message"
        for part in item["content"] if part["type"] == "output_text"
    )


def summarize(text):
    """Summarize a long string into a roughly 200 word summary."""
    logger.info("Summarizing %d characters with %s", len(text), DEPLOYMENT)
    response = requests.post(
        f"{OPENAI_V1_BASE}/responses",
        headers=auth_headers(),
        json={
            "model": DEPLOYMENT,
            "instructions": "Summarize the text provided by the user in about 150 words.",
            "input": text,
        },
    )
    response.raise_for_status()
    return output_text(response.json())


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <text>", file=sys.stderr)
        sys.exit(1)

    print(summarize(" ".join(sys.argv[1:])))


if __name__ == "__main__":
    main()
