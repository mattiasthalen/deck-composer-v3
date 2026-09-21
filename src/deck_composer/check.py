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

    @property
    def passed(self) -> bool:
        return not self.violations and all(deck.passed for deck in self.decks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bracket": BRACKET,
            "snapshot": {
                "export_sha256": self.export_sha256,
                "card_facts_refreshed": self.refreshed,
                "rules_version": self.rules.version,
                "rules_hash": self.rules.content_hash,
                "targets_version": self.targets.version,
            },
            "passed": self.passed,
            "decks": [deck.to_dict() for deck in self.decks],
            "table": {
                "passed": not self.violations,
                "violations": [v.to_dict() for v in self.violations],
                "metrics": self.metrics,
            },
            "next": self._next(),
        }

    def _next(self) -> str:
        if self.passed:
            return (
                "No violations. Render the decklists, then write the playbooks from these metrics."
            )
        count = len(self.violations) + sum(len(d.violations) for d in self.decks)
        return (
            f"{count} violation(s). Fix them and run check again; "
            "artifacts stay blocked until clean."
        )


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


def check(decks: Sequence[Deck], facts: CardFacts, rules: Rules, targets: Targets) -> TableReport:
    built = [_build(deck, facts) for deck in decks]
    ceilings: dict[tuple[str, tuple[str, ...]], int] = {}
    reports = tuple(_deck_report(entry, facts, rules, targets, ceilings) for entry in built)
    return TableReport(
        decks=reports,
        violations=tuple(_table_violations(built, facts)),
        metrics=_table_metrics(built, facts, reports),
        export_sha256=facts.export_sha256,
        refreshed=facts.refreshed,
        rules=rules,
        targets=targets,
    )


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
        "basics": {
            card.card.name: entry.quantity
            for entry, card in sorted(lands, key=lambda p: p[1].card.name)
            if is_basic(card)
        },
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
    built: Sequence[_Built], facts: CardFacts, reports: Sequence[DeckReport]
) -> dict[str, Any]:
    basics: dict[str, dict[str, int]] = {}
    for entry in facts.cards:
        if is_basic(entry) and entry.owned:
            basics[entry.card.name] = {"owned": entry.owned, "used": 0, "remaining": entry.owned}
    for deck in built:
        for entry, card in deck.cards:
            if is_basic(card) and card.card.name in basics:
                block = basics[card.card.name]
                block["used"] += entry.quantity
                block["remaining"] = block["owned"] - block["used"]

    # The commanders were picked partly on the checkpoint's estimate, which no
    # list has to honour. Comparing the two here is what makes a choice made on
    # a figure that did not hold visible (ADR-0005). The dangerous direction is
    # an estimate that was too generous: it admits a commander set the
    # collection cannot support, and nothing discovers that until four land
    # bases exist.
    estimate = _estimated_demand([deck.identity for deck in built])
    generous = []
    for name, block in basics.items():
        predicted = estimate.get(name, 0)
        block["estimated_used"] = predicted
        block["divergence"] = block["used"] - predicted
        if block["divergence"] > 0:
            generous.append(name)

    return {
        "decks": len(built),
        "basis": "measured from the four lists",
        "estimate": {
            "basis": _ESTIMATE_BASIS,
            "divergence": "measured minus estimated; positive means the estimate was generous",
            "generous_for": sorted(generous),
        },
        "basic_budget": {name: basics[name] for name in sorted(basics)},
        "spread": _spread(reports),
    }


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
    """The same table object, before any deck exists.

    ADR-0008 needs the tribal core and the basic headroom computable from the card
    facts and a commander alone. This is `check` with fewer inputs rather than a
    second operation: every deck-dependent field is absent, and no field appears
    here that a full run cannot also produce.

    `passed` is deliberately absent. A checkpoint reporting green would read as a
    table that had passed, which is the false green gen 1 shipped.
    """
    decks = []
    identities = []
    for entry in (resolve(facts, name, where="checkpoint") for name in names):
        identity = tuple(c for c in COLOR_ORDER if c in set(entry.card.color_identity))
        identities.append(identity)
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
        decks.append(
            {
                "commander": [entry.card.name],
                "color_identity": list(identity),
                "violations": [v.to_dict() for v in violations],
                "metrics": {
                    "pool": _pool(facts, identity),
                    "tribal_core": {
                        tribe: {
                            "ceiling": tribal_core(
                                facts, tribe, identity, excluding=entry.card.name
                            )
                        }
                        for tribe in subtypes(entry.card.type_line)
                    },
                    "categories": {
                        category.name: _with_context(
                            None, targets.of(category.name), ceiling(facts, category, identity)
                        )
                        for category in rules.metrics
                    },
                },
            }
        )
    return {
        "bracket": BRACKET,
        "snapshot": {
            "export_sha256": facts.export_sha256,
            "card_facts_refreshed": facts.refreshed,
            "rules_version": rules.version,
            "rules_hash": rules.content_hash,
            "targets_version": targets.version,
        },
        "decks": decks,
        "table": {"metrics": _headroom(facts, identities)},
        "next": "Pick a set, then compose against the card facts and run check on the four decks.",
    }


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
    """What the checkpoint predicted each basic would be asked for.

    No real deck splits its lands evenly across its colours, so this is only ever
    an estimate. It is the only thing available before lists exist, and the
    measured figure is compared against it once they do.
    """
    demand = dict.fromkeys(BASIC_FOR_COLOR, 0.0)
    for identity in identities:
        if not identity:
            continue
        share = LAND_FLOOR / len(identity)
        for colour in identity:
            demand[colour] += share
    return {BASIC_FOR_COLOR[colour]: round(amount) for colour, amount in demand.items()}


def _headroom(facts: CardFacts, identities: Sequence[Sequence[str]]) -> dict[str, Any]:
    """Basics are the only contended resource here, so say how tight the set is.

    Demand assumes an even split of a deck's lands across its colours, which no
    real deck has. It is a headroom estimate for choosing commanders; `check`
    computes the real figure from the actual lists.
    """
    owned = {
        name: (entry.owned if (entry := facts.card(name)) else 0)
        for name in BASIC_FOR_COLOR.values()
    }
    demand = _estimated_demand(identities)
    return {
        "decks": len(identities),
        "basis": f"estimated: {_ESTIMATE_BASIS}",
        "basic_budget": {
            BASIC_FOR_COLOR[colour]: {
                "owned": owned[BASIC_FOR_COLOR[colour]],
                "used": demand[BASIC_FOR_COLOR[colour]],
                "remaining": owned[BASIC_FOR_COLOR[colour]] - demand[BASIC_FOR_COLOR[colour]],
            }
            for colour in COLOR_ORDER
            if demand[BASIC_FOR_COLOR[colour]] or owned[BASIC_FOR_COLOR[colour]]
        },
    }
