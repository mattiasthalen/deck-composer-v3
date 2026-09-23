"""The two verbs: argument parsing, JSON rendering, exit codes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deck_composer import cli
from deck_composer.facts import render
from tests.helpers import EXPORT, SEAT_LINES, deck_text, write_deck

ZORALINE = "1 Zoraline, Cosmos Caller (BLB) 242"


@pytest.fixture
def facts_file(tmp_path: Path, card_facts) -> Path:
    path = tmp_path / "card_facts.json"
    path.write_text(render(card_facts), encoding="utf-8")
    return path


def four_decks(tmp_path: Path, mainboard: list[str]) -> list[str]:
    """A whole table: the lexicon's table is four decks, and only four is certified."""
    return [
        str(write_deck(tmp_path, f"d{n}", deck_text(f"d{n}", [SEAT_LINES[n]], mainboard)))
        for n in range(4)
    ]


def run(argv: list[str], capsys) -> tuple[int, dict, dict]:
    code = cli.main(argv)
    captured = capsys.readouterr()
    out = json.loads(captured.out) if captured.out.strip() else {}
    err = json.loads(captured.err) if captured.err.strip() else {}
    return code, out, err


# --- check ----------------------------------------------------------------


def test_check_exits_zero_with_violations_in_the_output(tmp_path, facts_file, capsys) -> None:
    """ADR-0006: a deck with violations is a successful run."""
    decks = four_decks(tmp_path, ["4 Uncharted Haven"])
    code, out, _ = run(["check", *decks, "--facts", str(facts_file)], capsys)
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
        text = deck_text(f"d{n}", [SEAT_LINES[n]], ["1 Vengeful Bloodwitch"])
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
    assert out["decks"][0]["commander"] == ["Zoraline, Cosmos Caller"]
    assert "basic_budget" in out["table"]["metrics"]


def test_decks_and_commanders_compose_into_one_table(tmp_path, facts_file, capsys) -> None:
    """ADR-0005 builds the scarcest basic first, so a table is part-built for a while.

    Deck files are the seats that exist; --commander names the ones that do not
    yet. Both are the same table, and the budget has to span all four or the
    first deck looks far cheaper than it is.
    """
    deck = write_deck(tmp_path, "d", deck_text("d", [ZORALINE], ["15 Plains"]))
    code, out, _ = run(
        [
            "check",
            str(deck),
            "--commander",
            "Wick, the Whorled Mind",
            "--facts",
            str(facts_file),
        ],
        capsys,
    )
    assert code == 0
    assert len(out["decks"]) == 2
    built, seat = out["decks"]
    assert "size" in built["metrics"] and "size" not in seat["metrics"]
    metrics = out["table"]["metrics"]
    assert metrics["decks"] == 1 and metrics["seats_unbuilt"] == 1
    assert "measured" in metrics["basis"] and "estimated" in metrics["basis"]
    assert "passed" not in out, "a table with an unbuilt seat must not report green"


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


def _paths(obj, prefix: str = "") -> set[str]:
    """Every field path in a response, ignoring leaf names that vary by card."""
    varies = (".basics.", ".color_sources.", ".basic_budget.", "tribal_core.", "curve.")
    found: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = prefix + key
            if not any(segment in path for segment in varies):
                found.add(path)
            found |= _paths(value, path + ".")
    elif isinstance(obj, list) and obj:
        found |= _paths(obj[0], prefix)
    return {p for p in found if not any(segment in p for segment in varies)}


def test_the_checkpoint_is_the_same_object_with_fields_absent(tmp_path, facts_file, capsys) -> None:
    """ADR-0001 is guarded by the output's shape, not by counting verbs.

    `check --commander` is the same verb only while it returns the same
    table-shaped object with the deck-dependent fields absent. The failure mode
    is a flag that quietly changes the operation, which leaves the verb count at
    two — so counting verbs guards the wrong invariant. If this ever starts
    enumerating, ranking or recommending commander sets, it has become a second
    operation wearing a flag, and it has also taken work ADR-0002 gives the
    composer.
    """
    deck = write_deck(tmp_path, "d", deck_text("d", [ZORALINE], ["1 Plains"]))
    _, full, _ = run(
        ["check", *four_decks(tmp_path, ["1 Plains"]), "--facts", str(facts_file)], capsys
    )
    # A part-built table is also a run over real decks, and it is the stage that
    # carries seat-dependent facts such as the scarcest basic. The checkpoint may
    # produce nothing that no stage with decks can produce.
    _, part, _ = run(
        ["check", str(deck), "--commander", "Wick, the Whorled Mind", "--facts", str(facts_file)],
        capsys,
    )
    _, point, _ = run(
        ["check", "--commander", "Zoraline, Cosmos Caller", "--facts", str(facts_file)], capsys
    )

    introduced = _paths(point) - (_paths(full) | _paths(part))
    assert introduced == set(), (
        f"the checkpoint introduced fields a full run cannot produce: {introduced}"
    )

    absent = _paths(full) - _paths(point)
    assert "passed" in absent, "a checkpoint must not report green; that is gen 1's false green"
    assert {"decks.metrics.size", "decks.metrics.lands", "table.metrics.spread"} <= absent


def test_the_checkpoint_reports_what_a_commander_alone_decides(
    tmp_path, facts_file, capsys
) -> None:
    _, point, _ = run(
        ["check", "--commander", "Zoraline, Cosmos Caller", "--facts", str(facts_file)], capsys
    )
    metrics = point["decks"][0]["metrics"]
    assert metrics["tribal_core"]["Bat"]["ceiling"]["total"] >= 0
    assert "count" not in metrics["categories"]["ramp"]
    assert "ceiling" in metrics["categories"]["ramp"]
    assert point["table"]["metrics"]["basic_budget"]["Plains"]["owned"] > 0
    assert "estimated" in point["table"]["metrics"]["basis"]


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


def test_undecodable_card_facts_exits_one_with_json(tmp_path, capsys) -> None:
    """The contract itself: exit 1, one JSON object on stderr, nothing on stdout."""
    facts = tmp_path / "card_facts.json"
    facts.write_bytes(b'{"schema": 1, "cards": ["\xff\xfe"]}')
    code, out, err = run(
        ["check", "--commander", "Zoraline, Cosmos Caller", "--facts", str(facts)], capsys
    )
    assert code == 1
    assert out == {}
    assert err["error"] == "card_facts_unreadable" and err["next"]


def _every_key_path(obj, prefix: str = ""):
    """Every key path in a payload, walking EVERY list element, not a sample.

    A guard that sampled the first element would miss a `passed` on the second
    deck, which is exactly where a part-built table puts its unbuilt seats.
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            yield path
            yield from _every_key_path(value, path)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _every_key_path(value, f"{prefix}[{index}]")


def _passed_paths(payload) -> list[str]:
    return [p for p in _every_key_path(payload) if p == "passed" or p.endswith(".passed")]


def test_a_verdict_is_present_only_when_its_subject_exists_in_full(
    tmp_path, facts_file, capsys
) -> None:
    """ADR-0006: the rule is about the subject, not the depth.

    The table's `passed` and `table.passed` need every seat, so at a checkpoint
    or a part-built table they are absent — both were vacuously true, `all()`
    over a subject that did not yet exist. A built deck's `passed` is a measured
    result and stays. Every path in the payload is walked, every list element,
    so a vacuous verdict anywhere else cannot slip past.
    """
    deck = write_deck(tmp_path, "d", deck_text("d", [ZORALINE], ["1 Plains"]))

    _, point, _ = run(
        ["check", "--commander", "Zoraline, Cosmos Caller", "--facts", str(facts_file)], capsys
    )
    assert _passed_paths(point) == [], "a checkpoint judges nothing that exists"

    _, part, _ = run(
        ["check", str(deck), "--commander", "Wick, the Whorled Mind", "--facts", str(facts_file)],
        capsys,
    )
    built = [i for i, d in enumerate(part["decks"]) if "deck" in d]  # seats have no deck key
    assert built == [0]
    assert _passed_paths(part) == [f"decks[{i}].passed" for i in built]


def test_every_passed_key_returns_once_every_seat_is_built(tmp_path, facts_file, capsys) -> None:
    """With all four seats built, every verdict is back and means what it says."""
    _, out, _ = run(
        ["check", *four_decks(tmp_path, ["1 Plains"]), "--facts", str(facts_file)], capsys
    )
    assert _passed_paths(out) == [
        "passed",
        "decks[0].passed",
        "decks[1].passed",
        "decks[2].passed",
        "decks[3].passed",
        "table.passed",
    ]


@pytest.mark.parametrize("count", [1, 2, 3])
def test_fewer_than_four_decks_is_not_a_table(tmp_path, facts_file, capsys, count: int) -> None:
    """`check` on one deck alone was certified as a finished table.

    No seat was declared, so none looked unbuilt: `passed`, `table.passed` and
    "render the decklists" on a quarter of a table, and the missing seats charged
    nothing against the basic budget — the first deck looks cheap, which is what
    ADR-0005 builds the scarcest basic first to prevent. Each built deck keeps its
    own verdict; only the table's are withheld, and `next` asks for the rest.
    """
    decks = four_decks(tmp_path, ["1 Plains"])[:count]
    _, out, _ = run(["check", *decks, "--facts", str(facts_file)], capsys)
    assert _passed_paths(out) == [f"decks[{i}].passed" for i in range(count)]
    assert "render" not in out["next"].lower()


def test_more_than_four_seats_exits_one_with_json(tmp_path, facts_file, capsys) -> None:
    """ADR-0006: exit 1, one JSON object on stderr, nothing on stdout."""
    decks = four_decks(tmp_path, ["1 Plains"])
    decks.append(str(write_deck(tmp_path, "d4", deck_text("d4", [SEAT_LINES[4]], ["1 Plains"]))))
    code, out, err = run(["check", *decks, "--facts", str(facts_file)], capsys)
    assert code == 1
    assert out == {}
    assert err["error"] == "too_many_seats" and err["next"]


def test_the_same_deck_given_twice_exits_one(tmp_path, facts_file, capsys) -> None:
    deck = write_deck(tmp_path, "d", deck_text("d", [ZORALINE], ["1 Plains"]))
    code, out, err = run(["check", str(deck), str(deck), "--facts", str(facts_file)], capsys)
    assert code == 1
    assert out == {}
    assert err["error"] == "deck_given_twice"


def test_a_commander_declared_twice_exits_one(tmp_path, facts_file, capsys) -> None:
    code, out, err = run(
        [
            "check",
            "--commander",
            "Zoraline, Cosmos Caller",
            "--commander",
            "Zoraline, Cosmos Caller",
            "--facts",
            str(facts_file),
        ],
        capsys,
    )
    assert code == 1
    assert out == {}
    assert err["error"] == "commander_declared_twice" and err["next"]
