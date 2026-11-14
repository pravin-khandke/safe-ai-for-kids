"""Model catalogue for homework mode.

"Homework mode" restricts the conversation to tools chosen for schoolwork. The
catalogue is deliberately a plain data table so a deployment can swap it without
touching the moderator, and so the restriction is visible in one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

HOMEWORK_TAG = "homework"


@dataclass(frozen=True)
class ModelProfile:
    model_id: str
    label: str
    description: str
    tags: Tuple[str, ...]

    @property
    def is_educational(self) -> bool:
        return HOMEWORK_TAG in self.tags


MODEL_CATALOG: Tuple[ModelProfile, ...] = (
    ModelProfile(
        model_id="study-coach",
        label="Study Coach",
        description=(
            "Explains method and checks understanding. Never hands over a finished "
            "answer to submit."
        ),
        tags=("education", "homework", "study"),
    ),
    ModelProfile(
        model_id="reading-buddy",
        label="Reading Buddy",
        description="Reading support, vocabulary and story help for school reading.",
        tags=("education", "homework", "reading"),
    ),
    ModelProfile(
        model_id="science-lab",
        label="Science Lab",
        description="Science explanations, safe at-home experiments, and lab write-up coaching.",
        tags=("education", "homework", "science"),
    ),
    ModelProfile(
        model_id="general-chat",
        label="General Chat",
        description="Everyday conversation, general questions and current information.",
        tags=("general",),
    ),
    ModelProfile(
        model_id="creative-studio",
        label="Creative Studio",
        description="Stories, poems, drawings prompts and creative projects.",
        tags=("creative", "general"),
    ),
)

_BY_ID: Dict[str, ModelProfile] = {profile.model_id: profile for profile in MODEL_CATALOG}


def find_model(model_id: str) -> "ModelProfile | None":
    return _BY_ID.get(str(model_id).strip())


def available_models(settings) -> Tuple[ModelProfile, ...]:
    """Models a child may pick, given the current settings."""
    if getattr(settings, "homework_mode", False):
        return tuple(profile for profile in MODEL_CATALOG if profile.is_educational)
    return MODEL_CATALOG


def model_allowed(model_id: str, settings) -> Tuple[bool, str]:
    """Whether a model can be selected, plus a short reason when it cannot."""
    profile = find_model(model_id)
    if profile is None:
        return False, "there is no tool called %s" % model_id
    if getattr(settings, "homework_mode", False) and not profile.is_educational:
        return False, "homework mode limits the tools to schoolwork ones"
    return True, ""
