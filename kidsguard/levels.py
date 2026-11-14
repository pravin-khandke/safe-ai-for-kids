"""Protection levels and category groups for the adjustable moderation settings.

The settings screen offers four protection levels per category group. Each level
is expressed as a severity ceiling: content that a classifier rates at or above
the ceiling is refused.

Severity runs 0 to 4.

    0  benign, no concern
    1  mild, a concerning reference without harm (a friendly sword fight)
    2  clearly inappropriate for a child
    3  harmful
    4  unambiguous harm (graphic violence, sexual content, a crisis disclosure)

Levels are ordered from strictest to loosest. ``ProtectionLevel.rank`` is that
ordering; lower rank means stricter. Two settings are compared by taking the
stricter of the two, which is how the per-age-band floor is enforced.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Tuple

AGE_BANDS: Tuple[str, ...] = ("8-11", "12-15", "16-18")

MAX_SEVERITY = 4


class CategoryGroup(str, Enum):
    """The two category groups the settings screen exposes."""

    HARASSMENT_HATE = "harassment_hate"
    VIOLENCE_ADULT = "violence_adult"


CATEGORY_GROUP_LABEL: Dict[CategoryGroup, str] = {
    CategoryGroup.HARASSMENT_HATE: "Harassment & Hate",
    CategoryGroup.VIOLENCE_ADULT: "Violence & Adult Content",
}


class ProtectionLevel(str, Enum):
    """Protection level, strictest first."""

    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        return _RANK[self]

    @property
    def ceiling(self) -> int:
        """Severity at or above which content is refused."""
        return _CEILING[self]

    @property
    def label(self) -> str:
        return _LABEL[self]

    @classmethod
    def parse(cls, value: str) -> "ProtectionLevel":
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        for level in cls:
            if key in (level.value, level.label.lower().replace(" ", "_")):
                return level
        raise ValueError(
            "unknown protection level %r, expected one of: %s"
            % (value, ", ".join(level.value for level in cls))
        )

    @classmethod
    def stricter(cls, first: "ProtectionLevel", second: "ProtectionLevel") -> "ProtectionLevel":
        """Return whichever level is more strict."""
        return first if first.rank <= second.rank else second


_RANK: Dict[ProtectionLevel, int] = {
    ProtectionLevel.VERY_HIGH: 0,
    ProtectionLevel.HIGH: 1,
    ProtectionLevel.MEDIUM: 2,
    ProtectionLevel.LOW: 3,
}

_CEILING: Dict[ProtectionLevel, int] = {
    ProtectionLevel.VERY_HIGH: 1,
    ProtectionLevel.HIGH: 2,
    ProtectionLevel.MEDIUM: 3,
    ProtectionLevel.LOW: 4,
}

_LABEL: Dict[ProtectionLevel, str] = {
    ProtectionLevel.VERY_HIGH: "Very High Protection",
    ProtectionLevel.HIGH: "High Protection",
    ProtectionLevel.MEDIUM: "Medium Protection",
    ProtectionLevel.LOW: "Low Protection",
}

# Wording shown for the "Safety & Protection" control, where the level applies to
# the conversation as a whole.
GENERAL_DESCRIPTIONS: Dict[ProtectionLevel, str] = {
    ProtectionLevel.VERY_HIGH: (
        "Blocks most content that could be concerning, including mild references "
        "to violence or conflict."
    ),
    ProtectionLevel.HIGH: (
        "Blocks clearly inappropriate content while allowing age appropriate "
        "discussion of challenging topics."
    ),
    ProtectionLevel.MEDIUM: (
        "Blocks harmful content while allowing more open discussion of age "
        "appropriate topics."
    ),
    ProtectionLevel.LOW: (
        "Only blocks clearly harmful content, allowing more open discussion while "
        "keeping basic safety in place."
    ),
}

# Per group wording. The source screen reused the violence wording under every
# heading, which reads as if harassment and violence mean the same thing. Each
# group gets its own sentence here so the adult can tell what they are changing.
GROUP_DESCRIPTIONS: Dict[CategoryGroup, Dict[ProtectionLevel, str]] = {
    CategoryGroup.HARASSMENT_HATE: {
        ProtectionLevel.VERY_HIGH: (
            "Blocks most teasing, name calling and insults, including mild ones "
            "aimed at another person."
        ),
        ProtectionLevel.HIGH: (
            "Blocks insults and hateful language aimed at a person or group, while "
            "allowing questions about bullying itself."
        ),
        ProtectionLevel.MEDIUM: (
            "Blocks sustained harassment and hate speech, while allowing talk about "
            "conflict and social issues."
        ),
        ProtectionLevel.LOW: (
            "Only blocks threats, severe harassment and hate speech, while keeping "
            "basic safety in place."
        ),
    },
    CategoryGroup.VIOLENCE_ADULT: {
        ProtectionLevel.VERY_HIGH: (
            "Blocks most content that could be concerning, including mild references "
            "to violence, fighting or adult themes."
        ),
        ProtectionLevel.HIGH: (
            "Blocks graphic violence and explicit adult content, while allowing age "
            "appropriate discussion of conflict, news and health."
        ),
        ProtectionLevel.MEDIUM: (
            "Blocks harmful depictions of violence and adult sexual content, while "
            "allowing more open discussion of age appropriate topics."
        ),
        ProtectionLevel.LOW: (
            "Only blocks clearly harmful content such as graphic violence and explicit "
            "sexual material, while keeping basic safety in place."
        ),
    },
}

# The refuse row of the standard is unambiguous at 8 to 11 ("anything scary,
# violent, or sexual") and narrows as children get older. The floor below makes
# the settings screen respect that: an adult can tighten a band, never loosen it
# past what the standard already demands.
AGE_BAND_FLOOR: Dict[str, ProtectionLevel] = {
    "8-11": ProtectionLevel.VERY_HIGH,
    "12-15": ProtectionLevel.MEDIUM,
    "16-18": ProtectionLevel.LOW,
}


def normalize_band(value: str) -> str:
    """Accept ``8-11``, ``8–11`` (en dash) or ``Ages 8-11`` and return ``8-11``."""
    import re

    match = re.search(r"(\d+)\s*[\u2013\u2014-]\s*(\d+)", str(value))
    if not match:
        raise ValueError(
            "unknown age band %r, expected one of: %s" % (value, ", ".join(AGE_BANDS))
        )
    band = "%s-%s" % (match.group(1), match.group(2))
    if band not in AGE_BANDS:
        raise ValueError(
            "unknown age band %r, expected one of: %s" % (value, ", ".join(AGE_BANDS))
        )
    return band


def band_floor(age_band: str) -> ProtectionLevel:
    return AGE_BAND_FLOOR[normalize_band(age_band)]


def describe_level(level: ProtectionLevel, group: "CategoryGroup | None" = None) -> str:
    """One sentence describing what a level does, for display next to the control."""
    if group is None:
        return GENERAL_DESCRIPTIONS[level]
    return GROUP_DESCRIPTIONS[group][level]
