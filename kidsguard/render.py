"""Text rendering of the content moderation settings screen.

The renderer reads the settings object and the standard, and writes the screen an
adult sees. Keeping it here means the CLI demo and any future web form show the
same wording, and the level descriptions cannot drift between the two.
"""

from __future__ import annotations

from typing import List, Optional

from .levels import (
    CATEGORY_GROUP_LABEL,
    CategoryGroup,
    ProtectionLevel,
    describe_level,
    normalize_band,
)
from .moderation import Decision
from .settings import ModerationSettings
from .standard import Standard

BUILT_IN_TEXT = (
    "All conversations are automatically protected against harmful content like "
    "explicit violence, sexual content, and harassment. No control on this screen can "
    "weaken that: the standard requires these refusals at every age, and a self-harm "
    "message always names a crisis line."
)

NO_WORDS_TEXT = "No filtered words added yet. Type a word and press Enter to add it."


def _mark(flag: bool) -> str:
    return "[x]" if flag else "[ ]"


def _title(text: str, underline: str = "=") -> str:
    return "%s\n%s" % (text, underline * len(text))


def render_settings(
    settings: ModerationSettings,
    standard: Optional[Standard] = None,
    *,
    age_band: Optional[str] = None,
    child_name: Optional[str] = None,
    config_path: Optional[str] = None,
    saved: Optional[bool] = None,
) -> str:
    """Render the whole settings screen as plain text."""
    who = child_name.strip() if child_name else "your child"
    lines = [
        _title("Content Moderation"),
        "",
        "Customize how strictly %s's conversations are moderated" % who,
        "",
        _title("Built-in Safety Features", "-"),
        *_wrap(BUILT_IN_TEXT),
        "",
        _title("Enable Content Moderation", "-"),
        "  %s Use AI to automatically filter inappropriate content" % _mark(settings.moderation_enabled),
        "      When this is off, the adjustable categories stop filtering. The built-in",
        "      protection above stays on.",
        "",
        _title("Safety & Protection", "-"),
    ]

    band = normalize_band(age_band) if age_band else None
    lines.extend(_level_block(ProtectionLevel, None, settings, band, "  "))
    lines.append("")

    for group in CategoryGroup:
        lines.append(_title(CATEGORY_GROUP_LABEL[group], "-"))
        lines.extend(_level_block(ProtectionLevel, group, settings, band, "  "))
        lines.append("")

    lines.append(_title("Additional Settings", "-"))
    lines.append(
        "  %s Homework Mode" % _mark(settings.homework_mode)
        + "\n      Restricts the conversation to schoolwork tools only."
    )
    lines.append(
        "  %s Custom Word Filtering" % _mark(settings.custom_word_filtering)
        + "\n      Blocks words the adult added to the filter list below."
    )
    lines.append("")
    lines.append(_title("Custom Word Filters", "-"))
    if settings.custom_words:
        for index, word in enumerate(settings.custom_words, start=1):
            lines.append("  %2d. %s" % (index, word))
    else:
        lines.append("  " + NO_WORDS_TEXT)
    lines.append("")

    if standard is not None:
        lines.append(
            "Policy language: %s (%s)" % (standard.source.split("/")[-1], standard.version)
        )
    line = "Clear All: empties the word list   |   Reset to Default: restores every setting"
    lines.append(line)
    if config_path:
        status = {None: "", True: "  [saved]", False: "  [not saved]"}[saved]
        lines.append("Save Changes -> %s%s" % (config_path, status))
        if saved is False:
            lines.append("  No settings changed, so nothing was written.")
    return "\n".join(lines)


def _level_block(levels, group, settings: ModerationSettings, band, indent: str):
    lines = []
    shared = settings.global_level
    for level in levels:
        if group is None:
            current = settings.moderation_enabled and shared is level
            note = "" if shared is not None else "  (levels were set separately below)"
            if shared is None:
                current = False
            if band is not None and current and shared is not None:
                applied = [
                    settings.effective_level(member, band) for member in CategoryGroup
                ]
                tighter = [
                    item for item in applied if item is not None and item.rank < shared.rank
                ]
                if tighter:
                    note = "  (applied as %s for ages %s)" % (tighter[0].label, band)
        else:
            current = settings.levels[group] is level
            note = ""
            if band is not None:
                applied = settings.effective_level(group, band)
                if applied is not level and current:
                    note = "  (applied as %s for ages %s)" % (applied.label, band)
        lines.append("%s%s %s%s" % (indent, _mark(current), level.label, note))
        lines.extend(_wrap(describe_level(level, group), indent=indent + "    "))
    return lines


def _wrap(text: str, width: int = 78, indent: str = "  ") -> List[str]:
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) > width - len(indent):
            lines.append(indent + current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(indent + current)
    return lines


def render_decision(decision: Decision, label: str = "") -> str:
    """One-line-plus-explanation view of a moderation decision."""
    header = "%s%s  [%s]  reason=%s" % (
        (label + ": ") if label else "",
        decision.action.value,
        decision.category or "-",
        decision.reason,
    )
    parts = [header]
    if decision.applied_level is not None:
        parts.append("  level in force: %s" % decision.applied_level.label)
    if decision.evidence:
        parts.append("  matched: %s" % ", ".join(decision.evidence))
    if decision.suppressed:
        parts.append("  also seen (not shown to child): %s" % ", ".join(decision.suppressed))
    if decision.explanation:
        parts.append("")
        for line in decision.explanation.splitlines():
            parts.append("  " + line if line else "")
    return "\n".join(parts)
