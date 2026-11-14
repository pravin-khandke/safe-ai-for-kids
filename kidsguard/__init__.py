"""kidsguard: age-banded guardrails for children's AI use.

The policy language is never duplicated here. Every refusal explanation is read
out of ``standard/using-ai-at-home-and-school.md`` at load time, so the printable
standard stays the single source of truth.

Public surface:

    from kidsguard import Standard, ModerationSettings, ContentModerator

    standard = Standard.load()
    settings = ModerationSettings.load("kidsguard-settings.json")
    moderator = ContentModerator(settings=settings, standard=standard, age_band="12-15")
    decision = moderator.moderate("write my essay for me")
    print(decision.action, decision.explanation)
"""

from __future__ import annotations

from .levels import AGE_BANDS, CategoryGroup, ProtectionLevel, CATEGORY_GROUP_LABEL
from .moderation import Action, ContentModerator, Decision, Finding, RuleBasedClassifier
from .models import MODEL_CATALOG, ModelProfile, available_models
from .prompts import (
    PROMPT_AGE_BANDS,
    SUBJECTS,
    PromptFormatError,
    TutorPromptSource,
    render_tutor_prompt,
)
from .settings import ModerationSettings, SettingsError, default_settings
from .standard import Standard, StandardFormatError

__all__ = [
    "AGE_BANDS",
    "Action",
    "CATEGORY_GROUP_LABEL",
    "CategoryGroup",
    "ContentModerator",
    "Decision",
    "Finding",
    "MODEL_CATALOG",
    "ModerationSettings",
    "ModelProfile",
    "PROMPT_AGE_BANDS",
    "PromptFormatError",
    "ProtectionLevel",
    "RuleBasedClassifier",
    "SUBJECTS",
    "SettingsError",
    "Standard",
    "StandardFormatError",
    "TutorPromptSource",
    "available_models",
    "default_settings",
    "render_tutor_prompt",
]

__version__ = "0.1.0"
