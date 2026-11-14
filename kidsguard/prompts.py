"""Renders the tutor system prompt for one age band and one subject.

The prompt text lives in ``prompts/study-buddy-tutor.md`` and is parsed here, the
same way the standard is parsed rather than copied. The safety blocks are not in
that document at all: they are injected from the standard at render time, so the
refusal wording in the prompt and the refusal wording in the engine can never
disagree.

    from kidsguard import Standard, ModerationSettings
    from kidsguard.prompts import render_tutor_prompt

    text = render_tutor_prompt(
        Standard.load(), ModerationSettings.load("kidsguard-settings.json"), "8-11", "math"
    )
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .levels import CATEGORY_GROUP_LABEL, CategoryGroup, normalize_band
from .moderation import FLOOR_PRIORITY
from .settings import ModerationSettings
from .standard import Standard

PROMPT_RELATIVE_PATH = Path("prompts") / "study-buddy-tutor.md"

#: Bands this prompt covers. 16-18 needs its own tone and its own document.
PROMPT_AGE_BANDS: Tuple[str, ...] = ("8-11", "12-15")

SUBJECTS: Tuple[str, ...] = (
    "unsure",
    "math",
    "reading",
    "writing",
    "science",
    "history",
    "art",
)

#: Sections the renderer needs. Named exactly as the document's headings.
REQUIRED_SECTIONS: Tuple[str, ...] = (
    "identity",
    "teaching_sequence",
    "formatting",
    "restrictions",
) + tuple("band:%s" % band for band in PROMPT_AGE_BANDS) + tuple(
    "subject:%s" % subject for subject in SUBJECTS
)

_VERSION = re.compile(r"\*v(\d+\.\d+)[^*]*\*")


class PromptFormatError(ValueError):
    """The prompt document no longer has the sections the renderer needs."""


def normalize_subject(raw: Optional[str]) -> str:
    """Unknown subjects fall back to the menu subject instead of failing."""
    if not raw:
        return "unsure"
    key = str(raw).strip().lower()
    aliases = {"maths": "math", "ela": "reading", "english": "writing", "spelling": "writing"}
    key = aliases.get(key, key)
    return key if key in SUBJECTS else "unsure"


def _section_key(heading: str) -> str:
    key = re.sub(r"\s+", " ", heading.strip().lower())
    key = re.sub(r"\s*:\s*", ":", key)
    return key.replace(" ", "_")


def _check_sections(sections: Mapping[str, str], source: str) -> None:
    missing = [key for key in REQUIRED_SECTIONS if not sections.get(key)]
    if missing:
        raise PromptFormatError(
            "%s: missing or empty section(s): %s"
            % (source, ", ".join("## " + key for key in missing))
        )


@dataclass(frozen=True)
class TutorPromptSource:
    """The parsed prompt document."""

    sections: Mapping[str, str]
    version: str
    source: str

    @classmethod
    def load(cls, path: "str | Path | None" = None) -> "TutorPromptSource":
        if path is None:
            candidate = Path(__file__).resolve().parents[1] / PROMPT_RELATIVE_PATH
            if not candidate.exists():
                raise PromptFormatError(
                    "prompt document not found at %s, pass an explicit path" % candidate
                )
            path = candidate
        resolved = Path(path)
        return cls.from_text(resolved.read_text(encoding="utf-8"), source=str(resolved))

    @classmethod
    def from_text(cls, text: str, *, source: str = "<text>") -> "TutorPromptSource":
        sections: Dict[str, str] = {}
        current: Optional[str] = None
        buffer: List[str] = []
        for line in text.splitlines():
            if line.startswith("## "):
                if current is not None:
                    sections[current] = "\n".join(buffer).strip()
                current = _section_key(line[3:])
                buffer = []
                continue
            if current is not None:
                buffer.append(line)
        if current is not None:
            sections[current] = "\n".join(buffer).strip()

        _check_sections(sections, source)
        version_match = _VERSION.search(text)
        version = "v%s" % version_match.group(1) if version_match else "unknown"
        return cls(sections=dict(sections), version=version, source=source)

    def validate(self) -> "TutorPromptSource":
        _check_sections(self.sections, self.source)
        return self

    def section(self, key: str) -> str:
        return self.sections[key]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<TutorPromptSource %s, %d sections>" % (self.version, len(self.sections))


def _safety_block(standard: Standard, settings: ModerationSettings) -> List[str]:
    lines = ["## What you must say no to, and why", ""]
    for category in FLOOR_PRIORITY:
        if category == "self_harm":
            continue
        lines.append("- " + standard.universal_rule(category))
    lines.append("")
    lines.append("## If the child is in danger or thinking about self-harm")
    lines.append("")
    lines.append("- " + standard.universal_rule("self_harm"))
    lines.append(
        "- Name this line in your reply, in your own words, and tell them to talk to a "
        "trusted adult right now: " + settings.crisis_contact
    )
    lines.append("- Do not continue the lesson in that reply. Do not ask for details.")
    lines.append("")
    return lines


def _learning_block(standard: Standard, settings: ModerationSettings, band: str) -> List[str]:
    lines = ["## Teaching without giving the work away", ""]
    lines.append(
        "- When a child asks for the answer instead of the method, say something close "
        "to this: " + standard.learning_explanation(band)
    )
    lines.append(
        "- Explain the method and let the child produce the answer. Never write work they "
        "could hand in as their own."
    )
    lines.append("")
    lines.append("## When you must say no")
    lines.append("")
    lines.append(
        "- Say why, in words for this age, not just no. For this band the standard's own "
        "reason sounds like this: " + standard.refuse_explanation(band)
    )
    group = CategoryGroup.VIOLENCE_ADULT
    level = settings.effective_level(group, band)
    lines.append(
        "- The tool blocks some content before you see it. %s is set to %s for this band, "
        "and %s to %s. If a message is blocked, do not guess what it said."
        % (
            CATEGORY_GROUP_LABEL[group],
            level.label,
            CATEGORY_GROUP_LABEL[CategoryGroup.HARASSMENT_HATE],
            settings.effective_level(CategoryGroup.HARASSMENT_HATE, band).label,
        )
    )
    lines.append("")
    return lines


def render_tutor_prompt(
    standard: Standard,
    settings: ModerationSettings,
    age_band: str,
    subject: Optional[str] = None,
    source: Optional[TutorPromptSource] = None,
) -> str:
    """Compose the full system prompt for one band and subject."""
    band = normalize_band(age_band)
    if band not in PROMPT_AGE_BANDS:
        raise ValueError(
            "this prompt covers ages %s. Ages 16-18 need their own document, because the "
            "standard gives that band independent use rather than a study buddy."
            % " and ".join(PROMPT_AGE_BANDS)
        )
    prompt_source = (source or TutorPromptSource.load()).validate()
    settings.validate()
    chosen = normalize_subject(subject)

    def with_band(text: str) -> str:
        return text.replace("{age_band}", band)

    lines: List[str] = ["# Study helper instructions", ""]
    lines.append(with_band(prompt_source.section("identity")))
    lines.append("")
    lines.extend(_safety_block(standard, settings))
    lines.extend(_learning_block(standard, settings, band))
    lines.append("## This band")
    lines.append("")
    lines.append(with_band(prompt_source.section("band:%s" % band)))
    lines.append("")
    lines.append("## How a turn goes")
    lines.append("")
    lines.append(prompt_source.section("teaching_sequence"))
    lines.append("")
    lines.append("## This subject")
    lines.append("")
    lines.append(prompt_source.section("subject:%s" % chosen))
    lines.append("")
    lines.append("## Formatting")
    lines.append("")
    lines.append(prompt_source.section("formatting"))
    lines.append("")
    lines.append("## Restrictions")
    lines.append("")
    lines.append(prompt_source.section("restrictions"))
    lines.append("")
    lines.append(
        "Policy source: %s (%s). Prompt source: %s (%s)."
        % (
            Path(standard.source).name,
            standard.version,
            Path(prompt_source.source).name,
            prompt_source.version,
        )
    )
    return "\n".join(lines).strip() + "\n"
