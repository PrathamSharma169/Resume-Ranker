"""
JD Loader — Load Job Description from DOCX files.
Preserves section structure, headings, and bullet points.
"""

from typing import Union
from pathlib import Path
from docx import Document
from src.utils.logger import get_logger
from src.utils.text_utils import normalize_text

logger = get_logger("jd_loader")


def load_jd_from_docx(filepath: Union[str, Path]) -> dict:
    """
    Load a Job Description from a DOCX file.
    Returns structured representation with sections.

    Returns:
        dict with keys: raw_text, sections, paragraphs, metadata
    """
    filepath = Path(filepath)
    if not filepath.exists():
        logger.error(f"JD file not found: {filepath}")
        return {"raw_text": "", "sections": {}, "paragraphs": [], "metadata": {}}

    logger.info(f"Loading JD from: {filepath}")
    doc = Document(str(filepath))

    paragraphs = []
    sections = {}
    current_section = "Introduction"
    section_paragraphs = []

    for para in doc.paragraphs:
        text = normalize_text(para.text)
        if not text:
            continue

        style_name = para.style.name if para.style else ""

        # Detect section headings
        is_heading = (
            "Heading" in style_name
            or para.runs and para.runs[0].bold
            or text.isupper() and len(text) < 100
        )

        if is_heading and len(text) > 2:
            # Save previous section
            if section_paragraphs:
                sections[current_section] = "\n".join(section_paragraphs)

            current_section = text.strip(":#").strip()
            section_paragraphs = []
            paragraphs.append({"text": text, "type": "heading", "section": current_section})
        else:
            section_paragraphs.append(text)
            # Detect bullet points
            is_bullet = text.startswith(("•", "-", "–", "→", "*", "►"))
            para_type = "bullet" if is_bullet else "paragraph"
            paragraphs.append({
                "text": text,
                "type": para_type,
                "section": current_section,
            })

    # Save last section
    if section_paragraphs:
        sections[current_section] = "\n".join(section_paragraphs)

    # Build full raw text
    raw_text = "\n".join(p["text"] for p in paragraphs)

    result = {
        "raw_text": raw_text,
        "sections": sections,
        "paragraphs": paragraphs,
        "metadata": {
            "filename": filepath.name,
            "num_sections": len(sections),
            "num_paragraphs": len(paragraphs),
            "total_chars": len(raw_text),
        }
    }

    logger.info(
        f"JD loaded: {len(sections)} sections, "
        f"{len(paragraphs)} paragraphs, "
        f"{len(raw_text)} characters"
    )
    return result
