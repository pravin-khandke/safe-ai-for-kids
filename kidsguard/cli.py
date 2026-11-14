"""Command line front end for the content moderation settings.

    python -m kidsguard show --age 12-15
    python -m kidsguard set-level all very-high
    python -m kidsguard set-level harassment-hate medium
    python -m kidsguard toggle homework on
    python -m kidsguard words add fortnite
    python -m kidsguard words clear
    python -m kidsguard reset
    python -m kidsguard check "write my essay for me" --age 12-15
    python -m kidsguard models --age 8-11

Settings live in ``kidsguard-settings.json`` unless ``--config`` says otherwise.
``check`` exits 1 when the message is refused, so it can be used in a smoke test.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .levels import CategoryGroup, ProtectionLevel
from .moderation import ContentModerator
from .render import render_decision, render_settings
from .settings import ModerationSettings, SettingsError
from .standard import Standard, StandardFormatError

DEFAULT_CONFIG = "kidsguard-settings.json"

_GROUP_ALIASES = {
    "all": None,
    "both": None,
    "harassment": CategoryGroup.HARASSMENT_HATE,
    "harassment-hate": CategoryGroup.HARASSMENT_HATE,
    "harassment_hate": CategoryGroup.HARASSMENT_HATE,
    "hate": CategoryGroup.HARASSMENT_HATE,
    "violence": CategoryGroup.VIOLENCE_ADULT,
    "violence-adult": CategoryGroup.VIOLENCE_ADULT,
    "violence_adult": CategoryGroup.VIOLENCE_ADULT,
    "adult": CategoryGroup.VIOLENCE_ADULT,
}


def _parse_group(raw: str) -> Optional[CategoryGroup]:
    key = raw.strip().lower()
    if key not in _GROUP_ALIASES:
        raise SettingsError(
            "unknown group %r, expected one of: all, %s"
            % (raw, ", ".join(sorted({"harassment-hate", "violence-adult"})))
        )
    return _GROUP_ALIASES[key]


def _load(args) -> ModerationSettings:
    return ModerationSettings.load(args.config)


def _print_screen(args, settings: ModerationSettings, *, saved: Optional[bool] = None) -> None:
    standard = Standard.load(args.standard)
    print(
        render_settings(
            settings,
            standard,
            age_band=args.age,
            child_name=args.child,
            config_path=args.config,
            saved=saved,
        )
    )


def cmd_show(args) -> int:
    _print_screen(args, _load(args))
    return 0


def cmd_set_level(args) -> int:
    settings = _load(args)
    level = ProtectionLevel.parse(args.level)
    group = _parse_group(args.group)
    if group is None:
        settings.set_all_levels(level)
    else:
        settings.set_level(group, level)
    settings.save(args.config)
    _print_screen(args, settings, saved=True)
    return 0


def cmd_toggle(args) -> int:
    settings = _load(args)
    state = args.state.strip().lower() in ("on", "true", "1", "yes")
    mapping = {
        "moderation": "moderation_enabled",
        "word-filter": "custom_word_filtering",
        "word_filter": "custom_word_filtering",
        "homework": "homework_mode",
    }
    field_name = mapping.get(args.flag.strip().lower())
    if field_name is None:
        raise SettingsError(
            "unknown flag %r, expected one of: moderation, word-filter, homework" % args.flag
        )
    setattr(settings, field_name, state)
    settings.save(args.config)
    _print_screen(args, settings, saved=True)
    return 0


def cmd_words(args) -> int:
    settings = _load(args)
    if args.action == "add":
        settings.add_word(args.word)
    elif args.action == "remove":
        if not settings.remove_word(args.word):
            print("%r was not on the filter list." % args.word)
    elif args.action == "clear":
        count = len(settings.custom_words)
        settings.clear_custom_words()
        print("Cleared %d filtered word(s)." % count)
    else:  # pragma: no cover - argparse restricts the choices
        raise SettingsError("unknown words action %r" % args.action)
    settings.save(args.config)
    _print_screen(args, settings, saved=True)
    return 0


def cmd_reset(args) -> int:
    settings = _load(args)
    settings.reset_to_default()
    settings.save(args.config)
    print("Reset every setting to the default, filtered words included.")
    _print_screen(args, settings, saved=True)
    return 0


def cmd_check(args) -> int:
    settings = _load(args)
    standard = Standard.load(args.standard)
    moderator = ContentModerator(settings, standard, args.age)
    decision = moderator.moderate(args.text)
    print(render_decision(decision, label="child (%s)" % args.age))
    return 1 if decision.refused else 0


def cmd_models(args) -> int:
    settings = _load(args)
    standard = Standard.load(args.standard)
    moderator = ContentModerator(settings, standard, args.age)
    homework = "on" if settings.homework_mode else "off"
    print("Homework mode: %s" % homework)
    for profile in moderator.available_models():
        print("  %-16s %s" % (profile.model_id, profile.label))
        print("  %-16s %s" % ("", profile.description))
    if settings.homework_mode:
        decision = moderator.select_model("general-chat")
        print("")
        print(render_decision(decision, label="general-chat"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kidsguard",
        description="Content moderation settings and policy check for an age-banded guardrail.",
    )
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="settings file (default: %(default)s)")
    parser.add_argument("--standard", default=None, help="path to the standard markdown")
    parser.add_argument(
        "--age",
        default="12-15",
        help="age band: 8-11, 12-15 or 16-18 (default: %(default)s)",
    )
    parser.add_argument("--child", default=None, help="child's name for the screen heading")

    # --age and --child are also accepted after the subcommand. SUPPRESS keeps the
    # value parsed at the top level when the subcommand does not repeat them.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--age", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    common.add_argument("--child", default=argparse.SUPPRESS, help=argparse.SUPPRESS)

    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", parents=[common], help="print the settings screen")
    show.set_defaults(func=cmd_show)

    set_level = sub.add_parser(
        "set-level", parents=[common], help="change a protection level"
    )
    set_level.add_argument("group", help="all, harassment-hate or violence-adult")
    set_level.add_argument("level", help="very-high, high, medium or low")
    set_level.set_defaults(func=cmd_set_level)

    toggle = sub.add_parser("toggle", parents=[common], help="turn a switch on or off")
    toggle.add_argument("flag", help="moderation, word-filter or homework")
    toggle.add_argument("state", help="on or off")
    toggle.set_defaults(func=cmd_toggle)

    words = sub.add_parser(
        "words", parents=[common], help="edit the custom word filter list"
    )
    words.add_argument("action", choices=["add", "remove", "clear"])
    words.add_argument("word", nargs="?", default="", help="the word, for add and remove")
    words.set_defaults(func=cmd_words)

    reset = sub.add_parser(
        "reset", parents=[common], help="reset every setting to the default"
    )
    reset.set_defaults(func=cmd_reset)

    check = sub.add_parser(
        "check", parents=[common], help="run one message through the policy engine"
    )
    check.add_argument("text", help="the message to check")
    check.set_defaults(func=cmd_check)

    models = sub.add_parser(
        "models", parents=[common], help="list the tools available under the current settings"
    )
    models.set_defaults(func=cmd_models)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (SettingsError, StandardFormatError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 3


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
