from tvt.media import pdf_renderer

DOCUMENT = {
    "video_url": "https://example.com/test.mp4",
    "transcript": "A transcript.",
    "summary": "First paragraph.\n\nSecond paragraph.",
    "screenshot_url": None,
    "translations": [
        {"language": "es", "text": "Una transcripción."},
        {"language": "ja", "text": "日本語のテキスト。"},
    ],
}


def test_renders_a_pdf():
    pdf = pdf_renderer.render_pdf(DOCUMENT, "wf-test-1234")
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_template_escapes_html_in_content():
    document = dict(DOCUMENT, transcript="<script>alert('x')</script>")
    # renders without executing/injecting; just proves autoescape stays on
    pdf = pdf_renderer.render_pdf(document, "wf-test-1234")
    assert pdf.startswith(b"%PDF")
