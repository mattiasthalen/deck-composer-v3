"""Test helpers: an offline Scryfall transport and decklist construction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).parent / "fixtures"
EXPORT = FIXTURES / "collection.csv"
SCRYFALL = FIXTURES / "scryfall" / "collection.json"
GOLDEN = FIXTURES / "golden"


def cached_objects() -> list[dict[str, Any]]:
    return json.loads(SCRYFALL.read_text(encoding="utf-8"))


class FakeScryfall:
    """Serves the cached collection response. Never touches the network."""

    def __init__(self, objects: list[dict[str, Any]] | None = None) -> None:
        self.objects = objects if objects is not None else cached_objects()
        self.by_id = {obj["id"]: obj for obj in self.objects}
        self.calls: list[list[dict[str, str]]] = []

    def __call__(
        self, method: str, url: str, headers: dict[str, str], body: bytes
    ) -> tuple[int, bytes]:
        payload = json.loads(body) if body else {}
        identifiers = payload.get("identifiers", [])
        self.calls.append(identifiers)
        data = [self.by_id[i["id"]] for i in identifiers if i.get("id") in self.by_id]
        missing = [i for i in identifiers if i.get("id") not in self.by_id]
        return 200, json.dumps({"data": data, "not_found": missing}).encode()


def deck_text(
    name: str,
    commander: list[str],
    mainboard: list[str],
    maybeboard: list[str] | None = None,
    *,
    schema: int | None = 1,
) -> str:
    """Build a ManaBox decklist. Entries are given verbatim, e.g. `4 Uncharted Haven`."""
    lines = []
    if schema is not None:
        lines.append(f"// schema: {schema}")
    lines += [f"// {name}", "", "// Commander", *commander, "", "// Mainboard", *mainboard]
    if maybeboard:
        lines += ["", "// Maybeboard", *maybeboard]
    return "\n".join(lines) + "\n"


def write_deck(directory: Path, name: str, text: str) -> Path:
    path = directory / f"{name}.deck.txt"
    path.write_text(text, encoding="utf-8")
    return path
