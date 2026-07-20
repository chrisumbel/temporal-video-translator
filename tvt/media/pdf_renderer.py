"""Render the result document through output-template.html and upload the PDF."""

import logging
import os

import jinja2
from dotenv import load_dotenv
from weasyprint import HTML

from tvt.azure import blob_store

load_dotenv()

PDF_CONTAINER = os.environ["PDF_CONTAINER"]

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "output-template.html")

logger = logging.getLogger(__name__)


def render_pdf(document, workflow_id):
    """Render the result document dict to PDF bytes."""
    with open(TEMPLATE_PATH) as f:
        template = jinja2.Environment(autoescape=True).from_string(f.read())
    html = template.render(**document, workflow_id=workflow_id)
    return HTML(string=html).write_pdf()


def upload_pdf(blob_name, pdf_bytes):
    """Upload the PDF to the pdf container; return its blob URL."""
    logger.info("Uploading %d PDF bytes to %s/%s", len(pdf_bytes), PDF_CONTAINER, blob_name)
    return blob_store.upload_blob(PDF_CONTAINER, blob_name, pdf_bytes,
                                  content_type="application/pdf")
