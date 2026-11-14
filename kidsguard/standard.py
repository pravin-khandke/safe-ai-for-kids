"""Reader for the printable standard, which stays the single source of policy language.

Nothing in this package hard codes refusal wording. Every explanation handed back
to a child is quoted out of ``standard/using-ai-at-home-and-school.md``:

* the ten bullets under "Always, at every age", used as the reason line for each
  non-negotiable category;
* the bolded "When it refuses ..." quote in each age band's refuse cell, used as
  the age appropriate "why" that the standard requires;
* the quoted learning-integrity line in each age band's allowed cell, used when a
  child asks for the answer instead of the method.

The parser fails loudly. If the standard's structure moves, ``StandardFormatError``
is raised rather than silently returning half a policy.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from .levels import AGE_BANDS, normalize_band

DEFAULT_RELATIVE_PATH = Path("standard") / "using-ai-at-home-and-school.md"

UNIVERSAL_HEADING = "always, at every age"

ROW_ALLOWED = "what's allowed"
ROW_ADULT = "what the adult checks"
ROW_REFUSE = "what the tool must refuse"

#: Category key -> a distinctive phrase that must appear in exactly one of the
#: universal bullets. The bullet itself becomes the refusal reason.
UNIVERSAL_BULLET_MARKERS: Dict[str, str] = {
    "self_identification": "identify itself as an ai",
    "self_harm": "disordered eating",
    "sexual_content_minor": "sexual content with a child",
    "deepfake_nudify": "nude images of any real person",
    "hide_from_parent": "hide activity from a parent",
    "pii_solicitation": "collect or solicit a child's personal information",
}

_REFUSE_QUOTE = re.compile(r"\*\*When it refuses[^*]*\*\*\s*\"([^\"]+)\"")
_ANY_QUOTE = re.compile(r"\"([^\"]{12,})\"")
_LEARNING_MARKERS = ("learn", "practice", "skills", "discipline", "miss")
_VERSION = re.compile(r"v(\d+\.\d+)[^\n]*reviewed\s+([0-9]{4}-[0-9]{2})")


class StandardFormatError(ValueError):
    """The standard document no longer has the structure the parser depends on."""


def _strip_markup(cell: str) -> str:
    return cell.replace("**", "").replace("*", "").strip()


def _cells(line: str) -> List[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def _is_separator(cells: Sequence[str]) -> bool:
    return all(set(cell) <= set("-: ") and cell for cell in cells)


class Standard:
    """Parsed view of the printable standard."""

    def __init__(
        self,
        *,
        source: str,
        universal: Sequence[Tuple[str, str]],
        refuse_explanations: Dict[str, str],
        learning_explanations: Dict[str, str],
        version: str,
    ) -> None:
        self.source = source
        self._universal = tuple(universal)
        self._refuse = dict(refuse_explanations)
        self._learning = dict(learning_explanations)
        self.version = version

    # -- construction -----------------------------------------------------
    @classmethod
    def load(cls, path: "str | Path | None" = None) -> "Standard":
        resolved = Path(path) if path is not None else cls.default_path()
        return cls.from_text(resolved.read_text(encoding="utf-8"), source=str(resolved))

    @staticmethod
    def default_path() -> Path:
        repo_root = Path(__file__).resolve().parents[1]
        candidate = repo_root / DEFAULT_RELATIVE_PATH
        if candidate.exists():
            return candidate
        raise StandardFormatError(
            "standard document not found at %s, pass an explicit path" % candidate
        )

    @classmethod
    def from_text(cls, text: str, *, source: str = "<text>") -> "Standard":
        lines = text.splitlines()
        universal = cls._parse_universal(lines, source)
        bands, rows = cls._parse_grid(lines, source)
        if tuple(bands) != AGE_BANDS:
            raise StandardFormatError(
                "%s: expected age bands %s in the grid header, found %s"
                % (source, ", ".join(AGE_BANDS), ", ".join(bands) or "none")
            )

        refuse_explanations: Dict[str, str] = {}
        learning_explanations: Dict[str, str] = {}
        for band in AGE_BANDS:
            refuse_cell = rows[ROW_REFUSE][band]
            match = _REFUSE_QUOTE.search(refuse_cell)
            if not match:
                raise StandardFormatError(
                    "%s: no bolded 'When it refuses ...' quote in the %s refuse cell"
                    % (source, band)
                )
            refuse_explanations[band] = match.group(1).strip()

            allowed_cell = rows[ROW_ALLOWED][band]
            quotes = [
                quote.strip()
                for quote in _ANY_QUOTE.findall(allowed_cell)
                if any(marker in quote.lower() for marker in _LEARNING_MARKERS)
            ]
            if not quotes:
                raise StandardFormatError(
                    "%s: no quoted learning-integrity line in the %s allowed cell"
                    % (source, band)
                )
            learning_explanations[band] = quotes[0]

        version_match = _VERSION.search(text)
        version = (
            "v%s reviewed %s" % (version_match.group(1), version_match.group(2))
            if version_match
            else "unknown"
        )

        return cls(
            source=source,
            universal=universal,
            refuse_explanations=refuse_explanations,
            learning_explanations=learning_explanations,
            version=version,
        )

    # -- parsing helpers --------------------------------------------------
    @staticmethod
    def _parse_universal(lines: Sequence[str], source: str) -> List[Tuple[str, str]]:
        bullets: List[str] = []
        in_section = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip().lower()
                in_section = UNIVERSAL_HEADING in heading
                continue
            if not in_section:
                continue
            if stripped.startswith("- "):
                bullets.append(_strip_markup(stripped[2:]))
            elif stripped == "---":
                break
        if len(bullets) < len(UNIVERSAL_BULLET_MARKERS):
            raise StandardFormatError(
                "%s: found %d universal bullets, expected at least %d"
                % (source, len(bullets), len(UNIVERSAL_BULLET_MARKERS))
            )
        return [(bullet, bullet.lower()) for bullet in bullets]

    @staticmethod
    def _parse_grid(
        lines: Sequence[str], source: str
    ) -> Tuple[List[str], Dict[str, Dict[str, str]]]:
        header_index = None
        for index, line in enumerate(lines):
            if line.strip().startswith("|") and "ages" in line.lower():
                header_index = index
                break
        if header_index is None:
            raise StandardFormatError("%s: no age band table header found" % source)

        header = [_strip_markup(cell) for cell in _cells(lines[header_index])]
        bands: List[str] = []
        for cell in header[1:]:
            try:
                bands.append(normalize_band(cell))
            except ValueError as exc:
                raise StandardFormatError("%s: %s" % (source, exc)) from None

        rows: Dict[str, Dict[str, str]] = {}
        for line in lines[header_index + 1 :]:
            stripped = line.strip()
            if not stripped.startswith("|"):
                break
            cells = _cells(stripped)
            if _is_separator(cells) or not cells:
                continue
            label = _strip_markup(cells[0]).lower()
            if not label:
                continue
            values = cells[1:]
            if len(values) != len(bands):
                raise StandardFormatError(
                    "%s: row %r has %d cells, expected %d"
                    % (source, label, len(values), len(bands))
                )
            rows[label] = dict(zip(bands, values))

        for required in (ROW_ALLOWED, ROW_ADULT, ROW_REFUSE):
            if required not in rows:
                raise StandardFormatError(
                    "%s: missing grid row %r, found %s"
                    % (source, required, ", ".join(sorted(rows)) or "none")
                )
        return bands, rows

    # -- accessors --------------------------------------------------------
    @property
    def age_bands(self) -> Tuple[str, ...]:
        return AGE_BANDS

    @property
    def universal_bullets(self) -> Tuple[str, ...]:
        return tuple(bullet for bullet, _ in self._universal)

    def universal_rule(self, category: str) -> str:
        """The verbatim universal bullet that governs ``category``."""
        marker = UNIVERSAL_BULLET_MARKERS.get(category)
        if marker is None:
            raise KeyError("no universal rule for category %r" % category)
        matches = [bullet for bullet, lowered in self._universal if marker in lowered]
        if len(matches) != 1:
            raise StandardFormatError(
                "%s: expected exactly one universal bullet containing %r, found %d"
                % (self.source, marker, len(matches))
            )
        return matches[0]

    def refuse_explanation(self, age_band: str) -> str:
        """The standard's own age appropriate 'why' for a refusal."""
        return self._refuse[normalize_band(age_band)]

    def learning_explanation(self, age_band: str) -> str:
        """The standard's own age appropriate line about the cost of skipping work."""
        return self._learning[normalize_band(age_band)]

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<Standard %s, %d universal bullets>" % (self.version, len(self._universal))
