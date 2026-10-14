"""Deterministic PHI redaction that runs before the AI adapter boundary."""

import re
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple


@dataclass(frozen=True)
class RedactionResult:
    text: str
    counts: Dict[str, int]


PATTERNS = (
    ("email", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE), "[EMAIL]"),
    ("id", re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE), "[ID]"),
    (
        "phone",
        re.compile(r"(?<!\d)(?:\+?65[\s-]?)?[689]\d{3}[\s-]?\d{4}(?!\d)"),
        "[PHONE]",
    ),
)
LABELLED_NAME = re.compile(
    r"(?i:\b(?:my name is|patient name is|name:)\s+)(?P<name>[A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+){0,2})"
)
TITLED_NAME = re.compile(
    r"\b(?:Dr|Mr|Mrs|Ms)\.?\s+[A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+){0,2}\b"
)


def _candidate_names(names: Iterable[str]) -> Tuple[str, ...]:
    cleaned = set()
    for value in names:
        without_demo_suffix = re.sub(r"\s*\([^)]*\)\s*$", "", value).strip()
        without_title = re.sub(r"^(?:dr\.?|mr\.?|mrs\.?|ms\.?)\s+", "", without_demo_suffix, flags=re.I)
        for candidate in (without_demo_suffix, without_title):
            if len(candidate) >= 3:
                cleaned.add(candidate)
    return tuple(sorted(cleaned, key=len, reverse=True))


def redact_phi(text: str, known_names: Iterable[str] = ()) -> RedactionResult:
    redacted = text
    counts: Dict[str, int] = {"name": 0, "id": 0, "phone": 0, "email": 0}

    for pattern in (LABELLED_NAME, TITLED_NAME):
        redacted, count = pattern.subn("[NAME]", redacted)
        counts["name"] += count

    for name in _candidate_names(known_names):
        redacted, count = re.subn(rf"\b{re.escape(name)}\b", "[NAME]", redacted, flags=re.I)
        counts["name"] += count

    for label, pattern, replacement in PATTERNS:
        redacted, count = pattern.subn(replacement, redacted)
        counts[label] += count

    return RedactionResult(text=redacted, counts=counts)


class DeterministicScribe:
    """A replaceable adapter; it can only receive already-redacted text."""

    def summarize(self, redacted_text: str) -> str:
        if any(token in redacted_text for token in ("@", "+65")):
            raise ValueError("Unredacted contact data reached the AI boundary")
        normalized = " ".join(redacted_text.split())
        return f"AI draft — {normalized[:360]}"
