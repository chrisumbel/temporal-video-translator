import asyncio
import json

import pytest
from temporalio.testing import ActivityEnvironment

from tvt.azure import paragrapher
from tvt.azure import summarizer


def test_same_ignoring_whitespace():
    assert paragrapher.same_ignoring_whitespace("a b c", "a\n\nb c")
    assert paragrapher.same_ignoring_whitespace("one two", "one\ttwo")
    assert not paragrapher.same_ignoring_whitespace("one two", "one too")
    assert not paragrapher.same_ignoring_whitespace("one two", "one two three")


class FakeResponse:
    def __init__(self, text):
        self._text = text

    def raise_for_status(self):
        pass

    def json(self):
        return {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": self._text},
        ]}]}


def _install(monkeypatch, reply):
    monkeypatch.setattr(summarizer, "auth_headers", lambda: {"Authorization": "Bearer token"})
    monkeypatch.setattr(paragrapher.requests, "post", lambda *a, **kw: FakeResponse(reply))


def test_add_paragraphs_inserts_breaks_at_reported_starts(monkeypatch):
    _install(monkeypatch, json.dumps({"paragraph_starts": [1, 3]}))
    text = "One. Two. Three. Four."
    assert paragrapher.add_paragraphs(text) == "One. Two.\n\nThree. Four."


def test_out_of_range_starts_are_ignored(monkeypatch):
    _install(monkeypatch, json.dumps({"paragraph_starts": [1, 3, 99]}))
    assert paragrapher.add_paragraphs("One. Two. Three.") == "One. Two.\n\nThree."


def test_single_sentence_passes_through_without_a_call(monkeypatch):
    monkeypatch.setattr(paragrapher.requests, "post",
                        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("no call")))
    assert paragrapher.add_paragraphs("Just one sentence.") == "Just one sentence."


def test_unusable_model_reply_raises_value_error(monkeypatch):
    _install(monkeypatch, "not json at all")
    with pytest.raises(ValueError):
        paragrapher.add_paragraphs("One. Two. Three.")


def test_activity_falls_back_to_original_on_rewording(monkeypatch):
    from tvt.temporal.activities import paragraph_transcript_activity
    monkeypatch.setattr(paragrapher, "add_paragraphs",
                        lambda text: (_ for _ in ()).throw(ValueError("altered")))
    env = ActivityEnvironment()
    out = asyncio.run(env.run(paragraph_transcript_activity, "untouched text"))
    assert out == "untouched text"
