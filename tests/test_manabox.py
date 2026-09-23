"""Both ManaBox formats: the export and the decklist."""

from __future__ import annotations

from pathlib import Path

import pytest

from deck_composer.errors import ToolError
from deck_composer.manabox import Deck, Entry, parse_deck, read_deck, read_export, render_deck
from tests.helpers import EXPORT, deck_text

ZORALINE = "1 Zoraline, Cosmos Caller (BLB) 242"

# --- the export -----------------------------------------------------------


def test_the_export_hashes_its_raw_bytes() -> None:
    export = read_export(EXPORT)
    assert export.sha256.startswith("sha256:")
    assert export.sha256 == read_export(EXPORT).sha256


def test_the_export_is_read_whole() -> None:
    export = read_export(EXPORT)
    assert export.rows == 35
    assert len({lot.name for lot in export.lots}) == 21
    assert sum(lot.quantity for lot in export.lots) == 131


def test_set_codes_are_lowercased_to_match_scryfall() -> None:
    """The export writes SOS and TBLB; Scryfall answers sos and tblb."""
    export = read_export(EXPORT)
    assert all(lot.set_code == lot.set_code.lower() for lot in export.lots)
    assert {"blb", "fdn", "tblb"} <= {lot.set_code for lot in export.lots}


def test_ownership_joins_through_printings() -> None:
    """Never by name: Starscape Cleric is a card and a token of the same name."""
    owned = read_export(EXPORT).owned_by_printing()
    assert owned["53a938a7-0154-4350-87cb-00da24ec3824"] == 6  # the BLB card
    assert owned["5379a77e-4b98-4abc-b967-fbc76bb85fc6"] == 2  # the TBLB token


def test_a_missing_export_says_what_to_do(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as caught:
        read_export(tmp_path / "nope.csv")
    assert caught.value.error == "export_not_found"
    assert caught.value.next_step


def test_a_header_without_the_required_columns_fails(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("Name,Quantity\r\nPlains,1\r\n", encoding="utf-8")
    with pytest.raises(ToolError) as caught:
        read_export(path)
    assert caught.value.error == "missing_columns"


def test_every_bad_row_is_reported_before_failing(tmp_path: Path) -> None:
    header = EXPORT.read_text(encoding="utf-8").splitlines()[0]
    body = EXPORT.read_text(encoding="utf-8").splitlines()[1:3]
    broken = [row.replace(",1,", ",0,", 1) for row in body]
    path = tmp_path / "bad.csv"
    path.write_text("\r\n".join([header, *broken]) + "\r\n", encoding="utf-8")
    with pytest.raises(ToolError) as caught:
        read_export(path)
    assert caught.value.error == "invalid_rows"
    assert caught.value.detail["total"] >= 1


# --- the decklist ---------------------------------------------------------


def test_a_basic_land_line_has_no_set_suffix() -> None:
    """`15 Plains` is bare. A parser requiring the suffix drops every basic."""
    deck = parse_deck(deck_text("d", [ZORALINE], ["15 Plains"]), path="d")
    plains = deck.mainboard[0]
    assert plains == Entry(quantity=15, name="Plains")
    assert plains.pinned is False


def test_a_pinned_printing_carries_set_and_collector_number() -> None:
    deck = parse_deck(deck_text("d", [ZORALINE], []), path="d")
    entry = deck.commander[0]
    assert entry.name == "Zoraline, Cosmos Caller"
    assert (entry.set_code, entry.collector_number) == ("blb", "242")


def test_a_name_containing_a_double_slash_survives() -> None:
    deck = parse_deck(deck_text("d", [], ["1 Honorbound Page // Forum's Favor (SOS) 19"]), path="d")
    assert deck.mainboard[0].name == "Honorbound Page // Forum's Favor"


def test_the_maybeboard_is_parsed_but_kept_apart() -> None:
    text = deck_text("d", ["1 Zoraline, Cosmos Caller (BLB) 242"], ["1 Plains"], ["1 Sol Ring"])
    deck = parse_deck(text, path="d")
    assert len(deck.maybeboard) == 1
    assert deck.counted == deck.commander + deck.mainboard
    assert deck.size == 2


def test_a_deck_without_a_schema_comment_is_malformed() -> None:
    with pytest.raises(ToolError) as caught:
        parse_deck(deck_text("d", [], ["1 Plains"], schema=None), path="d")
    assert caught.value.error == "deck_malformed"
    assert any(p["problem"] == "schema_missing" for p in caught.value.detail["problems"])


def test_an_unknown_schema_fails_loudly() -> None:
    with pytest.raises(ToolError) as caught:
        parse_deck(deck_text("d", [], ["1 Plains"], schema=99), path="d")
    assert caught.value.error == "deck_schema_unknown"
    assert caught.value.detail["schema"] == 99


def test_an_unparseable_line_is_a_contract_failure() -> None:
    with pytest.raises(ToolError) as caught:
        parse_deck("// schema: 1\n// Mainboard\nPlains\n", path="d")
    assert caught.value.error == "deck_malformed"


def test_free_comments_are_ignored_and_the_name_is_the_file() -> None:
    """ADR-0012 admits only `schema` into a comment, so the name is the filename."""
    text = "// schema: 1\n// my table deck\n// Mainboard\n1 Plains\n// a trailing note\n"
    deck = parse_deck(text, path="wick-rats.deck.txt")
    assert deck.name == "wick-rats"
    assert len(deck.mainboard) == 1


def test_a_deck_named_like_a_section_is_not_swallowed() -> None:
    """A name in a comment could be read as a section header; the filename cannot."""
    deck = Deck(
        path="Commander.deck.txt",
        name="Commander",
        commander=(Entry(1, "Zoraline, Cosmos Caller", "blb", "242"),),
        mainboard=(Entry(15, "Plains"),),
        maybeboard=(),
    )
    assert parse_deck(render_deck(deck), path="Commander.deck.txt") == deck


def test_a_decklist_round_trips() -> None:
    deck = Deck(
        path="round-trip.deck.txt",
        name="round-trip",
        commander=(Entry(1, "Zoraline, Cosmos Caller", "blb", "242"),),
        mainboard=(Entry(15, "Plains"), Entry(1, "Uncharted Haven", "fdn", "564")),
        maybeboard=(Entry(1, "Sol Ring"),),
    )
    rendered = render_deck(deck)
    assert "1 Zoraline, Cosmos Caller (BLB) 242" in rendered
    assert "15 Plains" in rendered
    assert parse_deck(rendered, path="round-trip.deck.txt") == deck


def test_a_missing_deck_file_says_what_to_do(tmp_path: Path) -> None:
    with pytest.raises(ToolError) as caught:
        read_deck(tmp_path / "nope.txt")
    assert caught.value.error == "deck_not_found"


def test_anything_after_a_pinned_suffix_is_unparseable() -> None:
    """It was swallowed into the name and resurfaced as an unknown card, no line.

    A foil marker such as `*F*` is not part of the recorded format (A5); if a
    real ManaBox export carries one, this fails loudly at the line and A5 needs
    amending, which is the order it should happen in.
    """
    with pytest.raises(ToolError) as caught:
        parse_deck("// schema: 1\n// Mainboard\n1 Sol Ring (LTR) 123 *F*\n", path="d")
    problem = caught.value.detail["problems"][0]
    assert problem["problem"] == "unparseable_entry"
    assert problem["line"] == 3


def test_a_name_carrying_parentheses_still_parses() -> None:
    """The strictness is about a trailing suffix, not about parentheses in names."""
    deck = parse_deck("// schema: 1\n// Mainboard\n1 Erase (Not the Urza's Legacy One)\n", path="d")
    assert deck.mainboard[0] == Entry(1, "Erase (Not the Urza's Legacy One)")
