import json

import pytest

from tvt.ai import screenshot_selector
from tvt.ai.screenshot_selector import ScreenshotSelector

AUTH = lambda: {"Authorization": "Bearer token"}


class FakeResponse:
    def __init__(self, verdict):
        self._verdict = verdict

    def raise_for_status(self):
        pass

    def json(self):
        return {"output": [{"type": "message", "content": [
            {"type": "output_text", "text": json.dumps(self._verdict)},
        ]}]}


@pytest.fixture
def selector_doubles(monkeypatch):
    def _install(verdict):
        monkeypatch.setattr(screenshot_selector.requests, "post",
                            lambda *a, **kw: FakeResponse(verdict))
    return _install


def test_choose_best_returns_model_choice(selector_doubles):
    selector_doubles({"choice": 1, "reason": "clear face"})
    assert ScreenshotSelector(AUTH).choose_best([b"a", b"b", b"c"]) == 1


def test_out_of_range_choice_raises(selector_doubles):
    selector_doubles({"choice": 7, "reason": "hallucinated"})
    with pytest.raises(ValueError, match="out-of-range"):
        ScreenshotSelector(AUTH).choose_best([b"a", b"b"])
