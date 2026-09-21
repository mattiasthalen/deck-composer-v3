"""Rules and measurements. The first test is the bug gen 1 shipped."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from deck_composer import check as check_module
from deck_composer.check import LAND_FLOOR, checkpoint
from deck_composer.errors import ToolError
from deck_composer.facts import CardFacts
from deck_composer.manabox import parse_deck
from deck_composer.rules import read_rules, read_targets
from tests.helpers import deck_text

ZORALINE = "1 Zoraline, Cosmos Caller (BLB) 242"
ZORALINE_NAME = "Zoraline, Cosmos Caller"
WICK = "Wick, the Whorled Mind"


def table(*texts: str) -> list:
    return [parse_deck(text, path=f"deck{n}.txt") for n, text in enumerate(texts)]


def codes(report, deck: int = 0) -> list[str]:
    return [v.code for v in report.decks[deck].violations]


def one(text: str, facts: CardFacts, rules=None, targets=None):
    return check_module.check(table(text), facts, rules or RULES, targets or TARGETS)


RULES = read_rules(Path("data/categories.json"))
TARGETS = read_targets(Path("data/targets.json"))


# --- the regression -------------------------------------------------------


def test_four_copies_of_a_nonbasic_land_is_a_singleton_violation(card_facts: CardFacts) -> None:
    """Gen 1 shipped `4 Uncharted Haven` against a green singleton check.

    Its duplicate predicate inspected nonland cards only. This is the exact
    false green that ADR-0002 exists to prevent, so it is the first test.
    """
    report = one(deck_text("regression", [ZORALINE], ["4 Uncharted Haven"]), card_facts)
    singleton = [v for v in report.decks[0].violations if v.code == "singleton"]
    assert singleton, "four copies of a nonbasic land must violate singleton"
    assert singleton[0].detail == {"card": "Uncharted Haven", "quantity": 4}
    assert not report.passed


def test_basic_lands_are_exempt_from_singleton(card_facts: CardFacts) -> None:
    report = one(deck_text("basics", [ZORALINE], ["15 Plains", "15 Swamp"]), card_facts)
    assert "singleton" not in codes(report)


def test_a_single_nonbasic_land_is_fine(card_facts: CardFacts) -> None:
    report = one(deck_text("one", [ZORALINE], ["1 Uncharted Haven"]), card_facts)
    assert "singleton" not in codes(report)


def test_a_duplicated_nonland_is_a_singleton_violation(card_facts: CardFacts) -> None:
    report = one(deck_text("spell", [ZORALINE], ["2 Feed the Cycle"]), card_facts)
    assert "singleton" in codes(report)


# --- the other hard rules -------------------------------------------------


def test_a_banned_card_is_not_legal(card_facts: CardFacts) -> None:
    report = one(deck_text("banned", [ZORALINE], ["1 Prophet of Kruphix"]), card_facts)
    found = [v for v in report.decks[0].violations if v.code == "not_legal"]
    assert found and found[0].detail["card"] == "Prophet of Kruphix"


def test_a_card_outside_the_commanders_identity_violates(card_facts: CardFacts) -> None:
    """Zoraline is Orzhov; Bakersbane Duo is green."""
    report = one(deck_text("identity", [ZORALINE], ["1 Bakersbane Duo"]), card_facts)
    found = [v for v in report.decks[0].violations if v.code == "color_identity"]
    assert found and found[0].detail["outside"] == ["G"]


def test_a_card_inside_the_identity_does_not_violate(card_facts: CardFacts) -> None:
    report = one(deck_text("identity", [ZORALINE], ["1 Vengeful Bloodwitch"]), card_facts)
    assert "color_identity" not in codes(report)


def test_a_game_changer_violates_at_bracket_two(card_facts: CardFacts) -> None:
    report = one(deck_text("gc", [ZORALINE], ["1 Vampiric Tutor"]), card_facts)
    assert "game_changer" in codes(report)


def test_a_deck_that_is_not_a_hundred_cards_violates(card_facts: CardFacts) -> None:
    report = one(deck_text("short", [ZORALINE], ["1 Feed the Cycle"]), card_facts)
    found = [v for v in report.decks[0].violations if v.code == "deck_size"]
    assert found and found[0].detail == {"size": 2, "expected": 100}


def test_a_deck_below_the_land_floor_violates(card_facts: CardFacts) -> None:
    report = one(deck_text("lands", [ZORALINE], ["10 Plains"]), card_facts)
    found = [v for v in report.decks[0].violations if v.code == "land_floor"]
    assert found and found[0].detail == {"lands": 10, "floor": LAND_FLOOR}


def test_a_deck_at_the_land_floor_does_not_violate(card_facts: CardFacts) -> None:
    report = one(deck_text("lands", [ZORALINE], ["18 Plains", "17 Swamp"]), card_facts)
    assert "land_floor" not in codes(report)


def test_a_commander_that_is_not_a_legendary_creature_violates(card_facts: CardFacts) -> None:
    report = one(deck_text("bad", ["1 Feed the Cycle"], ["1 Plains"]), card_facts)
    assert "commander_ineligible" in codes(report)


# --- the maybeboard -------------------------------------------------------


def test_the_maybeboard_never_counts(card_facts: CardFacts) -> None:
    """It holds unowned cards, so it counts towards nothing."""
    text = deck_text(
        "maybe",
        [ZORALINE],
        ["18 Plains", "17 Swamp"],
        maybeboard=["1 Sol Ring", "4 Uncharted Haven"],
    )
    report = one(text, card_facts)
    assert report.decks[0].metrics["size"] == 36
    assert report.decks[0].metrics["maybeboard"] == 5
    assert "singleton" not in codes(report)


def test_an_unowned_maybeboard_name_is_not_resolved(card_facts: CardFacts) -> None:
    """Sol Ring is not in the card facts; the maybeboard must not make that a failure."""
    text = deck_text("maybe", [ZORALINE], ["1 Plains"], maybeboard=["1 Sol Ring"])
    report = one(text, card_facts)
    assert report.decks[0].metrics["maybeboard"] == 1


# --- ownership, which is a table property ---------------------------------


def test_ownership_is_summed_across_the_whole_table(card_facts: CardFacts) -> None:
    """Six Moonrise Clerics are owned five; four decks each taking one is fine."""
    decks = [deck_text(f"d{n}", [ZORALINE], ["1 Moonrise Cleric"]) for n in range(4)]
    report = check_module.check(table(*decks), card_facts, RULES, TARGETS)
    assert not [v for v in report.violations if v.code == "ownership"]


def test_the_table_overdrawing_a_card_violates(card_facts: CardFacts) -> None:
    """Vengeful Bloodwitch is owned once; two decks cannot both play it."""
    decks = [deck_text(f"d{n}", [ZORALINE], ["1 Vengeful Bloodwitch"]) for n in range(2)]
    report = check_module.check(table(*decks), card_facts, RULES, TARGETS)
    found = [v for v in report.violations if v.code == "ownership"]
    assert found and found[0].detail == {
        "card": "Vengeful Bloodwitch",
        "used": 2,
        "owned": 1,
    }


def test_basics_are_owned_like_any_other_card(card_facts: CardFacts) -> None:
    """ADR-0005: no exemption. The export holds 14 Plains."""
    decks = [deck_text(f"d{n}", [ZORALINE], ["10 Plains"]) for n in range(2)]
    report = check_module.check(table(*decks), card_facts, RULES, TARGETS)
    found = [v for v in report.violations if v.code == "ownership"]
    assert found and found[0].detail == {"card": "Plains", "used": 20, "owned": 14}


def test_a_token_printing_does_not_inflate_the_cards_ownership(card_facts: CardFacts) -> None:
    """Starscape Cleric is 6 as a card and 2 more as a TBLB token.

    Summing owned quantity by name would say 8. Ownership joins through
    printings, so the card is 6 and the token is counted apart.
    """
    entry = card_facts.card("Starscape Cleric")
    assert entry is not None and entry.owned == 6
    token = next(t for t in card_facts.tokens if t.token.name == "Starscape Cleric")
    assert token.owned == 2


# --- the basic budget, a table-level fact ---------------------------------


def test_the_basic_budget_is_reported_at_the_table(card_facts: CardFacts) -> None:
    decks = [deck_text(f"d{n}", [ZORALINE], ["5 Plains"]) for n in range(2)]
    report = check_module.check(table(*decks), card_facts, RULES, TARGETS)
    budget = report.metrics["basic_budget"]["Plains"]
    assert budget["owned"] == 14
    assert budget["used"] == 10
    assert budget["remaining"] == 4


# --- metrics --------------------------------------------------------------


def test_the_tribal_core_is_two_numbers_never_one(card_facts: CardFacts) -> None:
    """Zoraline is a Bat Cleric, so both subtypes are measured and neither is chosen."""
    text = deck_text("bats", [ZORALINE], ["1 Starscape Cleric", "1 Moonrise Cleric"])
    core = one(text, card_facts).decks[0].metrics["tribal_core"]
    assert set(core) == {"Bat", "Cleric"}
    for numbers in core.values():
        assert set(numbers) == {"type_line", "text_mention", "total", "ceiling"}
        assert numbers["total"] == numbers["type_line"] + numbers["text_mention"]
        # The pool ceiling is the same two numbers, so a deck can be read
        # against what its colours could actually field.
        assert numbers["ceiling"]["total"] >= numbers["total"]


def test_metrics_measure_the_deck(card_facts: CardFacts) -> None:
    text = deck_text("m", [ZORALINE], ["18 Plains", "17 Swamp", "1 Feed the Cycle"])
    metrics = one(text, card_facts).decks[0].metrics
    assert metrics["lands"] == 35
    assert metrics["basics"] == {"Plains": 18, "Swamp": 17}
    assert metrics["nonbasic_lands"] == 0
    assert metrics["color_sources"] == {"W": 18, "B": 17}
    assert metrics["size"] == 37  # commander plus 36


def test_the_spread_is_reported_without_a_verdict(card_facts: CardFacts) -> None:
    """The band that would judge this spread is not yet decided, so none is emitted."""
    decks = [deck_text("a", [ZORALINE], ["20 Plains"]), deck_text("b", [ZORALINE], ["10 Plains"])]
    spread = check_module.check(table(*decks), card_facts, RULES, TARGETS).metrics["spread"]
    assert spread["lands"] == {"values": [20, 10], "min": 10, "max": 20, "spread": 10}
    assert "verdict" not in spread and "band" not in spread


def test_unsettled_fields_are_absent_not_null(card_facts: CardFacts) -> None:
    """A null invites a zero; an absent field cannot be cited by a playbook."""
    report = one(deck_text("m", [ZORALINE], ["1 Plains"]), card_facts).to_dict()
    metrics = report["decks"][0]["metrics"]
    for unsettled in ("removal", "draw", "ramp", "mass_land_denial", "extra_turns"):
        assert unsettled not in metrics
    assert "balance" not in report["table"]


# --- contract failures ----------------------------------------------------


def test_a_name_the_card_facts_lack_is_a_contract_failure(card_facts: CardFacts) -> None:
    with pytest.raises(ToolError) as caught:
        one(deck_text("x", [ZORALINE], ["1 Black Lotus"]), card_facts)
    assert caught.value.error == "unknown_card"
    assert caught.value.detail["card"] == "Black Lotus"


def test_a_face_name_resolves_to_its_card(card_facts: CardFacts) -> None:
    report = one(deck_text("face", [ZORALINE], ["1 Honorbound Page"]), card_facts)
    assert report.decks[0].metrics["size"] == 2


# --- the checkpoint -------------------------------------------------------


def test_the_checkpoint_computes_before_any_deck_exists(card_facts: CardFacts) -> None:
    """ADR-0008: tribal core and basic headroom from the card facts and a commander."""
    view = checkpoint(
        card_facts, ["Zoraline, Cosmos Caller", "Wick, the Whorled Mind"], RULES, TARGETS
    )
    zoraline = view["decks"][0]
    assert zoraline["color_identity"] == ["W", "B"]
    assert zoraline["violations"] == []
    assert set(zoraline["metrics"]["tribal_core"]) == {"Bat", "Cleric"}
    assert zoraline["metrics"]["pool"]["legal_nonland_names"] > 0
    assert view["table"]["metrics"]["basic_budget"]["Plains"]["owned"] == 14


def test_the_checkpoint_reports_the_snapshot(card_facts: CardFacts) -> None:
    view = checkpoint(card_facts, ["Zoraline, Cosmos Caller"], RULES, TARGETS)
    assert view["snapshot"]["export_sha256"].startswith("sha256:")
    assert view["snapshot"]["card_facts_refreshed"] == "2026-09-20"


# --- the commander does not count toward its own tribal core --------------


def test_a_commander_is_excluded_from_its_own_tribal_core(card_facts: CardFacts) -> None:
    """The number answers how tribal the 99 can be, and the commander is not one.

    Zoraline is a Bat. Counting her would add a constant 1 to every candidate,
    which carries no comparative information at the selection checkpoint.
    """
    identity = ("W", "B")
    with_her = check_module.tribal_core(card_facts, "Bat", identity)
    without = check_module.tribal_core(
        card_facts, "Bat", identity, excluding="Zoraline, Cosmos Caller"
    )
    assert without["type_line"] == with_her["type_line"] - 1


def test_the_checkpoint_excludes_each_commander_from_its_own_core(
    card_facts: CardFacts,
) -> None:
    view = checkpoint(card_facts, ["Zoraline, Cosmos Caller"], RULES, TARGETS)
    bats = view["decks"][0]["metrics"]["tribal_core"]["Bat"]["ceiling"]
    plain = check_module.tribal_core(card_facts, "Bat", ("W", "B"))
    assert bats["type_line"] == plain["type_line"] - 1


def test_a_commander_in_the_deck_is_excluded_from_the_deck_core(
    card_facts: CardFacts,
) -> None:
    text = deck_text("bats", [ZORALINE], ["1 Starscape Cleric"])
    core = one(text, card_facts).decks[0].metrics["tribal_core"]["Bat"]
    assert core["type_line"] == 1  # Starscape Cleric only, never Zoraline


# --- bracket 2 violation categories ---------------------------------------


def test_an_extra_turn_card_violates_at_bracket_two(card_facts: CardFacts) -> None:
    """Detected by pattern over oracle data, never by a label the composer applied."""
    from deck_composer.rules import read_rules

    payload = json.loads(Path("data/categories.json").read_text(encoding="utf-8"))
    payload["categories"]["extra_turns"]["include"] = ["Feed the Cycle"]
    path = Path(tempfile.mkdtemp()) / "categories.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    report = one(deck_text("x", [ZORALINE], ["1 Feed the Cycle"]), card_facts, read_rules(path))
    assert "extra_turns" in codes(report)


def test_a_clean_deck_trips_no_category_violation(card_facts: CardFacts) -> None:
    report = one(deck_text("x", [ZORALINE], ["18 Plains", "17 Swamp"]), card_facts)
    assert "extra_turns" not in codes(report)
    assert "mass_land_denial" not in codes(report)


# --- ceilings beside targets ----------------------------------------------


def test_a_metric_reports_its_target_and_its_ceiling(card_facts: CardFacts) -> None:
    """`ramp 2 (target 10, ceiling 2)` tells a build failure from a collection fact."""
    report = one(deck_text("x", [ZORALINE], ["18 Plains", "17 Swamp"]), card_facts)
    ramp = report.decks[0].metrics["categories"]["ramp"]
    assert set(ramp) == {"count", "target", "ceiling"}
    assert ramp["target"] == 10
    assert ramp["ceiling"] >= ramp["count"]


def test_a_target_the_collection_cannot_meet_is_still_reported(
    card_facts: CardFacts,
) -> None:
    """Sweepers stays at 2 against a pool holding fewer. The ceiling says why."""
    report = one(deck_text("x", [ZORALINE], ["1 Plains"]), card_facts)
    sweepers = report.decks[0].metrics["categories"]["sweepers"]
    assert sweepers["target"] == 2
    assert "ceiling" in sweepers


def test_the_ceiling_comes_from_colour_identity_alone(card_facts: CardFacts) -> None:
    """A ceiling that moved with build order could not be reasoned about."""
    alone = one(deck_text("a", [ZORALINE], ["1 Plains"]), card_facts)
    decks = [deck_text(f"d{n}", [ZORALINE], ["1 Vengeful Bloodwitch"]) for n in range(3)]
    crowded = check_module.check(table(*decks), card_facts, RULES, TARGETS)
    assert (
        alone.decks[0].metrics["categories"]["draw"]["ceiling"]
        == crowded.decks[0].metrics["categories"]["draw"]["ceiling"]
    )


# --- balance is a spread with no threshold --------------------------------


def test_the_spread_covers_four_axes_and_judges_none(card_facts: CardFacts) -> None:
    decks = [deck_text("a", [ZORALINE], ["20 Plains"]), deck_text("b", [ZORALINE], ["10 Plains"])]
    spread = check_module.check(table(*decks), card_facts, RULES, TARGETS).metrics["spread"]
    assert set(spread) == {
        "note",
        "lands",
        "average_mana_value",
        "creatures",
        "targeted_interaction",
    }
    for axis in ("lands", "average_mana_value", "creatures", "targeted_interaction"):
        assert set(spread[axis]) == {"values", "min", "max", "spread"}
        assert "verdict" not in spread[axis] and "passed" not in spread[axis]


def test_the_report_names_the_rules_it_ran_under(card_facts: CardFacts) -> None:
    report = one(deck_text("x", [ZORALINE], ["1 Plains"]), card_facts).to_dict()
    assert report["snapshot"]["rules_version"]
    assert report["snapshot"]["rules_hash"].startswith("sha256:")
    assert report["snapshot"]["targets_version"]


# --- the estimate the commanders were picked on --------------------------


def test_the_measured_budget_is_compared_against_the_estimate(
    card_facts: CardFacts,
) -> None:
    """The commanders were chosen partly on the checkpoint's estimate (ADR-0005).

    Two Orzhov decks estimate an even 35-land split, so roughly 35 Plains. Both
    lists here take 5, so the estimate asked for far more than the build used.
    """
    decks = [deck_text(f"d{n}", [ZORALINE], ["5 Plains"]) for n in range(2)]
    metrics = check_module.check(table(*decks), card_facts, RULES, TARGETS).metrics
    plains = metrics["basic_budget"]["Plains"]
    assert plains["used"] == 10
    assert plains["estimated_used"] == 35
    assert plains["divergence"] == -25  # conservative: the safe direction


def test_an_estimate_that_was_too_generous_is_named(card_facts: CardFacts) -> None:
    """The dangerous direction: the build wants more than the checkpoint predicted.

    It admits a commander set the collection cannot support, and nothing finds
    that out until four land bases exist.
    """
    decks = [deck_text(f"d{n}", [ZORALINE], ["30 Plains"]) for n in range(2)]
    metrics = check_module.check(table(*decks), card_facts, RULES, TARGETS).metrics
    assert metrics["basic_budget"]["Plains"]["divergence"] == 25
    assert "Plains" in metrics["estimate"]["generous_for"]
    assert "generous" in metrics["estimate"]["divergence"]


def test_an_unbuilt_seat_is_still_charged_to_the_budget(card_facts: CardFacts) -> None:
    """Otherwise the first deck built looks far cheaper than it is.

    Zoraline's list takes 5 Plains. Wick is unbuilt, and being three-colour his
    seat is estimated to want roughly a third of a 35-land floor in each of his
    colours. The remaining budget must already carry that.
    """
    deck = deck_text("d", [ZORALINE], ["5 Plains"])
    report = check_module.check(table(deck), card_facts, RULES, TARGETS, pending=[WICK])
    swamp = report.metrics["basic_budget"]["Swamp"]
    assert swamp["unbuilt_estimate"] == 12  # a third of 35, rounded
    assert swamp["remaining"] == swamp["owned"] - swamp["used"] - 12
    assert report.metrics["seats_unbuilt"] == 1


def test_the_estimate_a_seat_carries_is_the_one_it_is_later_judged_against(
    card_facts: CardFacts,
) -> None:
    """A comparison to an estimate means nothing unless it is the same estimate.

    What the checkpoint charges an unbuilt seat must equal what a later run
    treats as that seat's baseline, or the divergence silently measures against
    a figure nobody ever saw.
    """
    at_checkpoint = checkpoint(card_facts, [ZORALINE_NAME], RULES, TARGETS)
    charged = at_checkpoint["table"]["metrics"]["basic_budget"]["Plains"]["unbuilt_estimate"]

    once_built = check_module.check(
        table(deck_text("d", [ZORALINE], ["1 Plains"])), card_facts, RULES, TARGETS
    ).metrics
    assert charged == once_built["basic_budget"]["Plains"]["estimated_used"]


def test_a_checkpoint_carries_no_divergence(card_facts: CardFacts) -> None:
    """Nothing is measured yet, so there is nothing to compare; absent, not zero."""
    view = checkpoint(card_facts, [ZORALINE_NAME], RULES, TARGETS)
    plains = view["table"]["metrics"]["basic_budget"]["Plains"]
    assert "unbuilt_estimate" in plains
    assert "divergence" not in plains and "estimated_used" not in plains
    assert "estimate" not in view["table"]["metrics"]


def test_a_projected_overrun_is_named_not_blocked(card_facts: CardFacts) -> None:
    """Part of the projection is an estimate, and this project does not block on one.

    Measured overuse is already an ownership violation. This names the basics a
    part-built table is on course to run out of, which is the whole payoff of
    building the scarcest basic first: seen at deck one, not deck four.
    """
    deck = deck_text("d", [ZORALINE], ["12 Swamp"])
    report = check_module.check(table(deck), card_facts, RULES, TARGETS, pending=[WICK, WICK])
    metrics = report.metrics
    assert metrics["basic_budget"]["Swamp"]["remaining"] < 0
    assert "Swamp" in metrics["overcommitted"]
    assert not [v for v in report.violations if v.code == "ownership"]


def test_a_table_within_budget_names_nothing(card_facts: CardFacts) -> None:
    deck = deck_text("d", [ZORALINE], ["1 Swamp"])
    metrics = check_module.check(table(deck), card_facts, RULES, TARGETS).metrics
    assert metrics["overcommitted"] == []
