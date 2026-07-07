# -*- coding: utf-8 -*-
"""Shared helpers for the extraction pipeline."""
import re

CSV_COLS = [
    "id", "word", "phonetic", "part_of_speech", "meanings", "word_forms",
    "core_usages", "related_words", "examples_en", "examples_cn", "exam_tags",
    "common_errors", "source_page", "source_batch", "source_text",
    "confidence", "status",
]

VALID_CONFIDENCE = {"high", "medium", "low"}
# word must start with a letter; allow letters/digits/space and . ' ( ) / & -
WORD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9 .'()/&\-]*$")


def clean_id_part(word):
    return re.sub(r"[^a-z0-9]", "", word.lower()) or "entry"


def join_cell(items):
    return "；".join(str(x) for x in items if str(x).strip())


def usage_cell(usages):
    parts = []
    for u in usages or []:
        pat = (u.get("pattern") or "").strip()
        mean = (u.get("meaning") or "").strip()
        if pat:
            parts.append(pat + (f"（{mean}）" if mean else ""))
    return "；".join(parts)


def is_probably_garbage(word):
    """Heuristic: reject OCR fragments like 'ing', 'ess', 'None'."""
    w = (word or "").strip()
    if not w or not WORD_RE.match(w):
        return True
    if w.lower() in {"none", "null"}:
        return True
    # single fragment endings that are almost never headwords
    if w.lower() in {"ing", "ess", "ed", "tion", "ly", "ment"}:
        return True
    return False
