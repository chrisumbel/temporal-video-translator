#!/usr/bin/env python3
"""Translate English text to another language using Azure AI Translator."""

import logging
import os
import sys

import requests
from dotenv import load_dotenv

from tvt.azure import entra

load_dotenv()

SUBSCRIPTION_ID = os.environ["AZURE_SUBSCRIPTION_ID"]
RESOURCE_GROUP = os.environ["AZURE_RESOURCE_GROUP"]
ACCOUNT_NAME = os.environ["TRANSLATOR_ACCOUNT_NAME"]
LOCATION = os.environ["AZURE_LOCATION"]

TRANSLATOR_ENDPOINT = os.environ["TRANSLATOR_ENDPOINT"]
# Entra auth against the global endpoint needs the regional resource spelled out
TRANSLATOR_RESOURCE_ID = (
    f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
    f"/providers/Microsoft.CognitiveServices/accounts/{ACCOUNT_NAME}"
)

# common not-quite-right codes people reach for
LANGUAGE_ALIASES = {
    "jp": "ja",
    "kr": "ko",
    "cn": "zh-Hans",
    "zh": "zh-Hans",
    "zh-cn": "zh-Hans",
    "zh-tw": "zh-Hant",
}

logger = logging.getLogger(__name__)


def supported_languages():
    """Translator's supported translation codes (unauthenticated endpoint)."""
    response = requests.get(
        f"{TRANSLATOR_ENDPOINT}/languages",
        params={"api-version": "3.0", "scope": "translation"},
    )
    response.raise_for_status()
    return list(response.json()["translation"].keys())


def normalize_language(language, supported=None):
    """Map language to a canonical Translator code; raise ValueError if unknown."""
    supported = supported if supported is not None else supported_languages()
    by_lower = {code.lower(): code for code in supported}
    candidate = LANGUAGE_ALIASES.get(language.lower(), language)
    code = by_lower.get(candidate.lower())
    if code is None:
        raise ValueError(f"unsupported translation language {language!r}")
    return code


def translate(text, language):
    """Translate an English string to the given target language."""
    logger.info("Translating %d characters to %s", len(text), language)
    response = requests.post(
        f"{TRANSLATOR_ENDPOINT}/translate",
        params={"api-version": "3.0", "from": "en", "to": language},
        headers={
            "Authorization": f"Bearer {entra.bearer_token(entra.COGNITIVE_SCOPE)}",
            "Ocp-Apim-ResourceId": TRANSLATOR_RESOURCE_ID,
            "Ocp-Apim-Subscription-Region": LOCATION,
        },
        json=[{"Text": text}],
    )
    response.raise_for_status()
    return response.json()[0]["translations"][0]["text"]


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logging.getLogger("azure").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <language> <text>", file=sys.stderr)
        sys.exit(1)

    print(translate(sys.argv[2], sys.argv[1]))


if __name__ == "__main__":
    main()
