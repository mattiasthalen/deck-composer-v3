"""The card-facts file and the refresh operation."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from deck_composer import manabox, scryfall
from deck_composer.errors import ToolError
from deck_composer.facts import read, refresh, render
from tests.helpers import EXPORT, GOLDEN, FakeScryfall, regenerating


def run(
    tmp_path: Path,
    export: manabox.Export,
    transport: FakeScryfall,
    *,
    all_entries: bool = False,
    path: Path | None = None,
):
    return refresh(
        export,
        path or tmp_path / "card_facts.json",
        all_entries=all_entries,
        client=scryfall.Client(transport=transport, sleep=lambda _: None),
        today=date(2026, 9, 20),
    )


# --- what refresh writes --------------------------------------------------


def test_refresh_writes_every_owned_printing(tmp_path, export, transport) -> None:
    result = run(tmp_path, export, transport)
    assert result.written
    assert len(result.facts.printing_ids) == 24
    assert result.facts.refreshed == "2026-09-20"
    assert result.facts.export_sha256 == export.sha256


def test_tokens_are_kept_apart_from_cards(tmp_path, export, transport) -> None:
    """A printing in a token set is a token whatever its layout."""
    facts = run(tmp_path, export, transport).facts
    names = {entry.token.name for entry in facts.tokens}
    assert {"Splash Lasher", "Starscape Cleric"} <= names
    card = facts.card("Splash Lasher")
    assert card is not None and "Token" not in card.card.type_line


def test_ownership_is_attached_per_card_and_per_printing(tmp_path, export, transport) -> None:
    facts = run(tmp_path, export, transport).facts
    cleric = facts.card("Starscape Cleric")
    assert cleric is not None
    assert cleric.owned == 6
    assert sum(cleric.owned_by_printing) == 6


def test_a_card_the_project_has_seen_but_does_not_own_is_zero(tmp_path, export, transport) -> None:
    facts = run(tmp_path, export, transport).facts
    assert all(entry.owned >= 0 for entry in facts.cards)


def test_edhrec_rank_is_held_at_two_significant_figures(tmp_path, export, transport) -> None:
    """So a refresh does not rewrite every line for a rank that drifted by one."""
    facts = run(tmp_path, export, transport).facts
    for entry in facts.cards:
        rank = entry.card.edhrec_rank
        if rank is not None and rank > 99:
            assert rank % (10 ** (len(str(rank)) - 2)) == 0


def test_a_face_name_resolves_to_the_whole_card(tmp_path, export, transport) -> None:
    facts = run(tmp_path, export, transport).facts
    assert facts.card("Honorbound Page") is facts.card("Honorbound Page // Forum's Favor")


# --- the guard rail: re-exporting must not re-crawl Scryfall --------------


def test_a_second_refresh_fetches_nothing(tmp_path, export, transport) -> None:
    path = tmp_path / "card_facts.json"
    run(tmp_path, export, transport, path=path)
    first = len(transport.calls)
    again = run(tmp_path, export, transport, path=path)
    assert len(transport.calls) == first, "an unchanged export must cost no requests"
    assert again.requests == 0
    assert not again.written


def test_a_new_export_recomputes_ownership_offline(tmp_path, export, transport) -> None:
    """Ownership changes on every re-export; card facts do not. They must not couple."""
    path = tmp_path / "card_facts.json"
    run(tmp_path, export, transport, path=path)
    calls = len(transport.calls)

    # The same cards, one Plains traded away.
    text = EXPORT.read_text(encoding="utf-8")
    fewer = text.replace(
        "Plains,FDN,Foundations,272,normal,common,14,",
        "Plains,FDN,Foundations,272,normal,common,13,",
    )
    assert fewer != text, "the fixture must still hold the Plains row this test edits"
    trimmed = tmp_path / "fewer.csv"
    trimmed.write_text(fewer, encoding="utf-8", newline="")
    second = manabox.read_export(trimmed, display="fewer.csv")

    result = run(tmp_path, second, transport, path=path)
    assert len(transport.calls) == calls, "a re-export must not re-crawl Scryfall"
    assert result.requests == 0
    plains = result.facts.card("Plains")
    assert plains is not None and plains.owned == 13
    assert result.facts.export_sha256 == second.sha256


def test_refresh_all_re_fetches_everything(tmp_path, export, transport) -> None:
    path = tmp_path / "card_facts.json"
    run(tmp_path, export, transport, path=path)
    calls = len(transport.calls)
    result = run(tmp_path, export, transport, all_entries=True, path=path)
    assert len(transport.calls) > calls
    assert result.requests > 0


def test_refresh_all_reports_a_legality_flip(tmp_path, export, transport) -> None:
    """A3's falsifier is a refresh flipping a flag on an owned card; it must be visible."""
    path = tmp_path / "card_facts.json"
    run(tmp_path, export, transport, path=path)
    for obj in transport.objects:
        if obj["name"] == "Vengeful Bloodwitch":
            obj["legalities"]["commander"] = "banned"
    transport.by_id = {obj["id"]: obj for obj in transport.objects}
    result = run(tmp_path, export, transport, all_entries=True, path=path)
    assert ("Vengeful Bloodwitch", "legal", "banned") in result.changes.legality


# --- the file -------------------------------------------------------------


def test_the_file_is_a_byte_exact_golden(tmp_path, export, transport) -> None:
    """The layout is locked. A deliberate change regenerates this, nothing else does."""
    rendered = render(run(tmp_path, export, transport).facts)
    golden = GOLDEN / "card_facts.json"
    if regenerating():
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(rendered, encoding="utf-8")
        pytest.skip("golden regenerated by explicit request; review the diff")
    assert golden.exists(), "run with DECK_COMPOSER_REGENERATE_GOLDEN=1 to create it"
    assert rendered == golden.read_text(encoding="utf-8")


def test_the_file_is_valid_json_with_one_entry_per_line(tmp_path, export, transport) -> None:
    rendered = render(run(tmp_path, export, transport).facts)
    payload = json.loads(rendered)
    assert payload["schema"] == 1
    entry_lines = sum(1 for line in rendered.splitlines() if '"oracle_id"' in line)
    assert entry_lines == len(payload["cards"]) + len(payload["tokens"])


def test_the_file_round_trips(tmp_path, export, transport) -> None:
    path = tmp_path / "card_facts.json"
    written = run(tmp_path, export, transport, path=path).facts
    assert read(path) == written


def test_rendering_is_deterministic(tmp_path, export, transport) -> None:
    first = render(run(tmp_path, export, FakeScryfall()).facts)
    second = render(run(tmp_path, export, FakeScryfall()).facts)
    assert first == second


def test_no_price_or_image_key_reaches_the_file(tmp_path, export, transport) -> None:
    """The projection is a whitelist; a price must never be committed."""
    rendered = render(run(tmp_path, export, transport).facts)
    for forbidden in ("price", "purchase", "image", "eur", "usd", "tix"):
        assert forbidden not in rendered.lower()


def test_an_unknown_schema_fails_loudly(tmp_path) -> None:
    path = tmp_path / "card_facts.json"
    path.write_text(json.dumps({"schema": 99, "cards": [], "tokens": []}), encoding="utf-8")
    with pytest.raises(ToolError) as caught:
        read(path)
    assert caught.value.error == "card_facts_schema_unknown"
    assert "regenerate" in caught.value.next_step.lower()


def test_a_missing_file_says_to_run_refresh(tmp_path) -> None:
    with pytest.raises(ToolError) as caught:
        read(tmp_path / "nope.json")
    assert caught.value.error == "card_facts_not_found"
    assert "refresh" in caught.value.next_step


def test_the_result_always_carries_a_next_sentence(tmp_path, export, transport) -> None:
    payload = run(tmp_path, export, transport).to_dict()
    assert payload["next"]
    assert payload["export"]["sha256"].startswith("sha256:")


def test_undecodable_card_facts_is_a_contract_failure(tmp_path) -> None:
    """A raw UnicodeDecodeError broke ADR-0006: exit 1 carries JSON, never a traceback."""
    path = tmp_path / "card_facts.json"
    path.write_bytes(b'{"schema": 1, "cards": ["\xff\xfe"]}')
    with pytest.raises(ToolError) as caught:
        read(path)
    assert caught.value.error == "card_facts_unreadable"


def test_refresh_regenerates_over_an_undecodable_file(tmp_path, export, transport) -> None:
    """Treating the old file as absent is not enough if the next line re-reads it."""
    path = tmp_path / "card_facts.json"
    path.write_bytes(b"\xff\xfe not json")
    result = run(tmp_path, export, transport, path=path)
    assert result.written
    assert read(path).export_sha256 == export.sha256


def test_an_undecodable_scryfall_response_is_a_contract_failure() -> None:
    """Not a leading BOM: json detects `\\xff\\xfe` as UTF-16 and raises the error it
    already caught. A bad byte mid-document is what reaches UnicodeDecodeError."""
    bad = b'{"data": ["\xc3\x28"]}'
    client = scryfall.Client(transport=lambda *a: (200, bad), sleep=lambda _: None)
    with pytest.raises(ToolError) as caught:
        client.collection([{"id": "x"}])
    assert caught.value.error == "scryfall_unparseable"
