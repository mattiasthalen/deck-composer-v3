"""Two verbs, argparse, JSON only.

A run that succeeds prints exactly one JSON object to stdout and exits 0, always
with a `next` sentence. A contract failure prints `{"error", "detail", "next"}`
to stderr and exits 1. A usage error exits 2.

`check` exits 0 whether or not it found violations (ADR-0006): the caller is a
model reading JSON, and a deck with violations is the normal state of a deck
being built.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

from deck_composer import check as check_module
from deck_composer import facts as facts_module
from deck_composer import manabox, scryfall
from deck_composer import rules as rules_module
from deck_composer.errors import ToolError

CARD_FACTS = Path("data/card_facts.json")
CATEGORIES = Path("data/categories.json")
TARGETS = Path("data/targets.json")


def project_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return here


def _version() -> str:
    try:
        return package_version("deck-composer")
    except PackageNotFoundError:
        return "unknown"


def _display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deck-composer",
        description="Compose a Commander table from a ManaBox collection. The model composes.",
    )
    parser.add_argument("--version", action="version", version=_version())
    verbs = parser.add_subparsers(dest="verb", required=True, metavar="<verb>")

    refresh = verbs.add_parser(
        "refresh", help="read a ManaBox export and Scryfall; write the card facts"
    )
    refresh.add_argument("export", type=Path, help="path to a ManaBox CSV export")
    refresh.add_argument(
        "--all",
        action="store_true",
        dest="all_entries",
        help="re-fetch every card, not only what is missing; reports legality and "
        "Game Changer flips",
    )
    refresh.add_argument("--out", type=Path, default=None, help="card facts path")
    refresh.set_defaults(handler=_refresh)

    check = verbs.add_parser("check", help="return violations and metrics for a table")
    check.add_argument("decks", type=Path, nargs="*", help="the deck files forming the table")
    check.add_argument(
        "--commander",
        action="append",
        default=[],
        metavar="NAME",
        help="a seat whose deck is not built yet; repeatable. With no deck files "
        "this is the selection checkpoint, and alongside them it is a table "
        "part-way through the build",
    )
    check.add_argument("--facts", type=Path, default=None, help="card facts path")
    check.add_argument(
        "--categories", type=Path, default=None, help="bracket category patterns path"
    )
    check.add_argument("--targets", type=Path, default=None, help="house metric targets path")
    check.set_defaults(handler=_check, usage_parser=check)
    return parser


def _refresh(args: argparse.Namespace, root: Path) -> dict[str, Any]:
    out = args.out or root / CARD_FACTS
    export = manabox.read_export(args.export, display=str(args.export))
    result = facts_module.refresh(
        export,
        out,
        all_entries=args.all_entries,
        client=scryfall.Client(version=_version()),
        display=_display(out, root),
    )
    return result.to_dict()


def _check(args: argparse.Namespace, root: Path) -> dict[str, Any]:
    if not args.decks and not args.commander:
        args.usage_parser.error("give deck files, --commander names, or both")
    path = args.facts or root / CARD_FACTS
    card_facts = facts_module.read(path, display=_display(path, root))
    categories = args.categories or root / CATEGORIES
    rules = rules_module.read_rules(categories, display=_display(categories, root))
    targets_path = args.targets or root / TARGETS
    targets = rules_module.read_targets(targets_path, display=_display(targets_path, root))
    decks = [manabox.read_deck(deck, display=_display(deck, root)) for deck in args.decks]
    return check_module.check(decks, card_facts, rules, targets, pending=args.commander).to_dict()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = args.handler(args, project_root())
    except ToolError as error:
        print(json.dumps(error.to_dict(), ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
