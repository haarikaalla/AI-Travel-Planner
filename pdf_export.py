"""
pdf_export.py — backwards-compatible facade.

The renderer moved to :mod:`travel_planner.exporters.pdf`. Import from there in
new code; this shim keeps ``from pdf_export import generate_pdf`` working.
"""

from travel_planner.exporters.documents import (
    generate_ics,
    generate_markdown,
    generate_text,
)
from travel_planner.exporters.pdf import build_styles, generate_pdf

__all__ = [
    "build_styles",
    "generate_ics",
    "generate_markdown",
    "generate_pdf",
    "generate_text",
]
