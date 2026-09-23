"""Owns the rules and the measurements: violations block, metrics inform.

Every number here derives from Scryfall card facts (ADR-0002). Nothing reads a
label the composer applied, and nothing the checker did not measure may appear
in an artifact.

A field the design has not settled is absent from the output, never null and
never a guessed default — a corollary of ADR-0002 and ADR-0006: an absent field
cannot be cited, a null one invites a zero.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from deck_composer.errors import ToolError
from deck_composer.facts import CardFacts, OwnedCard
from deck_composer.manabox import Deck, Entry
from deck_composer.rules import Category, Rules, Targets, searchable

DECK_SIZE = 100
LAND_FLOOR = 35
TABLE_SIZE = 4  # the lexicon's table is four decks
BRACKET = 2
GAME_CHANGER_CAP = 0
COLOR_ORDER = "WUBRG"

# Plural forms the collection needs. A tribe's text mention is soft by design.
PLURALS: dict[str, str] = {"Mouse": "Mice", "Wolf": "Wolves", "Elf": "Elves", "Dwarf": "Dwarves"}


@dataclass(frozen=True, slots=True)
class Violation:
    """A hard-rule failure with a reason. Blocks artifacts; reported as data."""

    code: str
    detail: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"violation": self.code, **self.detail}


@dataclass(frozen=True, slots=True)
class DeckReport:
    name: str
    path: str
    commander: tuple[str, ...]
    color_identity: tuple[str, ...]
    violations: tuple[Violation, ...]
    metrics: dict[str, Any]

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_dict(self) -> dict[str, Any]:
        """A built deck's `passed` is its measured result, present once it exists.

        It judges deck-level rules only, which the deck alone determines. What an
        unbuilt seat can still change — ownership across the four — is judged by
        `table.passed`, which is withheld until every seat is built (ADR-0006).
        """
        return {
            "deck": self.name,
            "path": self.path,
            "commander": list(self.commander),
            "color_identity": list(self.color_identity),
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "metrics": self.metrics,
        }


@dataclass(frozen=True, slots=True)
class TableReport:
    decks: tuple[DeckReport, ...]
    violations: tuple[Violation, ...]
    metrics: dict[str, Any]
    export_sha256: str
    refreshed: str | None
    rules: Rules
    targets: Targets
    seats: tuple[dict[str, Any], ...] = ()  # commanders whose decks are not built yet

    @property
    def passed(self) -> bool:
        """False while any seat is unbuilt: an empty table must not pass vacuously."""
        return self.complete and self.violation_count == 0

    @property
    def complete(self) -> bool:
        """Every seat of a table is built: four decks and no seat still a commander.

        Counting only the seats passed as --commander was not enough. `check` on
        one deck alone declares no seat, and was certified as a finished table —
        `passed`, `table.passed` and "render the decklists" on a quarter of one,
        with the three missing seats charged nothing against the basic budget.
        """
        return not self.seats and len(self.decks) == TABLE_SIZE

    @property
    def violation_count(self) -> int:
        """Every violation at the table, including commanders at unbuilt seats."""
        return (
            len(self.violations)
            + sum(len(deck.violations) for deck in self.decks)
            + sum(len(seat["violations"]) for seat in self.seats)
        )

    def to_dict(self) -> dict[str, Any]:
        # A verdict is present only when its subject exists in full (ADR-0006).
        # The table and its table-level rules need every seat, so both are
        # withheld while one is unbuilt: `all()` over a subject that does not yet
        # exist is vacuously true and reads as a pass. A built deck's verdict is
        # not that, and stays. Renaming a vacuous true would not help.
        certify = self.complete
        return {
            "bracket": BRACKET,
            "snapshot": {
                "export_sha256": self.export_sha256,
                "card_facts_refreshed": self.refreshed,
                "rules_version": self.rules.version,
                "rules_hash": self.rules.content_hash,
                "targets_version": self.targets.version,
            },
            **({"passed": self.passed} if certify else {}),
            "decks": [deck.to_dict() for deck in self.decks] + list(self.seats),
            "table": {
                # table-level rules only, such as ownership across the four
                **({"passed": not self.violations} if certify else {}),
                "violations": [v.to_dict() for v in self.violations],
                "metrics": self.metrics,
            },
            "next": self._next(),
        }

    def _next(self) -> str:
        """Says what this stage of the table is for, and never certifies more.

        `passed` is withheld while a seat is unbuilt, and this sentence must not
        say in prose what that field refuses to: a checkpoint told "no violations,
        render the decklists" is gen 1's false green in a different field.
        """
        if self.violation_count:
            return (
                f"{self.violation_count} violation(s). Fix them and run check again; "
                "artifacts stay blocked until clean."
            )
        short = self.metrics.get("overcommitted") or []
        warning = (
            f" The table is on course to run out of {', '.join(short)}; "
            "adjust before building further."
            if short
            else ""
        )
        scarcest = self.metrics.get("scarcest_basic")
        order = _build_order_sentence(scarcest) if scarcest else ""
        declared = len(self.decks) + len(self.seats)
        if declared < TABLE_SIZE:
            # Over part of a table the budget is a sound bound — a named overrun is
            # real — but an empty list is no evidence, and the build order is
            # withheld because the scarcest basic can move when the rest arrive.
            warning += (
                f" Only {declared} of the table's {TABLE_SIZE} seats are declared, so the "
                "build order is withheld and the basic budget covers those alone; an "
                "empty overcommitted list is not evidence. Pass the rest as --commander."
            )
        if self.seats and not self.decks:
            return (
                "This is the checkpoint: no deck exists yet, so nothing is certified. "
                "Once the commanders are picked, build scarcest basic first." + order + warning
            )
        if self.seats:
            return (
                f"The built seats are clean, but {len(self.seats)} seat(s) are unbuilt, so "
                "the table is not certified. Run check again after each seat, with the "
                "rest passed as --commander." + order + warning
            )
        if not self.complete:
            given = len(self.decks)
            return (
                f"{given} of the table's {TABLE_SIZE} seats are here and the rest were not "
                "declared, so nothing is certified and the basic budget charges the "
                "missing seats nothing. Pass them as --commander so the budget spans "
                "the whole table."
            )
        return "No violations. Render the decklists, then write the playbooks from these metrics."


# --- card lookups -----------------------------------------------------------


def resolve(facts: CardFacts, name: str, *, where: str) -> OwnedCard:
    """A name the card facts lack is a contract failure, not a violation (ADR-0006)."""
    entry = facts.card(name)
    if entry is None:
        raise ToolError(
            "unknown_card",
            {"card": name, "where": where},
            "Run refresh so the card facts carry this name, or fix the spelling in the deck.",
        )
    return entry


def front(type_line: str) -> str:
    return type_line.split("//")[0].strip()


def is_land(card: OwnedCard) -> bool:
    return "Land" in front(card.card.type_line)


def is_basic(card: OwnedCard) -> bool:
    return "Basic" in front(card.card.type_line) and is_land(card)


def is_creature(card: OwnedCard) -> bool:
    return "Creature" in front(card.card.type_line)


def is_legendary_creature(card: OwnedCard) -> bool:
    line = front(card.card.type_line)
    return "Legendary" in line and "Creature" in line


def subtypes(type_line: str) -> tuple[str, ...]:
    """The creature types on the front face, after the em dash."""
    line = front(type_line)
    if "—" not in line:
        return ()
    return tuple(part for part in line.split("—", 1)[1].split() if part.isalpha())


def _text_blob(card: OwnedCard) -> str:
    parts = [card.card.oracle_text or ""]
    parts += [face.oracle_text or "" for face in card.card.faces or ()]
    parts += [face.type_line or "" for face in card.card.faces or ()]
    return "\n".join(parts)


def tribal_core(
    facts: CardFacts, tribe: str, identity: Iterable[str], *, excluding: str = ""
) -> dict[str, int]:
    """Two numbers, never one: the type line is an oracle fact, a text mention is soft.

    The commander does not count toward its own tribal core. The number answers
    how tribal the 99 can be, and the commander is not one of the 99; counting it
    adds a constant 1 to every candidate, which carries no comparative
    information while inflating what is actually buildable.
    """
    allowed = set(identity)
    plural = PLURALS.get(tribe, tribe + "s")
    line = re.compile(rf"\b{re.escape(tribe)}\b")
    mention = re.compile(rf"\b({re.escape(tribe)}|{re.escape(plural)})\b")
    type_line = 0
    text = 0
    for entry in facts.cards:
        if not entry.owned or entry.card.legality != "legal":
            continue
        if entry.card.name == excluding:
            continue
        if not set(entry.card.color_identity) <= allowed:
            continue
        if line.search(entry.card.type_line):
            type_line += 1
        elif mention.search(_text_blob(entry)):
            text += 1
    return {"type_line": type_line, "text_mention": text, "total": type_line + text}


# --- the check --------------------------------------------------------------


def in_category(category: Category, card: OwnedCard) -> bool:
    text = searchable(card.card.type_line, card.card.oracle_text, card.card.faces)
    return category.matches(card.card.name, text, type_line=card.card.type_line)


def ceiling(facts: CardFacts, category: Category, identity: Iterable[str]) -> int:
    """The most the owned collection could supply to a deck of this colour identity.

    Distinct names, not copies: singleton caps every nonbasic at one per deck, so
    owning four Fountainport Bells still supplies one ramp slot. These categories
    exclude lands, where the basic exemption would matter.

    Colour identity alone. Cross-deck contention is reported separately, because a
    ceiling that moved with build order could not be reasoned about (ADR-0010).
    """
    allowed = set(identity)
    return sum(
        1
        for entry in facts.cards
        if entry.owned
        and entry.card.legality == "legal"
        and set(entry.card.color_identity) <= allowed
        and in_category(category, entry)
    )


@dataclass
class _Built:
    deck: Deck
    commander: tuple[OwnedCard, ...]
    cards: list[tuple[Entry, OwnedCard]] = field(default_factory=list)

    @property
    def identity(self) -> tuple[str, ...]:
        union = {c for entry in self.commander for c in entry.card.color_identity}
        return tuple(c for c in COLOR_ORDER if c in union)


def check(
    decks: Sequence[Deck],
    facts: CardFacts,
    rules: Rules,
    targets: Targets,
    pending: Sequence[str] = (),
) -> TableReport:
    """One table, at whatever stage it has reached.

    `pending` names the commanders whose decks are not built yet. A table with
    four commanders and no decks is the ADR-0008 checkpoint; a table with one
    deck and three commanders is the scarcest-basic-first build order of
    ADR-0005 after its first seat. Both are this table, earlier, so both are
    this object with the deck-dependent fields absent.

    Three inputs have no correct output and are contract failures (ADR-0006):
    more than four seats, since a table of five is not a table; the same deck
    given twice, which would charge every card in it to the budget twice; and the
    same commander at two seats. A table is four distinct commanders — ADR-0008's
    1,771 sets alongside Wick are C(23, 3) — and a repeat counts as four seats
    what is three: a built seat declared again, or one seat named twice, charged
    twice while a real seat is left out, with the build order named over it.
    """
    paths = [deck.path for deck in decks]
    repeated = sorted({path for path in paths if paths.count(path) > 1})
    if repeated:
        raise ToolError(
            "deck_given_twice",
            {"decks": repeated},
            "Give each deck once; a table is four different decks.",
        )
    if len(decks) + len(pending) > TABLE_SIZE:
        raise ToolError(
            "too_many_seats",
            {"decks": len(decks), "commanders": len(pending), "table_size": TABLE_SIZE},
            f"A table is {TABLE_SIZE} seats; give at most {TABLE_SIZE} decks and "
            "commanders between them.",
        )
    built = [_build(deck, facts) for deck in decks]
    # Resolved names, so a face name cannot slip a repeat past as an alias.
    commanders = [entry.card.name for b in built for entry in b.commander]
    commanders += [resolve(facts, name, where="seat").card.name for name in pending]
    repeated_commanders = sorted({n for n in commanders if commanders.count(n) > 1})
    if repeated_commanders:
        raise ToolError(
            "commander_declared_twice",
            {"commanders": repeated_commanders},
            "Give each commander once: a built seat is its deck file, an unbuilt one a "
            "--commander, never both, and a table is four distinct commanders.",
        )
    ceilings: dict[tuple[str, tuple[str, ...]], int] = {}
    reports = tuple(_deck_report(entry, facts, rules, targets, ceilings) for entry in built)
    seats = tuple(
        _seat(resolve(facts, name, where="seat"), facts, rules, targets, ceilings)
        for name in pending
    )
    return TableReport(
        decks=reports,
        violations=tuple(_table_violations(built, facts)),
        metrics=_table_metrics(built, facts, reports, seats),
        export_sha256=facts.export_sha256,
        refreshed=facts.refreshed,
        rules=rules,
        targets=targets,
        seats=seats,
    )


def _seat(
    entry: OwnedCard,
    facts: CardFacts,
    rules: Rules,
    targets: Targets,
    ceilings: dict[tuple[str, tuple[str, ...]], int],
) -> dict[str, Any]:
    """A seat with a commander and no deck: the same entry, with what it has."""
    identity = tuple(c for c in COLOR_ORDER if c in set(entry.card.color_identity))
    violations = []
    if not is_legendary_creature(entry):
        violations.append(
            Violation(
                "commander_ineligible",
                {"card": entry.card.name, "type_line": entry.card.type_line},
            )
        )
    if entry.card.legality != "legal":
        violations.append(
            Violation("not_legal", {"card": entry.card.name, "legality": entry.card.legality})
        )
    categories = {}
    for category in rules.metrics:
        key = (category.name, identity)
        if key not in ceilings:
            ceilings[key] = ceiling(facts, category, identity)
        categories[category.name] = _with_context(None, targets.of(category.name), ceilings[key])
    return {
        "commander": [entry.card.name],
        "color_identity": list(identity),
        "violations": [v.to_dict() for v in violations],
        "metrics": {
            "pool": _pool(facts, identity),
            "tribal_core": {
                tribe: {"ceiling": tribal_core(facts, tribe, identity, excluding=entry.card.name)}
                for tribe in subtypes(entry.card.type_line)
            },
            "categories": categories,
        },
    }


def _build(deck: Deck, facts: CardFacts) -> _Built:
    commander = tuple(
        resolve(facts, entry.name, where=f"{deck.name}/commander") for entry in deck.commander
    )
    built = _Built(deck=deck, commander=commander)
    for entry in deck.counted:
        built.cards.append((entry, resolve(facts, entry.name, where=deck.name)))
    return built


def _deck_report(
    built: _Built,
    facts: CardFacts,
    rules: Rules,
    targets: Targets,
    ceilings: dict[tuple[str, tuple[str, ...]], int],
) -> DeckReport:
    return DeckReport(
        name=built.deck.name,
        path=built.deck.path,
        commander=tuple(entry.card.name for entry in built.commander),
        color_identity=built.identity,
        violations=tuple(_deck_violations(built, rules)),
        metrics=_deck_metrics(built, facts, rules, targets, ceilings),
    )


def _deck_violations(built: _Built, rules: Rules) -> list[Violation]:
    found: list[Violation] = []
    deck = built.deck
    identity = set(built.identity)

    if not built.commander:
        found.append(Violation("commander_missing", {"detail": "the deck names no commander"}))
    for entry in built.commander:
        if not is_legendary_creature(entry):
            found.append(
                Violation(
                    "commander_ineligible",
                    {"card": entry.card.name, "type_line": entry.card.type_line},
                )
            )

    size = deck.size
    if size != DECK_SIZE:
        found.append(Violation("deck_size", {"size": size, "expected": DECK_SIZE}))

    # Singleton covers lands. Gen 1 shipped four Uncharted Haven against a green
    # check that inspected nonland cards only; this is the regression it guards.
    seen: dict[str, int] = {}
    for entry, card in built.cards:
        if is_basic(card):
            continue
        seen[card.card.name] = seen.get(card.card.name, 0) + entry.quantity
    for name, quantity in sorted(seen.items()):
        if quantity > 1:
            found.append(Violation("singleton", {"card": name, "quantity": quantity}))

    for _entry, card in built.cards:
        if card.card.legality != "legal":
            found.append(
                Violation("not_legal", {"card": card.card.name, "legality": card.card.legality})
            )
        outside = sorted(set(card.card.color_identity) - identity)
        if outside:
            found.append(
                Violation(
                    "color_identity",
                    {
                        "card": card.card.name,
                        "card_identity": list(card.card.color_identity),
                        "outside": outside,
                    },
                )
            )
        if card.card.game_changer:
            found.append(
                Violation("game_changer", {"card": card.card.name, "cap": GAME_CHANGER_CAP})
            )

    # Bracket 2 caps these at zero. Detection is patterns over oracle data, never
    # a label the composer applied (ADR-0002, ADR-0009).
    for category in rules.violations:
        for _entry, card in built.cards:
            if in_category(category, card):
                found.append(Violation(category.name, {"card": card.card.name, "cap": 0}))

    lands = sum(entry.quantity for entry, card in built.cards if is_land(card))
    if lands < LAND_FLOOR:
        found.append(Violation("land_floor", {"lands": lands, "floor": LAND_FLOOR}))
    return found


def _deck_metrics(
    built: _Built,
    facts: CardFacts,
    rules: Rules,
    targets: Targets,
    ceilings: dict[tuple[str, tuple[str, ...]], int],
) -> dict[str, Any]:
    lands = [(e, c) for e, c in built.cards if is_land(c)]
    nonland = [(e, c) for e, c in built.cards if not is_land(c)]
    creatures = sum(e.quantity for e, c in built.cards if is_creature(c))
    total_mv = sum(c.card.cmc * e.quantity for e, c in nonland)
    count = sum(e.quantity for e, c in nonland)

    curve: dict[str, int] = {}
    for entry, card in nonland:
        bucket = "7+" if card.card.cmc >= 7 else str(int(card.card.cmc))
        curve[bucket] = curve.get(bucket, 0) + entry.quantity

    sources: dict[str, int] = {}
    for entry, card in lands:
        for color in card.card.produced_mana or ():
            if color in COLOR_ORDER:
                sources[color] = sources.get(color, 0) + entry.quantity

    tribes = {}
    for entry in built.commander:
        for tribe in subtypes(entry.card.type_line):
            tribes[tribe] = {
                **_core_in_deck(built, tribe),
                "ceiling": tribal_core(facts, tribe, built.identity, excluding=entry.card.name),
            }

    categories: dict[str, Any] = {}
    for category in rules.metrics:
        key = (category.name, built.identity)
        if key not in ceilings:
            ceilings[key] = ceiling(facts, category, built.identity)
        categories[category.name] = _with_context(
            sum(e.quantity for e, c in built.cards if in_category(category, c)),
            targets.of(category.name),
            ceilings[key],
        )

    lands_total = sum(e.quantity for e, _ in lands)
    average = round(total_mv / count, 2) if count else 0
    return {
        "pool": _pool(facts, built.identity),
        "size": built.deck.size,
        "lands": lands_total,
        "lands_target": _target_only(targets.of("lands")),
        "basics": _basics_by_name(lands),
        "nonbasic_lands": sum(e.quantity for e, c in lands if not is_basic(c)),
        "creatures": creatures,
        "average_mana_value": average,
        "average_mana_value_target": _target_only(targets.of("average_mana_value")),
        "categories": categories,
        "curve": {key: curve[key] for key in sorted(curve, key=_curve_order)},
        "color_sources": {c: sources[c] for c in COLOR_ORDER if c in sources},
        "tribal_core": tribes,
        "maybeboard": sum(entry.quantity for entry in built.deck.maybeboard),
    }


def _build_order_sentence(scarcest: dict[str, Any]) -> str:
    """The seat to build next, with the reason that actually decided it."""
    seat, basic = scarcest["build_first"], scarcest["basic"]
    reason = {
        "sole": "no other seat claims it, so there was nothing to compare",
        "colours": (
            "of the seats claiming it, this one has the most colours, so its estimate "
            "is the least reliable"
        ),
        "claim": "of the seats claiming it, this one ties on colours and has the largest claim",
        "name": (
            "the seats claiming it tie on colours and claim, so the arbitrary break on "
            "commander name decides"
        ),
    }[scarcest["decided_by"]]
    return (
        f" ADR-0005 builds {seat}'s seat next. {basic} is the basic with the least "
        f"headroom, and {reason}."
    )


def _basics_by_name(lands: Sequence[tuple[Entry, OwnedCard]]) -> dict[str, int]:
    """Summed, never overwritten: a list may carry one basic on several lines.

    The composer writes basics bare, one line per name, but a hand-edited or
    imported list need not — `20 Forest (FDN) 280` and `15 Forest` are 35 Forests.
    """
    totals: dict[str, int] = {}
    for entry, card in lands:
        if is_basic(card):
            totals[card.card.name] = totals.get(card.card.name, 0) + entry.quantity
    return dict(sorted(totals.items()))


def _with_context(count: int | None, target: dict[str, float] | None, limit: int) -> dict[str, Any]:
    """`ramp 2 (target 10, ceiling 2)` — a build failure and a collection fact differ.

    A target the collection structurally cannot meet is still reported: with the
    ceiling beside it the number says the collection is short, which is actionable.
    """
    body: dict[str, Any] = {"ceiling": limit}
    if count is not None:  # absent before any deck exists
        body["count"] = count
    if target:
        body["target"] = _target_only(target)
    return body


def _target_only(target: dict[str, float] | None) -> Any:
    if not target:
        return None
    if "max" in target and "min" in target:
        return [target["min"], target["max"]]
    return target.get("min", target.get("max"))


def _curve_order(bucket: str) -> int:
    return 99 if bucket == "7+" else int(bucket)


def _core_in_deck(built: _Built, tribe: str) -> dict[str, int]:
    """The tribe's presence in the 99. The commander is excluded from its own core."""
    plural = PLURALS.get(tribe, tribe + "s")
    line = re.compile(rf"\b{re.escape(tribe)}\b")
    mention = re.compile(rf"\b({re.escape(tribe)}|{re.escape(plural)})\b")
    type_line = 0
    text = 0
    commanders = {entry.card.name for entry in built.commander}
    for entry, card in built.cards:
        if card.card.name in commanders:
            continue
        if line.search(card.card.type_line):
            type_line += entry.quantity
        elif mention.search(_text_blob(card)):
            text += entry.quantity
    return {"type_line": type_line, "text_mention": text, "total": type_line + text}


def _table_violations(built: Sequence[_Built], facts: CardFacts) -> list[Violation]:
    """Ownership is a table property: the four decks draw on one shoebox (ADR-0005)."""
    used: dict[str, int] = {}
    for deck in built:
        for entry, card in deck.cards:
            used[card.card.name] = used.get(card.card.name, 0) + entry.quantity
    found: list[Violation] = []
    for name, quantity in sorted(used.items()):
        entry = facts.card(name)
        owned = entry.owned if entry else 0
        if quantity > owned:
            found.append(
                Violation("ownership", {"card": name, "used": quantity, "owned": owned}),
            )
    return found


def _table_metrics(
    built: Sequence[_Built],
    facts: CardFacts,
    reports: Sequence[DeckReport],
    seats: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    # Every colour's basic is a row, owned or not. A basic owned at zero is the
    # most important row in this table — trade away the last Swamp and it is the
    # one a black seat will overrun — so it can never be the row that vanishes
    # (ADR-0005). Any other basic enters when owned or when a deck uses it.
    basics: dict[str, dict[str, Any]] = {
        name: {"owned": _owned(facts, name), "used": 0} for name in BASIC_FOR_COLOR.values()
    }
    for entry in facts.cards:
        if is_basic(entry) and entry.owned:
            basics.setdefault(entry.card.name, {"owned": entry.owned, "used": 0})
    for deck in built:
        for entry, card in deck.cards:
            if is_basic(card):
                block = basics.setdefault(card.card.name, {"owned": card.owned, "used": 0})
                block["used"] += entry.quantity

    # The commanders were picked partly on the checkpoint's estimate, which no
    # list has to honour. Built seats are measured; unbuilt ones can only be
    # estimated. Reporting both is what makes a choice made on a figure that did
    # not hold visible (ADR-0005), and building the scarcest basic first is what
    # turns the largest of those estimates into a measurement early.
    on_built = _estimated_demand([deck.identity for deck in built])
    on_unbuilt = _estimated_demand([tuple(seat["color_identity"]) for seat in seats])

    generous = []
    for name, block in basics.items():
        pending = on_unbuilt.get(name, 0)
        block["remaining"] = block["owned"] - block["used"] - pending
        if seats:
            block["unbuilt_estimate"] = pending
        if built:  # nothing measured yet means nothing to compare
            block["estimated_used"] = on_built.get(name, 0)
            block["divergence"] = block["used"] - block["estimated_used"]
            if block["divergence"] > 0:
                generous.append(name)

    # A projected overrun, not a violation: part of it is an estimate, and this
    # project does not block on one. Measured overuse is already an ownership
    # violation. Naming it here is what makes building the scarcest basic first
    # worth doing — the set is seen to be over budget at deck one rather than
    # at deck four.
    overcommitted = sorted(name for name, block in basics.items() if block["remaining"] < 0)
    metrics: dict[str, Any] = {
        "decks": len(built),
        "seats_unbuilt": len(seats),
        "basis": _basis(bool(built), bool(seats)),
        "overcommitted": overcommitted,
        "basic_budget": {name: basics[name] for name in sorted(basics)},
    }
    # The build order is withheld until all four seats are declared (ADR-0005).
    # Adding a seat only adds demand, so the budget over part of a table is a
    # sound bound and stays; but the scarcest basic is an argmin, not monotone,
    # and can move to another basic or to a seat not yet declared.
    declared = len(built) + len(seats)
    scarcest = scarcest_basic(basics, seats) if declared == TABLE_SIZE else None
    if scarcest is not None:
        metrics["scarcest_basic"] = scarcest
    if built:
        metrics["estimate"] = {
            "basis": _ESTIMATE_BASIS,
            "divergence": "measured minus estimated; positive means the estimate was generous",
            "generous_for": sorted(generous),
        }
        metrics["spread"] = _spread(reports)
    return metrics


def scarcest_basic(
    basics: dict[str, dict[str, Any]], seats: Sequence[dict[str, Any]]
) -> dict[str, Any] | None:
    """The scarcest basic, and the unbuilt seat ADR-0005 builds first against it.

    Computed rather than chosen: it reads colour identity and projected headroom
    and picks nothing about any deck. Left to the composer, it would be a fact
    the builder derives about its own picks, which ADR-0002 forbids.

    The scarcest basic has the least projected headroom — owned, less measured,
    less estimated for the unbuilt seats — among the basics an unbuilt seat
    claims; 39 of 40 Plains claimed is scarcer than 10 of 38 Swamps, and a basic
    no unbuilt seat claims cannot be the one worth measuring early.

    The seat built first is the claimant with the most colours, because an even
    split errs by about 2 for two colours and by 3 to 6 in the generous
    direction for three: it is the least reliable estimate, the one worth
    turning into a measurement. Ties break to the largest claim, and an exact
    tie on both to the commander name that sorts first. That last tie is the
    common case — seats with the same colour count make the same claim, so once
    the three-colour seat is built the two-colour ones tie every time — and the
    break is arbitrary. What it must not be is the order the composer listed the
    seats in, which would let the writing of a list steer a tool decision; so
    nothing in this block depends on input order, the claimants included.

    The rejected rule built the largest claim first. Under an even split a
    two-colour seat out-claims a three-colour one, so it never built the
    three-colour seat at any table tested — the opposite of its purpose.
    """
    claims = [
        {
            "commander": seat["commander"][0],
            "colours": len(seat["color_identity"]),
            "demand": _estimated_demand([tuple(seat["color_identity"])]),
        }
        for seat in seats
    ]
    claimed = [name for name in basics if any(claim["demand"].get(name, 0) for claim in claims)]
    if not claimed:
        return None
    basic = min(claimed, key=lambda name: (basics[name]["remaining"], basics[name]["owned"], name))
    claimants = sorted(
        (
            {"commander": c["commander"], "colours": c["colours"], "estimated": c["demand"][basic]}
            for c in claims
            if c["demand"].get(basic, 0)
        ),
        key=lambda c: c["commander"],
    )
    first = min(claimants, key=lambda c: (-c["colours"], -c["estimated"], c["commander"]))
    return {
        "basic": basic,
        "remaining": basics[basic]["remaining"],
        "claimants": claimants,
        "build_first": first["commander"],
        "decided_by": _decided_by(first, claimants),
    }


def _decided_by(first: dict[str, Any], claimants: Sequence[dict[str, Any]]) -> str:
    """Which clause of the rule picked the seat, so nothing claims a reason it lacks.

    Only a win on colours means the seat's estimate is the least reliable. A win
    on the name tie means the claimants were equal and the break was arbitrary,
    and saying "least reliable" there would state a reason that did not decide.
    A sole claimant was compared with nothing, and says so.
    """
    rivals = [c for c in claimants if c is not first]
    if not rivals:
        # `all()` over no rivals is vacuously true, and read as a win on colours
        # it claimed a comparison with nobody — the vacuous-verdict shape again,
        # this time in a reason rather than a `passed`.
        return "sole"
    if all(c["colours"] < first["colours"] for c in rivals):
        return "colours"
    level = [c for c in rivals if c["colours"] == first["colours"]]
    if all(c["estimated"] < first["estimated"] for c in level):
        return "claim"
    return "name"


def _owned(facts: CardFacts, name: str) -> int:
    entry = facts.card(name)
    return entry.owned if entry else 0


def _basis(measured: bool, estimated: bool) -> str:
    if measured and estimated:
        return f"built seats measured; unbuilt seats estimated by {_ESTIMATE_BASIS}"
    if measured:
        return "measured from the lists"
    return f"estimated: {_ESTIMATE_BASIS}"


def _spread(reports: Sequence[DeckReport]) -> dict[str, Any]:
    """The spread across the four decks, on four axes, with no threshold on any.

    A band calibrated from gen 1's decks would have been invention wearing
    calibration's clothes, so there is none (ADR-0010). The table review is
    required to state these four numbers; that is what stops an unthresholded
    number going unread.
    """

    def axis(values: list[float]) -> dict[str, Any]:
        return {
            "values": values,
            "min": min(values, default=0),
            "max": max(values, default=0),
            "spread": round(max(values, default=0) - min(values, default=0), 2),
        }

    metrics = [report.metrics for report in reports]
    interaction = [
        m.get("categories", {}).get("targeted_interaction", {}).get("count", 0) for m in metrics
    ]
    return {
        "note": "no threshold; the table review states these (ADR-0010)",
        "lands": axis([m["lands"] for m in metrics]),
        "average_mana_value": axis([m["average_mana_value"] for m in metrics]),
        "creatures": axis([m["creatures"] for m in metrics]),
        "targeted_interaction": axis(interaction),
    }


# --- the checkpoint ---------------------------------------------------------


def checkpoint(
    facts: CardFacts, names: Sequence[str], rules: Rules, targets: Targets
) -> dict[str, Any]:
    """The table before any deck exists: `check` with every seat still a commander."""
    return check((), facts, rules, targets, pending=names).to_dict()


def _pool(facts: CardFacts, identity: Sequence[str]) -> dict[str, int]:
    allowed = set(identity)
    names = 0
    copies = 0
    for entry in facts.cards:
        if not entry.owned or entry.card.legality != "legal" or is_land(entry):
            continue
        if set(entry.card.color_identity) <= allowed:
            names += 1
            copies += entry.owned
    return {"legal_nonland_names": names, "copies": copies}


BASIC_FOR_COLOR = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}
_ESTIMATE_BASIS = "an even split of the 35-land floor across each deck's colours"


def _estimated_demand(identities: Sequence[Sequence[str]]) -> dict[str, int]:
    """What an unbuilt seat is charged against the basic budget.

    Two known errors, in opposite directions. No real deck splits its lands
    evenly across its colours, and for a three-colour deck with a primary colour
    that error runs generous — the dangerous way. Against that, this charges the
    whole land floor to basics and assumes no nonbasic land absorbs a slot,
    where gen 1's four decks absorbed two to six each, which runs conservative.

    Neither is corrected here. A correction factor would be invented, and the
    measured figure replaces the estimate seat by seat as decks are built, which
    is why ADR-0005 builds the scarcest basic first.
    """
    demand = dict.fromkeys(BASIC_FOR_COLOR, 0.0)
    for identity in identities:
        if not identity:
            continue
        share = LAND_FLOOR / len(identity)
        for colour in identity:
            demand[colour] += share
    return {BASIC_FOR_COLOR[colour]: round(amount) for colour, amount in demand.items()}
