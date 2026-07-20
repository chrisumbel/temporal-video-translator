from tvt.ai.summarizer import output_text


def test_collects_output_text_parts():
    response = {
        "output": [
            {"type": "reasoning", "content": []},
            {"type": "message", "content": [
                {"type": "output_text", "text": "part one "},
                {"type": "output_text", "text": "part two"},
            ]},
        ]
    }
    assert output_text(response) == "part one part two"


def test_ignores_non_text_parts():
    response = {
        "output": [
            {"type": "message", "content": [
                {"type": "refusal", "refusal": "nope"},
                {"type": "output_text", "text": "kept"},
            ]},
        ]
    }
    assert output_text(response) == "kept"


def test_empty_output_yields_empty_string():
    assert output_text({"output": []}) == ""
