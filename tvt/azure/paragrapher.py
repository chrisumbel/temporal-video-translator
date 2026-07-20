"""Insert paragraph breaks into transcripts, never changing words.

gpt-4o never reproduces the text (long verbatim echoes trip Azure's
protected-material content filter): it sees numbered sentences and returns
only the numbers where paragraphs start; we rebuild the text ourselves,
so the change is whitespace-only by construction and verified anyway.
"""

import json
import logging
import re

import requests

from tvt.azure import summarizer

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

INSTRUCTIONS = """You will receive a transcript as a numbered list of sentences.
Group consecutive sentences into paragraphs of roughly 3-6 sentences, breaking
at natural topic shifts. Respond with JSON:
{"paragraph_starts": [<numbers of the sentences that start each paragraph>]}
The first paragraph starts at sentence 1; numbers must be increasing."""

logger = logging.getLogger(__name__)


def same_ignoring_whitespace(a, b):
    """True when a and b are identical after stripping all whitespace."""
    return "".join(a.split()) == "".join(b.split())


def add_paragraphs(text):
    """Return text with paragraph breaks inserted; raise ValueError if the
    result is not a whitespace-only change (or the model reply is unusable)."""
    sentences = [s for s in SENTENCE_SPLIT.split(text) if s]
    if len(sentences) < 2:
        return text

    numbered = "\n".join(f"{i}: {s}" for i, s in enumerate(sentences, start=1))

    logger.info("Paragraphing %d sentences with %s", len(sentences), summarizer.DEPLOYMENT)
    response = requests.post(
        f"{summarizer.OPENAI_V1_BASE}/responses",
        headers=summarizer.auth_headers(),
        json={
            "model": summarizer.DEPLOYMENT,
            "instructions": INSTRUCTIONS,
            "input": f"Reply with your JSON verdict for these sentences:\n{numbered}",
            "text": {"format": {"type": "json_object"}},
        },
    )
    response.raise_for_status()
    verdict = json.loads(summarizer.output_text(response.json()))

    starts = {int(n) for n in verdict["paragraph_starts"] if 1 < int(n) <= len(sentences)}
    parts = [sentences[0]]
    for i, sentence in enumerate(sentences[1:], start=2):
        parts.append(("\n\n" if i in starts else " ") + sentence)
    paragraphed = "".join(parts)

    if not same_ignoring_whitespace(text, paragraphed):
        raise ValueError("paragraphing altered non-whitespace content")
    logger.info("Paragraphed into %d paragraphs", len(starts) + 1)
    return paragraphed
