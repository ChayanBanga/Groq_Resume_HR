"""
Anti-cheat / integrity layer for the resume screener.

Candidates increasingly try to game LLM-based resume screeners using tricks
that are invisible to a human reader but fully visible to the text extractor
that feeds an LLM. This module runs BEFORE the resume text ever reaches the
scoring prompt, and is intentionally kept as a separate pass rather than
folded into the scoring prompt itself -- an injection attempt embedded in the
resume should not get a chance to talk its way past the very call that is
supposed to catch it.

Three categories of cheat are covered:
  1. Hidden / invisible text (white-on-white, near-zero font size, text
     pushed off the visible page area, zero-width unicode characters).
  2. Prompt injection attempts (text addressed to "the AI/model/system",
     fake system/assistant tags, instructions to ignore prior context or
     to assign a specific score).
  3. Keyword stuffing (a required skill repeated far more than a genuine
     resume ever would, usually with no supporting context elsewhere).

Nothing here auto-rejects a candidate. Everything here produces a flag +
human-readable reason so the score stays informative and a person can
glance at flagged resumes before any decision goes out.
"""

import re
import unicodedata

import fitz  # PyMuPDF
from docx import Document


# ---------------------------------------------------------------------------
# 1. Hidden / invisible text detection
# ---------------------------------------------------------------------------

TINY_FONT_THRESHOLD_PT = 5.0
NEAR_WHITE_CHANNEL_MIN = 245  # out of 255, per RGB channel

ZERO_WIDTH_CHARS = {
    "\u200b": "zero-width space",
    "\u200c": "zero-width non-joiner",
    "\u200d": "zero-width joiner",
    "\ufeff": "zero-width no-break space (BOM)",
    "\u2060": "word joiner",
}


def detect_hidden_text_pdf(file_path: str) -> list[str]:
    """Inspect PDF text spans for white/near-white color, tiny font size,
    or placement outside the visible page area."""
    reasons = []
    doc = fitz.open(file_path)

    for page_index, page in enumerate(doc):
        page_rect = page.rect
        text_dict = page.get_text("dict")

        for block in text_dict.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue

                    size = span.get("size", 0)
                    color_int = span.get("color", 0)
                    bbox = span.get("bbox", None)

                    r = (color_int >> 16) & 255
                    g = (color_int >> 8) & 255
                    b = color_int & 255

                    snippet = text[:50]

                    if size and size < TINY_FONT_THRESHOLD_PT:
                        reasons.append(
                            f"Page {page_index + 1}: text rendered at {size:.1f}pt "
                            f"(effectively invisible) — \"{snippet}\""
                        )

                    if r >= NEAR_WHITE_CHANNEL_MIN and g >= NEAR_WHITE_CHANNEL_MIN and b >= NEAR_WHITE_CHANNEL_MIN:
                        reasons.append(
                            f"Page {page_index + 1}: near-white text color "
                            f"(likely invisible on white background) — \"{snippet}\""
                        )

                    if bbox:
                        x0, y0, x1, y1 = bbox
                        if x1 < 0 or y1 < 0 or x0 > page_rect.width or y0 > page_rect.height:
                            reasons.append(
                                f"Page {page_index + 1}: text positioned outside the "
                                f"visible page area — \"{snippet}\""
                            )

    doc.close()
    return reasons


def detect_hidden_text_docx(file_path: str) -> list[str]:
    """Inspect DOCX runs for the 'hidden'/vanish property, white font color,
    or near-zero font size."""
    reasons = []
    doc = Document(file_path)

    for para in doc.paragraphs:
        for run in para.runs:
            text = run.text.strip()
            if not text:
                continue
            snippet = text[:50]

            if run.font.hidden:
                reasons.append(f"Hidden run (Word 'vanish' formatting) — \"{snippet}\"")

            size = run.font.size
            if size is not None and size.pt < TINY_FONT_THRESHOLD_PT:
                reasons.append(f"Text rendered at {size.pt}pt (effectively invisible) — \"{snippet}\"")

            color = run.font.color
            if color is not None and color.rgb is not None:
                rgb = str(color.rgb)
                if rgb.upper() in ("FFFFFF", "FEFEFE", "FDFDFD"):
                    reasons.append(f"White-colored text — \"{snippet}\"")

    return reasons


def detect_zero_width_chars(resume_text: str) -> list[str]:
    """Zero-width/invisible unicode characters are sometimes used to hide
    injected instructions inside otherwise normal-looking words."""
    reasons = []
    for char, description in ZERO_WIDTH_CHARS.items():
        count = resume_text.count(char)
        if count > 0:
            reasons.append(f"{count}x {description} character found in resume text")
    return reasons


# ---------------------------------------------------------------------------
# 2. Prompt injection detection
# ---------------------------------------------------------------------------

INJECTION_PATTERNS = [
    r"ignore (all|any|the|previous|above)?\s*(previous|prior|above)?\s*instructions",
    r"disregard (all|any|the)?\s*(previous|prior|above)\s*(instructions|prompt)",
    r"you are (now|no longer|actually)",
    r"forget (your|the|all)?\s*(previous|prior)\s*(prompt|instructions|context)",
    r"new (system )?instructions?\s*:",
    r"^\s*system\s*:",
    r"^\s*assistant\s*:",
    r"as an ai( language)? model",
    r"override (the|your)?\s*(scoring|evaluation|instructions|rules)",
    r"(give|assign|rate|score|mark) (this|the)?\s*(candidate|resume|applicant)?\s*(a |as )?(perfect|10/10|100%|100 ?(out of|/) ?100|top score|strong fit)",
    r"this (candidate|resume|applicant) (is|should be) (the best|highly qualified|a perfect match|an ideal fit)",
    r"do not (flag|reject|deduct|penalize)",
    r"respond with (only )?[\"']?(strong fit|100)",
    r"<\|.*?\|>",       # fake special tokens e.g. <|system|>
    r"\[/?inst\]",      # fake instruction-format tokens
    r"\[/?system\]",
]

_COMPILED_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in INJECTION_PATTERNS]


def detect_prompt_injection(resume_text: str) -> list[str]:
    """Regex sweep for language addressed at an AI evaluator rather than a
    human recruiter. Runs on the raw extracted text, independent of and
    before the scoring LLM call."""
    reasons = []
    for pattern in _COMPILED_INJECTION_PATTERNS:
        match = pattern.search(resume_text)
        if match:
            snippet = resume_text[max(0, match.start() - 20): match.end() + 20].strip()
            reasons.append(f"Suspicious instruction-like phrase found: \"...{snippet}...\"")
    return reasons


# ---------------------------------------------------------------------------
# 3. Keyword stuffing detection
# ---------------------------------------------------------------------------

STUFFING_COUNT_THRESHOLD = 5


def detect_keyword_stuffing(resume_text: str, required_skills: list[str]) -> list[str]:
    """A required skill repeated far more than a genuine resume would,
    usually confined to a skills list with no supporting mentions in any
    project/experience description, is a common gaming tactic against
    embedding-based skill matchers."""
    reasons = []
    lower_text = resume_text.lower()

    for skill in required_skills:
        skill_lower = skill.lower().strip()
        if not skill_lower:
            continue
        count = lower_text.count(skill_lower)
        if count >= STUFFING_COUNT_THRESHOLD:
            reasons.append(
                f"'{skill}' appears {count} times in the resume — possible keyword stuffing"
            )
    return reasons


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_integrity_checks(
    file_path: str,
    resume_text: str,
    required_skills: list[str],
    file_ext: str,
) -> tuple[bool, list[str]]:
    """Run every integrity check and return (flagged, reasons)."""
    reasons: list[str] = []

    if file_ext == ".pdf":
        reasons.extend(detect_hidden_text_pdf(file_path))
    elif file_ext == ".docx":
        reasons.extend(detect_hidden_text_docx(file_path))

    reasons.extend(detect_zero_width_chars(resume_text))
    reasons.extend(detect_prompt_injection(resume_text))
    reasons.extend(detect_keyword_stuffing(resume_text, required_skills))

    # De-duplicate while preserving order (hidden-text scans can repeat
    # near-identical spans for wrapped lines).
    seen = set()
    unique_reasons = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            unique_reasons.append(r)

    return (len(unique_reasons) > 0, unique_reasons)
