"""Owns both ManaBox formats: the collection export (CSV) and the decklist (text).

One module owns what ManaBox means. `refresh` reads the export; `check` reads
decklists; artifacts are rendered back into the same decklist format, which
gen 1 proved round-trips through a real import (A5).

The decklist is the deck file (ADR-0007 wants an integer schema on every
committed file, so it rides in a `// schema:` comment that ManaBox ignores).
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path

from deck_composer.errors import ToolError

# --- the export -------------------------------------------------------------

REQUIRED_COLUMNS: tuple[str, ...] = (
    "Binder Name",
    "Binder Type",
    "Name",
    "Set code",
    "Collector number",
    "Foil",
    "Quantity",
    "Scryfall ID",
    "Condition",
    "Language",
)
OPTIONAL_COLUMNS: tuple[str, ...] = ("Added",)
BINDER_TYPES: frozenset[str] = frozenset({"binder", "deck"})
HASH_PREFIX = "sha256:"
ROW_DETAIL_CAP = 25

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_DIGITS = re.compile(r"^[0-9]+$")


@dataclass(frozen=True, slots=True)
class Lot:
    """One export row: a quantity of one printing, in one binder, in one condition."""

    name: str
    set_code: str
    collector_number: str
    scryfall_id: str
    quantity: int
    foil: str
    condition: str
    language: str
    binder_name: str
    binder_type: str


@dataclass(frozen=True, slots=True)
class Export:
    """A ManaBox export, hashed by its raw bytes so a reformat preserves the hash."""

    file: str
    sha256: str
    rows: int
    lots: tuple[Lot, ...]
    ignored_columns: tuple[str, ...]

    def owned_by_printing(self) -> dict[str, int]:
        """Copies owned per Scryfall ID.

        Ownership joins through printings, never by name: eight token lots share a
        card's name in this collection, so summing by name overcounts (v2's
        ADR-0013 is the trap this avoids).
        """
        owned: dict[str, int] = {}
        for lot in self.lots:
            owned[lot.scryfall_id] = owned.get(lot.scryfall_id, 0) + lot.quantity
        return owned


def read_export(path: Path, *, display: str | None = None) -> Export:
    """Parse a ManaBox export, collecting every row problem before failing."""
    name = display or path.name
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise ToolError(
            "export_not_found",
            {"path": name},
            "Export your collection from ManaBox as CSV and pass its path.",
        ) from exc
    except OSError as exc:
        raise ToolError(
            "export_unreadable", {"path": name}, "Check the file's permissions."
        ) from exc

    sha = HASH_PREFIX + hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ToolError(
            "export_not_utf8",
            {"path": name},
            "Re-export from ManaBox; the export is expected to be UTF-8.",
        ) from exc

    try:
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as exc:
        raise ToolError("export_unparseable", {"path": name}, "Re-export from ManaBox.") from exc
    if not rows:
        raise ToolError("no_rows", {"path": name}, "The export is empty; re-export from ManaBox.")

    header = rows[0]
    duplicates = sorted({c for c in header if header.count(c) > 1})
    if duplicates:
        raise ToolError(
            "duplicate_columns",
            {"path": name, "columns": duplicates},
            "Re-export from ManaBox; the header repeats a column.",
        )
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ToolError(
            "missing_columns",
            {"path": name, "columns": missing, "header": header},
            "Re-export from ManaBox with the default column set.",
        )
    index = {column: position for position, column in enumerate(header)}
    ignored = tuple(c for c in header if c not in REQUIRED_COLUMNS and c not in OPTIONAL_COLUMNS)

    lots: list[Lot] = []
    problems: list[dict[str, object]] = []
    for number, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue
        found = _row_problems(row, index)
        if found:
            problems.append({"row": number, "problems": found})
            continue
        lots.append(_lot(row, index))

    if problems:
        raise ToolError(
            "invalid_rows",
            {
                "path": name,
                "total": len(problems),
                "shown": min(len(problems), ROW_DETAIL_CAP),
                "rows": problems[:ROW_DETAIL_CAP],
            },
            "Fix the rows in ManaBox and re-export.",
        )
    if not lots:
        raise ToolError("no_rows", {"path": name}, "The export holds no card rows.")

    return Export(
        file=name,
        sha256=sha,
        rows=len(lots),
        lots=tuple(sorted(lots, key=lambda x: (x.name, x.set_code, x.collector_number, x.foil))),
        ignored_columns=ignored,
    )


def _row_problems(row: list[str], index: dict[str, int]) -> list[str]:
    problems: list[str] = []
    for column in REQUIRED_COLUMNS:
        if index[column] >= len(row) or not row[index[column]].strip():
            problems.append(f"empty:{column}")
    if problems:
        return problems
    quantity = row[index["Quantity"]].strip()
    if not _DIGITS.match(quantity) or int(quantity) < 1:
        problems.append("quantity_not_positive_integer")
    if not _UUID.match(row[index["Scryfall ID"]].strip()):
        problems.append("scryfall_id_invalid")
    binder_type = row[index["Binder Type"]].strip()
    if binder_type not in BINDER_TYPES:
        problems.append(f"binder_type_unknown:{binder_type}")
    return problems


def _lot(row: list[str], index: dict[str, int]) -> Lot:
    def value(column: str) -> str:
        return row[index[column]].strip()

    return Lot(
        name=value("Name"),
        # Set codes are uppercase in the export and lowercase on Scryfall.
        set_code=value("Set code").lower(),
        collector_number=value("Collector number"),
        scryfall_id=value("Scryfall ID").lower(),
        quantity=int(value("Quantity")),
        foil=value("Foil"),
        condition=value("Condition"),
        language=value("Language"),
        binder_name=value("Binder Name"),
        binder_type=value("Binder Type"),
    )


# --- the decklist -----------------------------------------------------------

SCHEMA = 1
COMMANDER = "Commander"
MAINBOARD = "Mainboard"
MAYBEBOARD = "Maybeboard"
SECTIONS: tuple[str, ...] = (COMMANDER, MAINBOARD, MAYBEBOARD)

_SCHEMA_LINE = re.compile(r"^//\s*schema:\s*(.+?)\s*$", re.I)
_SECTION_LINE = re.compile(r"^//\s*(commander|mainboard|maybeboard)\s*$", re.I)
# A pinned printing ends in ` (SET) COLLECTOR`; a basic or an unowned card does not.
_ENTRY = re.compile(r"^(\d+)\s+(.+?)(?:\s+\(([A-Za-z0-9]{2,6})\)\s+(\S+))?$")
# A set-and-collector suffix that does not end the line. The name capture above
# is deliberately loose, because real names carry parentheses — "Erase (Not the
# Urza's Legacy One)" — so without this a trailing token such as `*F*` is
# swallowed into the name and resurfaces later as an unknown card with no line
# number. Anything after the suffix is outside the recorded format (A5).
_TRAILING = re.compile(r"\s\([A-Za-z0-9]{2,6}\)\s+\S+\s+\S")


@dataclass(frozen=True, slots=True)
class Entry:
    """One decklist line. `set_code` and `collector_number` are absent when unpinned."""

    quantity: int
    name: str
    set_code: str | None = None
    collector_number: str | None = None

    @property
    def pinned(self) -> bool:
        return self.set_code is not None and self.collector_number is not None

    def render(self) -> str:
        if self.set_code is None or self.collector_number is None:
            return f"{self.quantity} {self.name}"
        return f"{self.quantity} {self.name} ({self.set_code.upper()}) {self.collector_number}"


@dataclass(frozen=True, slots=True)
class Deck:
    """A deck file: the ManaBox decklist itself, schema carried in a comment."""

    path: str
    name: str
    commander: tuple[Entry, ...]
    mainboard: tuple[Entry, ...]
    maybeboard: tuple[Entry, ...]

    @property
    def counted(self) -> tuple[Entry, ...]:
        """Commander plus mainboard. The maybeboard holds unowned cards and never counts."""
        return self.commander + self.mainboard

    @property
    def size(self) -> int:
        return sum(entry.quantity for entry in self.counted)


def read_deck(path: Path, *, display: str | None = None) -> Deck:
    """Parse a decklist. Anything malformed is a contract failure, never a violation."""
    shown = display or path.name
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise ToolError(
            "deck_not_found", {"path": shown}, "Check the path, or compose the deck first."
        ) from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ToolError(
            "deck_unreadable", {"path": shown}, "The deck file must be readable UTF-8 text."
        ) from exc
    return parse_deck(text, path=shown)


def parse_deck(text: str, *, path: str) -> Deck:
    schema: str | None = None
    section: str | None = None
    entries: dict[str, list[Entry]] = {s: [] for s in SECTIONS}
    problems: list[dict[str, object]] = []

    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("//"):
            if (found := _SCHEMA_LINE.match(line)) is not None:
                schema = found.group(1)
                continue
            if (found := _SECTION_LINE.match(line)) is not None:
                section = found.group(1).capitalize()
                continue
            continue  # every other comment is ignored
        if section is None:
            problems.append({"line": number, "problem": "entry_before_section", "text": line})
            continue
        found = _ENTRY.match(line)
        if found is None or (found.group(3) is None and _TRAILING.search(line)):
            problems.append({"line": number, "problem": "unparseable_entry", "text": line})
            continue
        quantity = int(found.group(1))
        if quantity < 1:
            problems.append({"line": number, "problem": "quantity_not_positive", "text": line})
            continue
        entries[section].append(
            Entry(
                quantity=quantity,
                name=found.group(2).strip(),
                set_code=(found.group(3) or "").lower() or None,
                collector_number=found.group(4),
            )
        )

    if schema is None:
        problems.append({"line": 0, "problem": "schema_missing"})
    elif not _DIGITS.match(schema):
        problems.append({"line": 0, "problem": f"schema_not_an_integer:{schema}"})
    elif int(schema) != SCHEMA:
        raise ToolError(
            "deck_schema_unknown",
            {"path": path, "schema": int(schema), "expected": SCHEMA},
            "Regenerate the deck file; this project does not migrate schemas (ADR-0007).",
        )
    if problems:
        raise ToolError(
            "deck_malformed",
            {"path": path, "total": len(problems), "problems": problems[:ROW_DETAIL_CAP]},
            "Fix the deck file; every line is `N Name` or `N Name (SET) COLLECTOR`.",
        )

    return Deck(
        path=path,
        # The name is the file's, never a comment: ADR-0012 admits only `schema`
        # into a comment, and a deck named "Commander" would be read as a section.
        name=Path(path).stem.removesuffix(".deck"),
        commander=tuple(entries[COMMANDER]),
        mainboard=tuple(entries[MAINBOARD]),
        maybeboard=tuple(entries[MAYBEBOARD]),
    )


def render_deck(deck: Deck) -> str:
    """Render a decklist ManaBox can import, schema first so a reader sees it."""
    lines = [f"// schema: {SCHEMA}", ""]
    for section, group in (
        (COMMANDER, deck.commander),
        (MAINBOARD, deck.mainboard),
        (MAYBEBOARD, deck.maybeboard),
    ):
        if not group:
            continue
        lines.append(f"// {section}")
        lines.extend(entry.render() for entry in group)
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"
