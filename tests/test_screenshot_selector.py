import json

import pytest

from tvt.azure import screenshot_selector
from tvt.azure import summarizer


class FakeResponse:
    def __init__(self, verdict):
        self._verdict = verdict

    def raise_for_status(self):
        pass

    def json(self):
        return {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(self._verdict)},
        ]}]}


class FakeBlob:
    def readall(self):
        return b"not-really-a-jpeg"


@pytest.fixture
def selector_doubles(monkeypatch):
    def _install(verdict):
        monkeypatch.setattr(summarizer, "auth_headers", lambda: {"Authorization": "Bearer token"})
        monkeypatch.setattr(screenshot_selector.blob_store, "open_blob",
                            lambda container, name: FakeBlob())
        monkeypatch.setattr(screenshot_selector.requests, "post",
                            lambda *a, **kw: FakeResponse(verdict))
    return _install


def test_choose_best_returns_model_choice(selector_doubles):
    selector_doubles({"choice": 1, "reason": "clear face"})
    assert screenshot_selector.choose_best(["a.jpg", "b.jpg", "c.jpg"]) == 1


def test_out_of_range_choice_raises(selector_doubles):
    selector_doubles({"choice": 7, "reason": "hallucinated"})
    with pytest.raises(ValueError, match="out-of-range"):
        screenshot_selector.choose_best(["a.jpg", "b.jpg"])
