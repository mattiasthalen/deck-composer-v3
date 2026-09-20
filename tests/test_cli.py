"""The two verbs: argument parsing, JSON rendering, exit codes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deck_composer import cli
from deck_composer.facts import render
from tests.helpers import EXPORT, deck_text, write_deck

ZORALINE = "1 Zoraline, Cosmos Caller (BLB) 242"


@pytest.fixture
def facts_file(tmp_path: Path, card_facts) -> Path:
    path = tmp_path / "card_facts.json"
    path.write_text(render(card_facts), encoding="utf-8")
    return path


def run(argv: list[str], capsys) -> tuple[int, dict, dict]:
    code = cli.main(argv)
    captured = capsys.readouterr()
    out = json.loads(captured.out) if captured.out.strip() else {}
    err = json.loads(captured.err) if captured.err.strip() else {}
    return code, out, err


# --- check ----------------------------------------------------------------


def test_check_exits_zero_with_violations_in_the_output(tmp_path, facts_file, capsys) -> None:
    """ADR-0006: a deck with violations is a successful run."""
    deck = write_deck(tmp_path, "d", deck_text("d", [ZORALINE], ["4 Uncharted Haven"]))
    code, out, _ = run(["check", str(deck), "--facts", str(facts_file)], capsys)
    assert code == 0
    assert out["passed"] is False
    assert any(v["violation"] == "singleton" for v in out["decks"][0]["violations"])
    assert out["next"]


def test_check_exits_one_for_a_contract_failure(tmp_path, facts_file, capsys) -> None:
    deck = write_deck(tmp_path, "d", deck_text("d", [ZORALINE], ["1 Black Lotus"]))
    code, out, err = run(["check", str(deck), "--facts", str(facts_file)], capsys)
    assert code == 1
    assert out == {}
    assert err["error"] == "unknown_card"
    assert err["next"]


def test_check_takes_the_whole_table_in_one_call(tmp_path, facts_file, capsys) -> None:
    decks = []
    for n in range(2):
        text = deck_text(f"d{n}", [ZORALINE], ["1 Vengeful Bloodwitch"])
        decks.append(str(write_deck(tmp_path, f"d{n}", text)))
    code, out, _ = run(["check", *decks, "--facts", str(facts_file)], capsys)
    assert code == 0
    assert len(out["decks"]) == 2
    assert any(v["violation"] == "ownership" for v in out["table"]["violations"])


def test_check_reports_the_snapshot_it_ran_against(tmp_path, facts_file, capsys) -> None:
    deck = write_deck(tmp_path, "d", deck_text("d", [ZORALINE], ["1 Plains"]))
    _, out, _ = run(["check", str(deck), "--facts", str(facts_file)], capsys)
    assert out["snapshot"]["export_sha256"].startswith("sha256:")
    assert out["snapshot"]["card_facts_refreshed"] == "2026-09-20"
    assert out["bracket"] == 2


def test_check_with_commanders_returns_the_checkpoint(tmp_path, facts_file, capsys) -> None:
    code, out, _ = run(
        ["check", "--commander", "Zoraline, Cosmos Caller", "--facts", str(facts_file)], capsys
    )
    assert code == 0
    assert out["commanders"][0]["commander"] == "Zoraline, Cosmos Caller"
    assert "basic_headroom" in out


def test_check_refuses_both_decks_and_commanders(tmp_path, facts_file, capsys) -> None:
    deck = write_deck(tmp_path, "d", deck_text("d", [ZORALINE], ["1 Plains"]))
    with pytest.raises(SystemExit) as caught:
        cli.main(["check", str(deck), "--commander", "Zoraline, Cosmos Caller"])
    assert caught.value.code == 2


def test_check_refuses_neither_decks_nor_commanders(capsys) -> None:
    with pytest.raises(SystemExit) as caught:
        cli.main(["check"])
    assert caught.value.code == 2


# --- refresh --------------------------------------------------------------


def test_refresh_writes_the_card_facts(tmp_path, monkeypatch, capsys) -> None:
    from tests.helpers import FakeScryfall

    monkeypatch.setattr("deck_composer.scryfall.urllib_transport", FakeScryfall(), raising=True)
    monkeypatch.setattr("time.sleep", lambda _: None)
    out_path = tmp_path / "card_facts.json"
    code, out, _ = run(["refresh", str(EXPORT), "--out", str(out_path)], capsys)
    assert code == 0
    assert out_path.exists()
    assert out["cards"] > 0
    assert out["export"]["rows"] == 35
    assert out["next"]


def test_refresh_reports_a_missing_export(tmp_path, capsys) -> None:
    code, _out, err = run(["refresh", str(tmp_path / "nope.csv")], capsys)
    assert code == 1
    assert err["error"] == "export_not_found"


# --- the shape of the surface --------------------------------------------


def test_there_are_exactly_two_verbs() -> None:
    """ADR-0001: a new fact is a field in check's output, never a new verb."""
    import argparse

    parser = cli.build_parser()
    verbs: set[str] = set()
    for action in parser._get_positional_actions():
        if isinstance(action, argparse._SubParsersAction):
            verbs |= set(action.choices)
    assert verbs == {"refresh", "check"}, (
        "adding a verb supersedes ADR-0001; a new fact belongs in check's output"
    )


def test_the_default_suite_never_reaches_the_network(monkeypatch, tmp_path, capsys) -> None:
    """A test believed to be offline once opened a real connection to Scryfall."""
    import socket

    from tests.helpers import FakeScryfall

    def refuse(*args, **kwargs):
        raise AssertionError("the default suite must not open a socket")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr("deck_composer.scryfall.urllib_transport", FakeScryfall(), raising=True)
    monkeypatch.setattr("time.sleep", lambda _: None)
    code, _out, _err = run(["refresh", str(EXPORT), "--out", str(tmp_path / "f.json")], capsys)
    assert code == 0
