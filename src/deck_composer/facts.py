"""Owns `data/card_facts.json` and the `refresh` operation that writes it.

One committed file carries both the Scryfall projection and how many copies the
owner holds. Ownership joins through printings, never by name: eight token lots
in this collection share a card's name, and summing by name overcounts.

Ownership is recomputed from the export on every refresh, offline. Fetching is
incremental — only printings the file does not already carry — so re-exporting
after a trade costs no Scryfall requests. `--all` re-fetches everything and is
the deliberate way to learn about legality and Game Changer flips.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

from deck_composer import scryfall
from deck_composer.errors import ToolError
from deck_composer.manabox import Export
from deck_composer.scryfall import Card, Face, Printing, Token

SCHEMA = 1

_CARD_KEYS = (
    "name", "oracle_id", "layout", "type_line", "mana_cost", "cmc", "colors",
    "color_identity", "produced_mana", "oracle_text", "keywords", "legality",
    "game_changer", "edhrec_rank", "faces", "owned", "printings",
)  # fmt: skip
_TOKEN_KEYS = ("oracle_id", "name", "layout", "type_line", "oracle_text", "owned", "printings")


@dataclass(frozen=True, slots=True)
class OwnedCard:
    """A card plus how many copies the export holds, per printing and in total."""

    card: Card
    owned: int
    owned_by_printing: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class OwnedToken:
    token: Token
    owned: int
    owned_by_printing: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CardFacts:
    """The committed projection. Authoritative for what a card is and how many exist."""

    export_file: str
    export_sha256: str
    export_rows: int
    refreshed: str | None
    cards: tuple[OwnedCard, ...]
    tokens: tuple[OwnedToken, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "cards", tuple(sorted(self.cards, key=lambda x: x.card.name)))
        object.__setattr__(
            self, "tokens", tuple(sorted(self.tokens, key=lambda x: x.token.oracle_id))
        )

    def card(self, name: str) -> OwnedCard | None:
        """Exact name first, then either face of a double-faced card, case-insensitively."""
        folded = name.casefold()
        for entry in self.cards:
            if entry.card.name.casefold() == folded:
                return entry
        for entry in self.cards:
            for face in entry.card.faces or ():
                if face.name.casefold() == folded:
                    return entry
        return None

    @property
    def printing_ids(self) -> frozenset[str]:
        return frozenset(
            printing.scryfall_id
            for entry in (*self.cards, *self.tokens)
            for printing in _record(entry).printings
        )


def empty(export: Export) -> CardFacts:
    return CardFacts(
        export_file=export.file,
        export_sha256=export.sha256,
        export_rows=export.rows,
        refreshed=None,
        cards=(),
        tokens=(),
    )


# --- the refresh operation --------------------------------------------------


@dataclass(frozen=True, slots=True)
class Changes:
    """What a whole-file refresh moved. Empty on an incremental one."""

    legality: tuple[tuple[str, str, str], ...] = ()
    game_changer: tuple[tuple[str, bool, bool], ...] = ()
    renamed: tuple[tuple[str, str], ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.legality or self.game_changer or self.renamed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "legality": [{"card": n, "was": a, "now": b} for n, a, b in self.legality],
            "game_changer": [{"card": n, "was": a, "now": b} for n, a, b in self.game_changer],
            "renamed": [{"was": a, "now": b} for a, b in self.renamed],
        }


@dataclass(frozen=True, slots=True)
class RefreshResult:
    facts_path: str
    facts: CardFacts
    written: bool
    fetched_cards: int
    fetched_tokens: int
    requests: int
    unresolved: tuple[str, ...]
    changes: Changes

    def to_dict(self) -> dict[str, Any]:
        owned_names = sum(1 for c in self.facts.cards if c.owned)
        return {
            "card_facts": self.facts_path,
            "written": self.written,
            "export": {
                "file": self.facts.export_file,
                "sha256": self.facts.export_sha256,
                "rows": self.facts.export_rows,
            },
            "refreshed": self.facts.refreshed,
            "cards": len(self.facts.cards),
            "tokens": len(self.facts.tokens),
            "owned_card_names": owned_names,
            "owned_cards": sum(c.owned for c in self.facts.cards),
            "fetched": {
                "cards": self.fetched_cards,
                "tokens": self.fetched_tokens,
                "requests": self.requests,
            },
            "unresolved": list(self.unresolved),
            "changes": self.changes.to_dict(),
            "next": _next_step(self),
        }


def _next_step(result: RefreshResult) -> str:
    if result.unresolved:
        return (
            "Some printings did not resolve; check the names against Scryfall, then refresh again."
        )
    if not result.changes.is_empty:
        return "Card facts moved; re-run check over the committed decks before trusting them."
    return "Card facts are current. Compose against them, then run check on the table."


def refresh(
    export: Export,
    facts_path: Path,
    *,
    all_entries: bool = False,
    client: scryfall.Client | None = None,
    today: date | None = None,
    display: str | None = None,
) -> RefreshResult:
    """Recompute ownership offline, fetch what is missing, write the card facts."""
    shown = display or facts_path.name
    # ADR-0007 handles a schema change by regenerating. refresh is the operation
    # that regenerates, so it must not fail on the file it is about to replace.
    previous = _previous(facts_path)
    base = previous or empty(export)

    wanted = {lot.scryfall_id for lot in export.lots}
    if all_entries:
        targets = sorted(wanted | base.printing_ids)
    else:
        targets = sorted(wanted - base.printing_ids)

    fetched: list[Card | Token] = []
    unresolved: tuple[str, ...] = ()
    requests = 0
    if targets:
        caller = client or scryfall.Client()
        found, missing = caller.collection([{"id": scryfall_id} for scryfall_id in targets])
        fetched = scryfall.project_all(found)
        unresolved = tuple(sorted(str(entry.get("id", "")) for entry in missing))
        requests = caller.requests

    merged = _replace_all(base, fetched) if all_entries else _merge(base, fetched)
    changes = _changes(base, merged) if all_entries else Changes()
    facts = _with_ownership(
        replace(
            merged,
            export_file=export.file,
            export_sha256=export.sha256,
            export_rows=export.rows,
            refreshed=(today or date.today()).isoformat() if targets else merged.refreshed,
        ),
        export,
    )

    rendered = render(facts)
    written = not facts_path.exists() or facts_path.read_bytes() != rendered.encode("utf-8")
    if written:
        write(rendered, facts_path)

    return RefreshResult(
        facts_path=shown,
        facts=facts,
        written=written,
        fetched_cards=sum(1 for entry in fetched if isinstance(entry, Card)),
        fetched_tokens=sum(1 for entry in fetched if isinstance(entry, Token)),
        requests=requests,
        unresolved=unresolved,
        changes=changes,
    )


def _previous(path: Path) -> CardFacts | None:
    if not path.exists():
        return None
    try:
        return read(path)
    except ToolError:
        return None  # unreadable or a foreign schema: rebuild it


def _record(entry: OwnedCard | OwnedToken) -> Card | Token:
    return entry.card if isinstance(entry, OwnedCard) else entry.token


def _split(fetched: Sequence[Card | Token]) -> tuple[list[Card], list[Token]]:
    cards = [record for record in fetched if isinstance(record, Card)]
    tokens = [record for record in fetched if isinstance(record, Token)]
    return cards, tokens


def _absorb[E: (Card, Token)](pool: dict[str, E], records: Sequence[E]) -> dict[str, E]:
    for record in records:
        held = pool.get(record.oracle_id)
        pool[record.oracle_id] = record if held is None else _fold(held, record.printings)
    return pool


def _merge(facts: CardFacts, fetched: Sequence[Card | Token]) -> CardFacts:
    """Add what is new and fold new printings into entries already held."""
    fresh_cards, fresh_tokens = _split(fetched)
    cards = _absorb({entry.card.oracle_id: entry.card for entry in facts.cards}, fresh_cards)
    tokens = _absorb({entry.token.oracle_id: entry.token for entry in facts.tokens}, fresh_tokens)
    return _rebuild(facts, cards.values(), tokens.values())


def _replace_all(facts: CardFacts, fetched: Sequence[Card | Token]) -> CardFacts:
    """Rebuild every re-fetched entry from scratch, keeping anything not re-fetched."""
    fresh_cards, fresh_tokens = _split(fetched)
    cards = {entry.card.oracle_id: entry.card for entry in facts.cards}
    tokens = {entry.token.oracle_id: entry.token for entry in facts.tokens}
    cards.update(_absorb({}, fresh_cards))
    tokens.update(_absorb({}, fresh_tokens))
    return _rebuild(facts, cards.values(), tokens.values())


def _fold[E: (Card, Token)](entry: E, printings: Iterable[Printing]) -> E:
    known = {printing.scryfall_id for printing in entry.printings}
    added = tuple(p for p in printings if p.scryfall_id not in known)
    if not added:
        return entry
    combined = sorted(entry.printings + added, key=lambda p: p.scryfall_id)
    return replace(entry, printings=tuple(combined))


def _rebuild(facts: CardFacts, cards: Iterable[Card], tokens: Iterable[Token]) -> CardFacts:
    return replace(
        facts,
        cards=tuple(OwnedCard(card=c, owned=0, owned_by_printing=()) for c in cards),
        tokens=tuple(OwnedToken(token=t, owned=0, owned_by_printing=()) for t in tokens),
    )


def _with_ownership(facts: CardFacts, export: Export) -> CardFacts:
    owned = export.owned_by_printing()

    def attach[E: (OwnedCard, OwnedToken)](entry: E) -> E:
        per = tuple(owned.get(p.scryfall_id, 0) for p in _record(entry).printings)
        return replace(entry, owned=sum(per), owned_by_printing=per)

    return replace(
        facts,
        cards=tuple(attach(entry) for entry in facts.cards),
        tokens=tuple(attach(entry) for entry in facts.tokens),
    )


def _changes(before: CardFacts, after: CardFacts) -> Changes:
    held = {entry.card.oracle_id: entry.card for entry in before.cards}
    legality: list[tuple[str, str, str]] = []
    game_changer: list[tuple[str, bool, bool]] = []
    renamed: list[tuple[str, str]] = []
    for entry in after.cards:
        was = held.get(entry.card.oracle_id)
        if was is None:
            continue
        now = entry.card
        if was.legality != now.legality:
            legality.append((now.name, was.legality, now.legality))
        if was.game_changer != now.game_changer:
            game_changer.append((now.name, was.game_changer, now.game_changer))
        if was.name != now.name:
            renamed.append((was.name, now.name))
    return Changes(tuple(legality), tuple(game_changer), tuple(renamed))


# --- the file ---------------------------------------------------------------


def render(facts: CardFacts) -> str:
    """One entry per line, sorted, so a diff reads. Never json.dump of the whole file."""
    lines = [
        "{",
        f'  "schema": {SCHEMA},',
        "  " + _dumps({"export": _export_block(facts)})[1:-1] + ",",
        f'  "refreshed": {_dumps(facts.refreshed)},',
        '  "cards": [',
    ]
    lines += _entries(facts.cards, _card_dict)
    lines += ["  ],", '  "tokens": [']
    lines += _entries(facts.tokens, _token_dict)
    lines += ["  ]", "}"]
    return "\n".join(lines) + "\n"


def _entries[E](entries: Sequence[E], to_dict: Any) -> list[str]:
    rendered = [f"    {_dumps(to_dict(entry))}" for entry in entries]
    return [line + "," for line in rendered[:-1]] + rendered[-1:]


def _export_block(facts: CardFacts) -> dict[str, Any]:
    return {"file": facts.export_file, "sha256": facts.export_sha256, "rows": facts.export_rows}


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _card_dict(entry: OwnedCard) -> dict[str, Any]:
    card = entry.card
    body = {
        "name": card.name,
        "oracle_id": card.oracle_id,
        "layout": card.layout,
        "type_line": card.type_line,
        "mana_cost": card.mana_cost,
        "cmc": card.cmc,
        "colors": list(card.colors) if card.colors is not None else None,
        "color_identity": list(card.color_identity),
        "produced_mana": list(card.produced_mana) if card.produced_mana is not None else None,
        "oracle_text": card.oracle_text,
        "keywords": list(card.keywords),
        "legality": card.legality,
        "game_changer": card.game_changer,
        "edhrec_rank": card.edhrec_rank,
        "faces": [_face_dict(f) for f in card.faces] if card.faces is not None else None,
        "owned": entry.owned,
        "printings": _printings(card.printings, entry.owned_by_printing),
    }
    return {key: body[key] for key in _CARD_KEYS}


def _token_dict(entry: OwnedToken) -> dict[str, Any]:
    token = entry.token
    body = {
        "oracle_id": token.oracle_id,
        "name": token.name,
        "layout": token.layout,
        "type_line": token.type_line,
        "oracle_text": token.oracle_text,
        "owned": entry.owned,
        "printings": _printings(token.printings, entry.owned_by_printing),
    }
    return {key: body[key] for key in _TOKEN_KEYS}


def _face_dict(face: Face) -> dict[str, Any]:
    return {
        "name": face.name,
        "mana_cost": face.mana_cost,
        "type_line": face.type_line,
        "colors": list(face.colors) if face.colors is not None else None,
        "oracle_text": face.oracle_text,
    }


def _printings(printings: Sequence[Printing], owned: Sequence[int]) -> list[dict[str, Any]]:
    return [
        {
            "scryfall_id": printing.scryfall_id,
            "set": printing.set,
            "set_type": printing.set_type,
            "collector_number": printing.collector_number,
            "rarity": printing.rarity,
            "released_at": printing.released_at,
            "owned": owned[index] if index < len(owned) else 0,
        }
        for index, printing in enumerate(printings)
    ]


def write(rendered: str, path: Path) -> None:
    temporary = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(rendered, encoding="utf-8")
        os.replace(temporary, path)
    except OSError as exc:
        raise ToolError(
            "card_facts_write_failed",
            {"path": str(path), "reason": str(exc)},
            "Check the directory is writable, then run refresh again.",
        ) from exc


def read(path: Path, *, display: str | None = None) -> CardFacts:
    shown = display or path.name
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ToolError(
            "card_facts_not_found", {"path": shown}, "Run refresh against a ManaBox export."
        ) from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolError(
            "card_facts_unreadable", {"path": shown}, "Delete the file and run refresh again."
        ) from exc
    if payload.get("schema") != SCHEMA:
        raise ToolError(
            "card_facts_schema_unknown",
            {"path": shown, "schema": payload.get("schema"), "expected": SCHEMA},
            "Run refresh to regenerate; this project does not migrate schemas (ADR-0007).",
        )
    export = payload.get("export") or {}
    return CardFacts(
        export_file=export.get("file", ""),
        export_sha256=export.get("sha256", ""),
        export_rows=export.get("rows", 0),
        refreshed=payload.get("refreshed"),
        cards=tuple(_read_card(entry) for entry in payload.get("cards", [])),
        tokens=tuple(_read_token(entry) for entry in payload.get("tokens", [])),
    )


def _read_card(entry: dict[str, Any]) -> OwnedCard:
    printings, owned = _read_printings(entry.get("printings", []))
    faces = entry.get("faces")
    return OwnedCard(
        card=Card(
            name=entry["name"],
            oracle_id=entry["oracle_id"],
            layout=entry["layout"],
            type_line=entry["type_line"],
            mana_cost=entry.get("mana_cost"),
            cmc=entry.get("cmc", 0),
            colors=_maybe(entry.get("colors")),
            color_identity=tuple(entry.get("color_identity") or ()),
            produced_mana=_maybe(entry.get("produced_mana")),
            oracle_text=entry.get("oracle_text"),
            keywords=tuple(entry.get("keywords") or ()),
            legality=entry["legality"],
            game_changer=bool(entry.get("game_changer")),
            edhrec_rank=entry.get("edhrec_rank"),
            faces=tuple(_read_face(f) for f in faces) if faces else None,
            printings=printings,
        ),
        owned=entry.get("owned", 0),
        owned_by_printing=owned,
    )


def _read_token(entry: dict[str, Any]) -> OwnedToken:
    printings, owned = _read_printings(entry.get("printings", []))
    return OwnedToken(
        token=Token(
            oracle_id=entry["oracle_id"],
            name=entry["name"],
            layout=entry["layout"],
            type_line=entry.get("type_line", ""),
            oracle_text=entry.get("oracle_text"),
            printings=printings,
        ),
        owned=entry.get("owned", 0),
        owned_by_printing=owned,
    )


def _read_face(entry: dict[str, Any]) -> Face:
    return Face(
        name=entry["name"],
        mana_cost=entry.get("mana_cost"),
        type_line=entry.get("type_line"),
        colors=_maybe(entry.get("colors")),
        oracle_text=entry.get("oracle_text"),
    )


def _read_printings(
    entries: Sequence[dict[str, Any]],
) -> tuple[tuple[Printing, ...], tuple[int, ...]]:
    printings = tuple(
        Printing(
            scryfall_id=entry["scryfall_id"],
            set=entry["set"],
            set_type=entry.get("set_type", ""),
            collector_number=entry.get("collector_number", ""),
            rarity=entry.get("rarity", ""),
            released_at=entry.get("released_at", ""),
        )
        for entry in entries
    )
    return printings, tuple(entry.get("owned", 0) for entry in entries)


def _maybe(value: Any) -> tuple[str, ...] | None:
    return tuple(value) if isinstance(value, list) else None
