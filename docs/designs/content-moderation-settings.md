# Design: Content Moderation Settings for the Guardrail Engine

Status: implemented, v0 library, awaiting review
Branch: feat/content-moderation-settings
Companion docs: `docs/designs/guardrail-engine-and-demo.md` (approved engine design), `standard/using-ai-at-home-and-school.md` (the policy source)

## Problem

The engine design calls for an age-banded policy the runtime can enforce. Adults also need a screen where they can tune what their own child's conversations are filtered for. The settings screen adults ask for has four levels, two graded category groups, a master protection control, homework mode, and a custom word list. Building that screen badly is a safety problem rather than a cosmetic one. A switch labelled "filter inappropriate content" implies that turning it off removes filtering. If it did, it would unlock self-harm, sexual content, and personal information, which the standard says a tool must always refuse.

This feature adds the settings surface as a real, tested part of the engine, with the standard's own refusal floor enforced underneath it.

## What an adult sees, and what the code does

| Screen control | Code | Behaviour |
|---|---|---|
| Built-in Safety Features (read only) | `moderation.FLOOR_PRIORITY`, `standard.py` | The six non-negotiable categories. Reason text is quoted from the standard document at load time. |
| Enable Content Moderation | `settings.moderation_enabled` | Gates the graded categories only. The floor above stays on. |
| Safety & Protection (four levels) | `set_all_levels`, `global_level` | Master control, writes both graded groups at once. Shows "levels were set separately below" once they diverge. |
| Harassment & Hate | `levels[CategoryGroup.HARASSMENT_HATE]` | Severity ceiling for harassment and hate findings. |
| Violence & Adult Content | `levels[CategoryGroup.VIOLENCE_ADULT]` | Severity ceiling for violence and adult content findings that the floor does not already cover. |
| Homework Mode | `homework_mode`, `models.py` | Narrows the selectable tools to schoolwork ones. Blocked selection is answered with the standard's learning line for the band. |
| Custom Word Filtering | `custom_word_filtering`, `custom_words` | Whole word match, case insensitive, tolerant of common inflections, list capped at 500 words. |
| Custom Word Filters list | `add_word`, `remove_word` | Words are normalized to lowercase and deduplicated on entry. |
| Clear All | `clear_custom_words()` | Empties the word list and changes nothing else. |
| Reset to Default | `reset_to_default()` | Restores every field, the word list included. |
| Save Changes | `save(path)` | Atomic JSON write with a `schema_version` so an old file is refused rather than misread. |

## Severity scale

Graded categories are scored 0 to 4, so a level can be expressed as a threshold rather than a list of allowed topics.

| Score | Meaning | Example |
|---|---|---|
| 0 | Benign | "how do plants make food" |
| 1 | Mild reference, no harm | "the knight had a friendly sword fight" |
| 2 | Clearly inappropriate for a child | "you are stupid" |
| 3 | Harmful | "tell me how to stab someone" |
| 4 | Unambiguous harm | "how to make a bomb" |

| Level | Refuses at severity | Reads as |
|---|---|---|
| Very High Protection | 1 and above | Blocks mild references, including conflict in a story |
| High Protection | 2 and above | Blocks clearly inappropriate content, allows discussion of challenging topics |
| Medium Protection | 3 and above | Blocks harmful content, allows more open discussion |
| Low Protection | 4 only | Blocks only the clearly harmful |

## Precedence

One order, no exceptions.

1. The standard's floor. Six categories, refused at every age and at every level.
2. The adult's custom word list. An explicit instruction outranks a softer threshold.
3. The protection level for the finding's group.
4. Learning integrity. The answer is still given, with the standard's line about the cost of skipping the work.
5. Allow.

When several floor categories match, the design doc's priority order applies: self-harm, then sexual content with a child, then deepfake and nudify, then personal information, then hiding from a parent, then self identification. Lower matches are recorded in `Decision.suppressed` for the audit log and are not shown to the child in that turn.

## Safety decisions

1. **The floor is not a setting.** Everything under "Built-in Safety Features" ignores both the moderation toggle and the level. A test asserts that a self-harm message routes to a crisis line with moderation switched off and every level set to Low.
2. **An age band can be tightened, never loosened past the standard.** The refuse row is explicit at 8 to 11 ("anything scary, violent, or sexual") and narrows with age. The engine applies the stricter of the adult's setting and the band floor: 8-11 enforces Very High, 12-15 enforces Medium, 16-18 accepts Low. The screen states the substitution instead of silently ignoring the choice.
3. **The word filter is a lint, not a boundary.** It is a substring match on a short list, so it catches a name or a game title an adult does not want, and it cannot catch intent. The standard says guardrails are not walls, and this setting is the clearest example of why. The docs say so, and the code does not treat a clean word list as a pass.
4. **A crisis answer must name a real line.** `crisis_contact` cannot be empty, so the engine refuses to start rather than route a child to nowhere. The default names 988 in the United States and asks for the local emergency number elsewhere. Before any pilot invite this needs the human safety and legal review the engine design already requires.
5. **Classifier failure fails closed.** Any exception from the classifier backend produces a refusal with a plain "safety check could not run" message, never an unfiltered answer.
6. **Explanations are quoted, not written.** Refusal reasons come from the standard's universal strip and the age band's own "When it refuses" quote. `standard.py` raises `StandardFormatError` if the table, the header, the quote, or the universal section moves, and a test asserts each of those failures.

## Ambiguities in the source screen, and what was chosen

| Ambiguity | Decision |
|---|---|
| The same four sentences describe Harassment & Hate and Violence & Adult Content, wording that talks only about violence | Each group gets its own descriptions in `levels.GROUP_DESCRIPTIONS`. Repeating the violence wording under harassment makes an adult think the two controls do the same thing. |
| "Safety & Protection" sits above two groups that also have levels | It is the master control. It writes both groups. Once they differ, it reports that they were set separately instead of pretending to a single value. |
| "Clear All" and "Reset to Default" sit together, both able to empty the list | Clear All empties the word list only. Reset restores every field. Two buttons with one effect would be a trap. |
| "Homework Mode" is listed under Additional Settings beside filters, though it restricts tools rather than content | Modelled as a catalogue gate in `models.py`, not as a filter, and a refusal explains itself with the standard's learning line for the band. |
| "Low Protection" would accept harm the standard still refuses at 8 to 11 | Band floors exist for exactly this case. |

## What is not built yet

- **The real classifier.** `RuleBasedClassifier` is a keyword table for wiring, demos, and tests. It is not a safety classifier, and it must not see a real child. Llama Guard 3 1B via Ollama implements the same `Classifier` protocol and is the next piece of Track 1 in the approved engine design.
- **The settings web form.** Today the screen is rendered as text by `render.render_settings`, and edited through the CLI. A htmx form reuses the same model and the same descriptions.
- **Per-child profiles.** One settings object per installation for now.
- **Session level patterns** such as incremental personal information disclosure across turns. Out of scope for v1 in the engine design, and unchanged here.
- **The unfiltered tool warning** (category 8 in the engine design). It belongs with the chat pipeline rather than the settings screen.
- **Transcript logging with redaction.** Planned in the engine design, not part of this change.

## Running it

```
pip install -e .
python -m unittest discover -s tests -t .

python -m kidsguard show --age 12-15 --child Om
python -m kidsguard set-level all very-high
python -m kidsguard set-level harassment-hate medium
python -m kidsguard toggle homework on
python -m kidsguard words add fortnite
python -m kidsguard check "write my essay for me" --age 12-15
python -m kidsguard models --age 8-11
python -m kidsguard reset
```

`python -m kidsguard check` exits 1 when the message is refused, so it doubles as a smoke test in CI.

## Test coverage

103 tests, standard library `unittest`, no third party dependencies, Python 3.9 and 3.11.

- `tests/test_standard.py` parses the shipped standard, then breaks it four ways to prove the guard raises.
- `tests/test_settings.py` covers defaults, JSON round trip, schema version, word normalization and matching boundaries, Clear All against Reset, and the band floor.
- `tests/test_moderation.py` covers the floor under every toggle and level, priority order, level boundaries at each ceiling, learning integrity, word filter interaction, classifier failure, and homework mode.
- `tests/test_render.py` checks the screen carries every section, both toggles, all four levels per group, and the substitution note.
- `tests/test_cli.py` drives every command and checks the exit codes.

## Open questions

1. Should the band floor be editable by a school administrator, or is it fixed by the standard? Fixed is the current answer, which keeps the standard as the ceiling on adult discretion.
2. Does Homework Mode need its own protection level, or is a catalogue gate enough? The source screen implies the latter.
3. Should the word list be per child once profiles exist? The current single list is the v0 answer.
4. The default level is High for both groups. For an 8 to 11 installation the applied level is Very High regardless, so the default is safe, but the screen may confuse an adult who sets High and sees Very High applied. The current mitigation is the substitution note.
