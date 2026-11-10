"""
Text cleaner module for the NIRF RAG system.
Sanitizes raw document text while preserving mathematical formulas, markdown tables,
parameter acronyms, and institutional identifiers.
"""

import re
import unicodedata


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace characters while preserving paragraph breaks.
    Replaces Windows newlines, non-breaking spaces, and excessive line breaks.
    """
    if not text:
        return ""

    # Replace non-breaking spaces and other special space characters
    text = text.replace("\xa0", " ").replace("\u200b", "").replace("\ufeff", "")
    
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Replace multiple spaces/tabs within lines, preserving indentation minimally
    lines = []
    for line in text.split("\n"):
        # Strip trailing whitespace on each line
        line = line.rstrip()
        # Replace multiple horizontal spaces with a single space
        line = re.sub(r"[ \t]+", " ", line)
        lines.append(line)

    text = "\n".join(lines)

    # Collapse 3 or more consecutive newlines into 2 (one blank line)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_text(text: str) -> str:
    """
    Perform general text sanitization for ingestion into the RAG chunking pipeline.
    Preserves LaTeX expressions ($...$ and $$...$$), tables (| ... |), and standard unicode.
    """
    if not text:
        return ""

    # Normalize unicode to NFKC standard
    text = unicodedata.normalize("NFKC", text)

    # Normalize whitespace
    text = normalize_whitespace(text)

    # Remove excessive horizontal rules (e.g., multiple '---' lines together)
    text = re.sub(r"(\n---\s*){2,}", "\n---\n", text)

    return text


def clean_markdown_section_title(title: str) -> str:
    """
    Cleans a markdown heading line into a clean section title string.
    Removes leading '#', '**', and trailing punctuation.
    """
    if not title:
        return ""
    
    cleaned = re.sub(r"^#+\s*", "", title.strip())
    cleaned = re.sub(r"^\*+|\*+$", "", cleaned.strip())
    return cleaned.strip()

