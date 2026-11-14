"""The moderation pipeline: text in, decision out.

Three layers, applied in this fixed order.

1. **The standard's floor.** Six categories in the printable standard are
   non-negotiable at every age. No setting can weaken them, and the AI moderation
   toggle does not switch them off. A switch labelled "filter inappropriate
   content" must not be able to unlock self-harm, sexual content, or personal
   information, because those are what the standard says a tool must always
   refuse.
2. **The adult's word list.** An explicit instruction from the adult, so it wins
   over the softer category thresholds.
3. **The protection level.** Harassment and hate, violence and adult content are
   graded by severity and compared against the level in force for the age band.

Learning integrity is not a refusal at all: the tool keeps answering and adds the
standard's own line about the cost of skipping the work.

Every explanation string comes out of the standard document, except the two
operational messages (filtered word, unavailable safety check) which describe the
tool rather than the policy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Protocol, Sequence, Tuple

from .levels import (
    CATEGORY_GROUP_LABEL,
    CategoryGroup,
    ProtectionLevel,
    normalize_band,
)
from .models import find_model, model_allowed
from .settings import ModerationSettings
from .standard import Standard

#: Categories the standard requires a refusal for at every age, in the priority
#: order the design doc fixes (highest priority first).
FLOOR_PRIORITY: Tuple[str, ...] = (
    "self_harm",
    "sexual_content_minor",
    "deepfake_nudify",
    "pii_solicitation",
    "hide_from_parent",
    "self_identification",
)

FLOOR_CATEGORIES = frozenset(FLOOR_PRIORITY)

#: Categories the settings screen can loosen or tighten.
GROUP_CATEGORIES: Dict[CategoryGroup, Tuple[str, ...]] = {
    CategoryGroup.HARASSMENT_HATE: ("harassment", "hate"),
    CategoryGroup.VIOLENCE_ADULT: ("violence", "adult_content"),
}

CATEGORY_GROUP: Dict[str, CategoryGroup] = {
    category: group
    for group, categories in GROUP_CATEGORIES.items()
    for category in categories
}

LEARNING_INTEGRITY = "learning_integrity"

UNAVAILABLE_TEMPLATE = (
    "The safety check could not run, so this message was not answered. "
    "Try again in a moment, and talk to a trusted adult if you need help now."
)

WORD_TEMPLATE = (
    "The word \"{word}\" is on the filter list the adult set for this app, so this "
    "message was not answered. Ask the adult to review the list if that was a mistake."
)


class Action(str, Enum):
    ALLOW = "allow"
    ALLOW_WITH_EXPLANATION = "allow_with_explanation"
    REFUSE_WITH_EXPLANATION = "refuse_with_explanation"
    REFUSE_AND_ROUTE_TO_CRISIS = "refuse_and_route_to_crisis"


@dataclass(frozen=True)
class Finding:
    """One thing a classifier noticed in the text."""

    category: str
    severity: int
    evidence: Tuple[str, ...] = ()

    @property
    def group(self) -> Optional[CategoryGroup]:
        return CATEGORY_GROUP.get(self.category)


@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str
    explanation: str = ""
    category: Optional[str] = None
    group: Optional[CategoryGroup] = None
    severity: int = 0
    evidence: Tuple[str, ...] = ()
    suppressed: Tuple[str, ...] = ()
    applied_level: Optional[ProtectionLevel] = None

    @property
    def refused(self) -> bool:
        return self.action in (
            Action.REFUSE_WITH_EXPLANATION,
            Action.REFUSE_AND_ROUTE_TO_CRISIS,
        )

    def as_dict(self) -> Dict[str, object]:
        return {
            "action": self.action.value,
            "reason": self.reason,
            "category": self.category,
            "group": self.group.value if self.group else None,
            "severity": self.severity,
            "explanation": self.explanation,
            "evidence": list(self.evidence),
            "suppressed": list(self.suppressed),
            "applied_level": self.applied_level.value if self.applied_level else None,
        }


class RuleBasedClassifier:
    """Deterministic keyword classifier used for wiring, demos and tests.

    This is not a safety classifier and is not a substitute for one. The design
    doc puts Llama Guard 3 behind the same interface, and a deployment must use
    that backend before any real child sees the tool. The keyword table exists so
    the policy engine can be exercised end to end without a model server.
    """

    #: category, severity, phrases
    RULES: Tuple[Tuple[str, int, Tuple[str, ...]], ...] = (
        (
            "self_harm",
            4,
            (
                "kill myself",
                "killing myself",
                "want to die",
                "end my life",
                "suicide",
                "cut myself",
                "starve myself",
                "stop eating",
                "anorexia",
                "hurt myself",
            ),
        ),
        (
            "sexual_content_minor",
            4,
            (
                "naked kid",
                "nude picture of a child",
                "nude photo of my classmate",
                "underage sex",
                "sexual roleplay",
                "romantic roleplay",
            ),
        ),
        (
            "deepfake_nudify",
            4,
            (
                "nudify",
                "deepfake",
                "undress her photo",
                "undress his photo",
                "make her naked",
                "make him naked",
            ),
        ),
        (
            "pii_solicitation",
            3,
            (
                "my address is",
                "my phone number is",
                "my school is called",
                "what school do you go to",
                "what is your address",
                "send me your photo",
            ),
        ),
        (
            "hide_from_parent",
            3,
            (
                "don't tell my parents",
                "dont tell my mom",
                "dont tell my dad",
                "don't tell my mom",
                "don't tell my dad",
                "hide this from my parents",
                "meet a stranger",
                "meet up with someone i met online",
            ),
        ),
        (
            "self_identification",
            2,
            (
                "are you a real person",
                "are you human",
                "pretend you are my friend",
                "pretend you are my girlfriend",
                "pretend you are my boyfriend",
                "be my best friend",
            ),
        ),
        (
            "harassment",
            2,
            (
                "you are stupid",
                "you're stupid",
                "idiot",
                "loser",
                "shut up",
                "you are ugly",
                "nobody likes you",
            ),
        ),
        ("harassment", 4, ("kill yourself", "go die")),
        (
            "hate",
            3,
            (
                "go back to your country",
                "i hate all",
                "hate all of them",
                "they should be removed",
            ),
        ),
        ("violence", 1, ("sword fight", "friendly fight", "punch", "wrestle")),
        ("violence", 2, ("beat him up", "beat her up", "violent video")),
        (
            "violence",
            3,
            (
                "how to kill",
                "how to stab",
                "shoot someone",
                "hurt someone badly",
                "torture",
            ),
        ),
        (
            "violence",
            4,
            (
                "make a bomb",
                "build a bomb",
                "graphic violence",
                "gory",
                "how to poison",
            ),
        ),
        ("adult_content", 3, ("nudes", "sex scene", "explicit sex", "porn")),
        (
            LEARNING_INTEGRITY,
            0,
            (
                "do my homework",
                "do my essay",
                "write my essay",
                "write my report",
                "write it for me",
                "just give me the answer",
                "only the answer",
                "answer without explaining",
                "no explanation just the answer",
            ),
        ),
    )

    def __init__(self, rules: "Sequence[Tuple[str, int, Sequence[str]]] | None" = None) -> None:
        self._rules = tuple(rules) if rules is not None else self.RULES
        self._compiled: Tuple[Tuple[str, int, re.Pattern], ...] = tuple(
            (
                category,
                severity,
                re.compile(
                    "|".join(
                        r"(?<![\w])" + re.escape(phrase) + r"(?![\w])" for phrase in phrases
                    ),
                    re.IGNORECASE,
                ),
            )
            for category, severity, phrases in self._rules
        )

    def classify(self, text: str, age_band: str) -> List[Finding]:
        lowered = text.lower()
        found: Dict[str, Finding] = {}
        for category, severity, pattern in self._compiled:
            match = pattern.search(lowered)
            if not match:
                continue
            existing = found.get(category)
            evidence = (match.group(0).strip(),)
            if existing is None or severity > existing.severity:
                found[category] = Finding(
                    category=category,
                    severity=severity,
                    evidence=(existing.evidence + evidence) if existing else evidence,
                )
            else:
                found[category] = Finding(
                    category=category,
                    severity=existing.severity,
                    evidence=existing.evidence + evidence,
                )
        return list(found.values())


class Classifier(Protocol):
    """The one interface a safety backend has to implement.

    ``RuleBasedClassifier`` and a Llama Guard backend both satisfy it, which is
    what keeps the policy engine independent of the detector.
    """

    def classify(self, text: str, age_band: str) -> List[Finding]:
        ...


class ContentModerator:
    """Applies the settings and the standard to a single message."""

    def __init__(
        self,
        settings: ModerationSettings,
        standard: Standard,
        age_band: str,
        classifier: Optional[Classifier] = None,
        crisis_contact: Optional[str] = None,
    ) -> None:
        self.settings = settings.validate()
        self.standard = standard
        self.age_band = normalize_band(age_band)
        self.classifier = classifier if classifier is not None else RuleBasedClassifier()
        self.crisis_contact = crisis_contact or self.settings.crisis_contact

    # -- policy helpers ---------------------------------------------------
    def applied_level(self, group: CategoryGroup) -> ProtectionLevel:
        return self.settings.effective_level(group, self.age_band)

    def explain_refusal(self, category: str) -> str:
        """The standard's reasoning for a refusal, plus the policy line when graded."""
        if category in FLOOR_CATEGORIES:
            return self.standard.universal_rule(category)
        group = CATEGORY_GROUP.get(category)
        reason = self.standard.refuse_explanation(self.age_band)
        if group is None:
            return reason
        level = self.applied_level(group)
        return "%s\n\nBlocked because %s is set to %s for ages %s." % (
            reason,
            CATEGORY_GROUP_LABEL[group].lower(),
            level.label,
            self.age_band,
        )

    def _floor_decision(self, findings: "Sequence[Finding]") -> Optional[Decision]:
        ranked = sorted(
            (finding for finding in findings if finding.category in FLOOR_CATEGORIES),
            key=lambda finding: FLOOR_PRIORITY.index(finding.category),
        )
        if not ranked:
            return None
        top = ranked[0]
        suppressed = tuple(finding.category for finding in ranked[1:])
        if top.category == "self_harm":
            explanation = "%s\n\n%s" % (
                self.standard.refuse_explanation(self.age_band),
                self.crisis_contact,
            )
            return Decision(
                action=Action.REFUSE_AND_ROUTE_TO_CRISIS,
                reason="floor_crisis",
                explanation=explanation,
                category=top.category,
                severity=top.severity,
                evidence=top.evidence,
                suppressed=suppressed,
            )
        return Decision(
            action=Action.REFUSE_WITH_EXPLANATION,
            reason="floor",
            explanation=self.standard.universal_rule(top.category),
            category=top.category,
            severity=top.severity,
            evidence=top.evidence,
            suppressed=suppressed,
        )

    # -- the pipeline -----------------------------------------------------
    def moderate(self, text: str) -> Decision:
        message = (text or "").strip()
        if not message:
            return Decision(action=Action.ALLOW, reason="empty_input")

        try:
            findings = list(self.classifier.classify(message, self.age_band))
        except Exception:  # noqa: BLE001 - any classifier failure must fail closed
            return Decision(
                action=Action.REFUSE_WITH_EXPLANATION,
                reason="classifier_unavailable",
                explanation=UNAVAILABLE_TEMPLATE,
            )

        floor = self._floor_decision(findings)
        if floor is not None:
            return floor

        word = self.settings.matches_custom_word(message)
        if word is not None:
            return Decision(
                action=Action.REFUSE_WITH_EXPLANATION,
                reason="custom_word",
                explanation=WORD_TEMPLATE.format(word=word),
                category="custom_word",
                evidence=(word,),
                suppressed=tuple(finding.category for finding in findings),
            )

        graded = [finding for finding in findings if finding.group is not None]
        if not self.settings.moderation_enabled:
            if graded or any(f.category == LEARNING_INTEGRITY for f in findings):
                return Decision(
                    action=Action.ALLOW,
                    reason="moderation_disabled",
                    suppressed=tuple(finding.category for finding in findings),
                )
            return Decision(action=Action.ALLOW, reason="allowed")

        refusal = self._graded_refusal(graded)
        if refusal is not None:
            return refusal

        learning = [f for f in findings if f.category == LEARNING_INTEGRITY]
        if learning:
            return Decision(
                action=Action.ALLOW_WITH_EXPLANATION,
                reason="learning_integrity",
                explanation=self.standard.learning_explanation(self.age_band),
                category=LEARNING_INTEGRITY,
                severity=learning[0].severity,
                evidence=learning[0].evidence,
            )

        return Decision(
            action=Action.ALLOW,
            reason="allowed",
            suppressed=tuple(finding.category for finding in graded),
        )

    def _graded_refusal(self, graded: "Sequence[Finding]") -> Optional[Decision]:
        worst: Optional[Finding] = None
        for finding in graded:
            level = self.applied_level(finding.group)  # type: ignore[arg-type]
            if finding.severity < level.ceiling:
                continue
            if worst is None or finding.severity > worst.severity:
                worst = finding
        if worst is None:
            return None
        suppressed = tuple(
            finding.category for finding in graded if finding.category != worst.category
        )
        return Decision(
            action=Action.REFUSE_WITH_EXPLANATION,
            reason="level_refusal",
            explanation=self.explain_refusal(worst.category),
            category=worst.category,
            group=worst.group,
            severity=worst.severity,
            evidence=worst.evidence,
            suppressed=suppressed,
            applied_level=self.applied_level(worst.group),  # type: ignore[arg-type]
        )

    # -- homework mode ----------------------------------------------------
    def select_model(self, model_id: str) -> Decision:
        allowed, reason = model_allowed(model_id, self.settings)
        if allowed:
            return Decision(action=Action.ALLOW, reason="model_allowed")
        profile = find_model(model_id)
        name = profile.label if profile else model_id
        explanation = (
            "Homework mode is on, so only the schoolwork tools are available. "
            "%s\n\nTurn homework mode off in the content moderation settings to use %s."
            % (self.standard.learning_explanation(self.age_band), name)
        )
        return Decision(
            action=Action.REFUSE_WITH_EXPLANATION,
            reason="homework_mode",
            explanation=explanation,
            category="model_choice",
        )

    def available_models(self):
        from .models import available_models

        return available_models(self.settings)
