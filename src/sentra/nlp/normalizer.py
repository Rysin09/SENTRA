"""
Text normalizer — Phase 2 NLP pipeline.

Accepts raw, untrusted complaint text and produces a sanitized, normalized
representation suitable for indicator extraction.

Security guarantees:
  - Prompt-injection patterns are detected and flagged (not silently removed).
  - Control characters are stripped before any further processing.
  - No raw text is stored beyond this module boundary; only token counts and
    quality metadata are propagated.

This module has NO external dependencies (stdlib only).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum

# ── Constants ─────────────────────────────────────────────────────────────────

# Minimum meaningful token count for a screenable submission.
MIN_SCREENABLE_TOKENS: int = 5

# Patterns that suggest prompt-injection or instruction-override attempts.
# These are flagged; the text is still processed (not discarded).
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a)", re.IGNORECASE),
    re.compile(r"<\s*/?(?:system|user|assistant|prompt)\s*>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]|\[SYS\]", re.IGNORECASE),
    re.compile(r"###\s*(?:system|instruction|prompt)", re.IGNORECASE),
    re.compile(r"-----BEGIN\s+\w+\s+KEY-----", re.IGNORECASE),
]

# Regex for characters that should be stripped outright (control chars, null bytes)
_CONTROL_CHAR_PATTERN: re.Pattern[str] = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
)

# Collapse runs of whitespace (preserving single newlines for sentence detection)
_MULTI_WHITESPACE: re.Pattern[str] = re.compile(r"[ \t]{2,}")
_MULTI_NEWLINE: re.Pattern[str] = re.compile(r"\n{3,}")


class TextQuality(str, Enum):
    """Quality of the normalized text for downstream scoring."""

    GOOD = "GOOD"
    DEGRADED = "DEGRADED"  # Low token count or unusual patterns
    FAILED = "FAILED"  # Empty, whitespace-only, or unscorable


@dataclass(frozen=True)
class NormalizedText:
    """Immutable result of the normalization pass.

    ``clean_text`` is sanitized but NOT safe for display — it still contains
    the complainant's narrative. Handle with the same care as raw text.
    ``sentences`` is used by the indicator extractor for context windows.
    """

    clean_text: str
    sentences: list[str]
    token_count: int
    char_count: int
    quality: TextQuality
    injection_detected: bool
    flags: list[str] = field(default_factory=list)

    @property
    def is_screenable(self) -> bool:
        """True if the text meets the minimum threshold for scoring."""
        return self.quality != TextQuality.FAILED and self.token_count >= MIN_SCREENABLE_TOKENS


# ── Public API ────────────────────────────────────────────────────────────────


def normalize(raw_text: str) -> NormalizedText:
    """Normalize and sanitize raw, untrusted complaint text.

    Args:
        raw_text: The complainant's free-text narrative. Treated as untrusted.

    Returns:
        A ``NormalizedText`` dataclass with clean text, token counts,
        quality assessment, and any security flags raised.

    Notes:
        - The ``clean_text`` field is sanitized but still sensitive.
        - Injection patterns are flagged but processing continues so that
          operators are aware of the attempt. The scorer will apply a
          confidence penalty when ``injection_detected`` is True.
    """
    flags: list[str] = []
    injection_detected = False

    # ── Step 1: Unicode normalization ────────────────────────────────────────
    text = unicodedata.normalize("NFC", raw_text)

    # ── Step 2: Strip control characters ─────────────────────────────────────
    text = _CONTROL_CHAR_PATTERN.sub("", text)

    # ── Step 3: Detect injection patterns (before case-folding) ──────────────
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            injection_detected = True
            flags.append(f"injection_pattern:{pattern.pattern[:40]}")

    # ── Step 4: Collapse whitespace ───────────────────────────────────────────
    text = _MULTI_WHITESPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    text = text.strip()

    # ── Step 5: Early exit for empty / whitespace-only input ─────────────────
    if not text:
        return NormalizedText(
            clean_text="",
            sentences=[],
            token_count=0,
            char_count=0,
            quality=TextQuality.FAILED,
            injection_detected=injection_detected,
            flags=flags + ["empty_text"],
        )

    # ── Step 6: Sentence splitting (heuristic) ───────────────────────────────
    sentences = _split_sentences(text)

    # ── Step 7: Token count (word-level, lowercased) ──────────────────────────
    # Tokenize on the lowercased version; clean_text retains original casing.
    lower = text.lower()
    tokens = _tokenize(lower)
    token_count = len(tokens)

    # ── Step 8: Quality assessment ────────────────────────────────────────────
    if token_count == 0:
        quality = TextQuality.FAILED
        flags.append("zero_tokens_after_normalization")
    elif token_count < MIN_SCREENABLE_TOKENS:
        quality = TextQuality.DEGRADED
        flags.append(f"low_token_count:{token_count}")
    elif injection_detected:
        quality = TextQuality.DEGRADED
    else:
        quality = TextQuality.GOOD

    return NormalizedText(
        clean_text=text,
        sentences=sentences,
        token_count=token_count,
        char_count=len(text),
        quality=quality,
        injection_detected=injection_detected,
        flags=flags,
    )


# ── Private helpers ───────────────────────────────────────────────────────────


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using a simple heuristic regex.

    Splits on '. ', '! ', '? ', or newlines.  This is intentionally
    simple — no NLTK dependency.  Accurate enough for indicator context windows.
    """
    # Split on sentence-ending punctuation followed by whitespace or end-of-string
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase word tokens, stripping punctuation."""
    return re.findall(r"\b[a-z][a-z'\-]*[a-z]\b|\b[a-z]\b", text.lower())
