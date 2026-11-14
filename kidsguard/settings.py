"""The content moderation settings that the settings screen edits and saves.

One object holds everything the screen exposes: the AI moderation toggle, the two
protection levels, the custom word list with its own toggle, and homework mode.
It round trips to JSON so a settings file can be inspected, diffed and committed
alongside a deployment.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .levels import (
    AGE_BANDS,
    CategoryGroup,
    ProtectionLevel,
    band_floor,
    normalize_band,
)

SCHEMA_VERSION = 1

DEFAULT_LEVELS: Dict[CategoryGroup, ProtectionLevel] = {
    CategoryGroup.HARASSMENT_HATE: ProtectionLevel.HIGH,
    CategoryGroup.VIOLENCE_ADULT: ProtectionLevel.HIGH,
}

DEFAULT_CRISIS_CONTACT = (
    "988 Suicide & Crisis Lifeline: call or text 988 (United States), "
    "or your local emergency number"
)

MAX_CUSTOM_WORDS = 500
MAX_CUSTOM_WORD_LENGTH = 60
MIN_CUSTOM_WORD_LENGTH = 2


class SettingsError(ValueError):
    """The settings payload is not usable."""


def normalize_word(raw: str) -> str:
    """Canonical form of a filtered word: lowercase, single spaces, trimmed."""
    word = re.sub(r"\s+", " ", str(raw).strip().strip("\"'")).lower()
    if not word:
        raise SettingsError("a filtered word cannot be empty")
    if len(word) < MIN_CUSTOM_WORD_LENGTH:
        raise SettingsError(
            "%r is too short, use at least %d characters"
            % (raw, MIN_CUSTOM_WORD_LENGTH)
        )
    if len(word) > MAX_CUSTOM_WORD_LENGTH:
        raise SettingsError(
            "%r is too long, the limit is %d characters"
            % (word, MAX_CUSTOM_WORD_LENGTH)
        )
    if any(ord(char) < 32 for char in word):
        raise SettingsError("%r contains control characters" % word)
    return word


def _coerce_bool(value: Any, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on"):
            return True
        if lowered in ("0", "false", "no", "off"):
            return False
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    raise SettingsError("%s must be true or false, got %r" % (name, value))


@dataclass
class ModerationSettings:
    """Everything the content moderation settings screen owns."""

    moderation_enabled: bool = True
    levels: Dict[CategoryGroup, ProtectionLevel] = field(
        default_factory=lambda: dict(DEFAULT_LEVELS)
    )
    custom_word_filtering: bool = True
    custom_words: List[str] = field(default_factory=list)
    homework_mode: bool = False
    crisis_contact: str = DEFAULT_CRISIS_CONTACT

    # -- validation -------------------------------------------------------
    def validate(self) -> "ModerationSettings":
        if not self.crisis_contact or not self.crisis_contact.strip():
            raise SettingsError(
                "crisis_contact cannot be empty: a self-harm disclosure always names "
                "a real crisis line, so the engine refuses to start without one"
            )
        for group in CategoryGroup:
            if group not in self.levels:
                raise SettingsError("missing protection level for %s" % group.value)
            if not isinstance(self.levels[group], ProtectionLevel):
                raise SettingsError(
                    "level for %s must be a ProtectionLevel, got %r"
                    % (group.value, self.levels[group])
                )
        words: List[str] = []
        for raw in self.custom_words:
            word = normalize_word(raw)
            if word not in words:
                words.append(word)
        if len(words) > MAX_CUSTOM_WORDS:
            raise SettingsError(
                "at most %d filtered words are supported, got %d"
                % (MAX_CUSTOM_WORDS, len(words))
            )
        self.custom_words = words
        return self

    # -- settings screen actions -----------------------------------------
    def set_level(self, group: CategoryGroup, level: ProtectionLevel) -> None:
        self.levels[CategoryGroup(group)] = ProtectionLevel(level)

    def set_all_levels(self, level: ProtectionLevel) -> None:
        """The "Safety & Protection" control, which sets every group at once."""
        for group in CategoryGroup:
            self.levels[group] = ProtectionLevel(level)

    @property
    def global_level(self) -> Optional[ProtectionLevel]:
        """The shared level, or None when the groups have been split apart."""
        levels = {self.levels[group] for group in CategoryGroup}
        if len(levels) == 1:
            return levels.pop()
        return None

    def add_word(self, word: str) -> str:
        """Add one filtered word, returning its canonical form."""
        canonical = normalize_word(word)
        if canonical not in self.custom_words:
            if len(self.custom_words) >= MAX_CUSTOM_WORDS:
                raise SettingsError(
                    "at most %d filtered words are supported" % MAX_CUSTOM_WORDS
                )
            self.custom_words.append(canonical)
        return canonical

    def remove_word(self, word: str) -> bool:
        canonical = normalize_word(word)
        if canonical in self.custom_words:
            self.custom_words.remove(canonical)
            return True
        return False

    def clear_custom_words(self) -> None:
        """The "Clear All" action: empties the word list, changes nothing else."""
        self.custom_words.clear()

    def reset_to_default(self) -> None:
        """The "Reset to Default" action: restores every field, word list included."""
        defaults = ModerationSettings()
        self.moderation_enabled = defaults.moderation_enabled
        self.levels = dict(defaults.levels)
        self.custom_word_filtering = defaults.custom_word_filtering
        self.custom_words = list(defaults.custom_words)
        self.homework_mode = defaults.homework_mode
        self.crisis_contact = defaults.crisis_contact

    # -- effective policy -------------------------------------------------
    def effective_level(self, group: CategoryGroup, age_band: str) -> ProtectionLevel:
        """The level actually applied for a band: the stricter of setting and floor."""
        group = CategoryGroup(group)
        return ProtectionLevel.stricter(self.levels[group], band_floor(age_band))

    def requested_level(self, group: CategoryGroup) -> ProtectionLevel:
        return self.levels[CategoryGroup(group)]

    def clamp_note(self, group: CategoryGroup, age_band: str) -> Optional[str]:
        """Explain a mismatch between what was requested and what is applied."""
        normalized = normalize_band(age_band)
        requested = self.levels[CategoryGroup(group)]
        applied = self.effective_level(group, normalized)
        if requested is applied:
            return None
        return (
            "%s is set to %s, applied as %s for ages %s because the standard's "
            "refuse row sets that floor."
            % (
                group.value.replace("_", " "),
                requested.label,
                applied.label,
                normalized,
            )
        )

    @property
    def word_filter_active(self) -> bool:
        return self.custom_word_filtering and bool(self.custom_words)

    def matches_custom_word(self, text: str) -> Optional[str]:
        """Return the first filtered word present in ``text`` as a whole word."""
        if not self.word_filter_active:
            return None
        for word in self.custom_words:
            pattern = re.compile(
                r"(?<![\w])" + re.escape(word) + r"(?:s|es|ed|ing|d)?(?![\w])",
                re.IGNORECASE,
            )
            if pattern.search(text):
                return word
        return None

    # -- serialisation ----------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "moderation_enabled": self.moderation_enabled,
            "levels": {
                group.value: self.levels[group].value for group in CategoryGroup
            },
            "custom_word_filtering": self.custom_word_filtering,
            "custom_words": list(self.custom_words),
            "homework_mode": self.homework_mode,
            "crisis_contact": self.crisis_contact,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ModerationSettings":
        if not isinstance(payload, Mapping):
            raise SettingsError("settings payload must be a mapping")
        schema = payload.get("schema_version", SCHEMA_VERSION)
        if schema != SCHEMA_VERSION:
            raise SettingsError(
                "unsupported settings schema_version %r, this build reads %d"
                % (schema, SCHEMA_VERSION)
            )

        levels = dict(DEFAULT_LEVELS)
        raw_levels = payload.get("levels", {})
        if not isinstance(raw_levels, Mapping):
            raise SettingsError("levels must be a mapping of group to level")
        for key, value in raw_levels.items():
            try:
                group = CategoryGroup(str(key))
            except ValueError:
                raise SettingsError("unknown category group %r" % key) from None
            try:
                levels[group] = ProtectionLevel.parse(str(value))
            except ValueError as exc:
                raise SettingsError(str(exc)) from None

        raw_words = payload.get("custom_words", [])
        if not isinstance(raw_words, (list, tuple)):
            raise SettingsError("custom_words must be a list")

        settings = cls(
            moderation_enabled=_coerce_bool(
                payload.get("moderation_enabled", True), "moderation_enabled"
            ),
            levels=levels,
            custom_word_filtering=_coerce_bool(
                payload.get("custom_word_filtering", True), "custom_word_filtering"
            ),
            custom_words=[str(word) for word in raw_words],
            homework_mode=_coerce_bool(payload.get("homework_mode", False), "homework_mode"),
            crisis_contact=str(payload.get("crisis_contact", DEFAULT_CRISIS_CONTACT)),
        )
        return settings.validate()

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "ModerationSettings":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SettingsError("settings file is not valid JSON: %s" % exc) from None
        return cls.from_dict(payload)

    def save(self, path: "str | Path") -> Path:
        """Write the settings atomically, so an interrupted save cannot corrupt them."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=str(target.parent), delete=False
        )
        try:
            handle.write(self.validate().to_json())
            handle.flush()
            os.fsync(handle.fileno())
        finally:
            handle.close()
        os.replace(handle.name, target)
        return target

    @classmethod
    def load(cls, path: "str | Path") -> "ModerationSettings":
        target = Path(path)
        if not target.exists():
            return cls().validate()
        return cls.from_json(target.read_text(encoding="utf-8"))

    # -- convenience ------------------------------------------------------
    @property
    def available_age_bands(self) -> Tuple[str, ...]:
        return AGE_BANDS

    def summary(self) -> Dict[str, str]:
        return {
            group.value: self.requested_level(group).value for group in CategoryGroup
        }


def default_settings() -> ModerationSettings:
    """A validated settings object with the screen's defaults."""
    return ModerationSettings().validate()
