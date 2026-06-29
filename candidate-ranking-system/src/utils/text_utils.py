"""
Text Utilities
Text normalization and processing functions.
"""

import re
import unicodedata
from typing import Optional


def normalize_text(text: str) -> str:
    """
    Normalize text for consistent processing.
    Preserves domain-specific terms (LLM, FAISS, LoRA, etc.)
    """
    if not text:
        return ""
    # Unicode normalization
    text = unicodedata.normalize("NFKD", text)
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_text(text: str) -> str:
    """Clean text by removing special characters while preserving meaning."""
    if not text:
        return ""
    text = normalize_text(text)
    # Remove control characters
    text = "".join(c for c in text if not unicodedata.category(c).startswith("C") or c in ("\n", "\t"))
    return text.strip()


def text_to_lower(text: str) -> str:
    """Convert to lowercase while preserving the original for reference."""
    return text.lower() if text else ""


def extract_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    if not text:
        return []
    # Simple sentence splitting
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def combine_text_fields(*fields: Optional[str], separator: str = " ") -> str:
    """Combine multiple text fields, filtering None/empty values."""
    parts = [f.strip() for f in fields if f and f.strip()]
    return separator.join(parts)


def contains_any(text: str, terms: list[str], case_insensitive: bool = True) -> bool:
    """Check if text contains any of the given terms."""
    if not text or not terms:
        return False
    if case_insensitive:
        text_lower = text.lower()
        return any(term.lower() in text_lower for term in terms)
    return any(term in text for term in terms)


def count_term_occurrences(text: str, term: str, case_insensitive: bool = True) -> int:
    """Count occurrences of a term in text."""
    if not text or not term:
        return 0
    if case_insensitive:
        return text.lower().count(term.lower())
    return text.count(term)


def truncate_text(text: str, max_length: int = 500) -> str:
    """Truncate text to max length, ending at word boundary."""
    if not text or len(text) <= max_length:
        return text
    truncated = text[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.8:
        return truncated[:last_space] + "..."
    return truncated + "..."


# Common role level keywords for seniority detection
SENIORITY_KEYWORDS = {
    "intern": 0,
    "junior": 1,
    "associate": 1,
    "entry": 1,
    "mid": 2,
    "senior": 3,
    "lead": 4,
    "principal": 5,
    "staff": 5,
    "director": 6,
    "vp": 7,
    "head": 6,
    "chief": 8,
    "cto": 8,
    "ceo": 8,
}


def estimate_seniority(title: str) -> int:
    """Estimate seniority level from job title (0-8 scale)."""
    if not title:
        return 2  # default to mid-level
    title_lower = title.lower()
    max_level = 2  # default
    for keyword, level in SENIORITY_KEYWORDS.items():
        if keyword in title_lower:
            max_level = max(max_level, level)
    return max_level


# Company size ordering
COMPANY_SIZE_ORDER = {
    "1-10": 1,
    "11-50": 2,
    "51-200": 3,
    "201-500": 4,
    "501-1000": 5,
    "1001-5000": 6,
    "5001-10000": 7,
    "10001+": 8,
}


def encode_company_size(size: str) -> int:
    """Encode company size string to ordinal value."""
    return COMPANY_SIZE_ORDER.get(size, 0)
