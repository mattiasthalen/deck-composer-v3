"""Owns `data/categories.json` and `data/targets.json` (ADR-0009).

Bracket criteria are WotC's data, not this project's logic, so the patterns live
in a versioned file carrying the document they came from and the date it was
read. House metric targets live in a separate file: a WotC update and a change
of taste have different authorities and different cadences.

Include and exclude lists correct a pattern **for violation categories only**.
A missed violation is a legality failure and needs a correction path; metric
categories never block, so maintaining lists for them is work with no payoff.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deck_composer.errors import ToolError

SCHEMA = 1
VIOLATION = "violation"
METRIC = "metric"
_REMINDER = re.compile(r"\([^()]*\)")


@dataclass(frozen=True, slots=True)
class Category:
    name: str
    kind: str
    patterns: tuple[re.Pattern[str], ...]
    not_patterns: tuple[re.Pattern[str], ...]
    include: frozenset[str]
    exclude: frozenset[str]
    types_excluded: tuple[str, ...] = ()

    @property
    def blocks(self) -> bool:
        return self.kind == VIOLATION

    def matches(self, name: str, text: str, *, type_line: str = "") -> bool:
        """Exact-name corrections win over patterns, and only violations have them."""
        if name in self.exclude:
            return False
        if name in self.include:
            return True
        front = type_line.split("//")[0]
        if any(excluded in front for excluded in self.types_excluded):
            return False
        if any(pattern.search(text) for pattern in self.not_patterns):
            return False
        return any(pattern.search(text) for pattern in self.patterns)


@dataclass(frozen=True, slots=True)
class Rules:
    version: str
    content_hash: str
    source: dict[str, Any]
    categories: tuple[Category, ...]

    def category(self, name: str) -> Category | None:
        return next((c for c in self.categories if c.name == name), None)

    @property
    def violations(self) -> tuple[Category, ...]:
        return tuple(c for c in self.categories if c.blocks)

    @property
    def metrics(self) -> tuple[Category, ...]:
        return tuple(c for c in self.categories if not c.blocks)


@dataclass(frozen=True, slots=True)
class Targets:
    version: str
    content_hash: str
    values: dict[str, dict[str, float]]

    def of(self, name: str) -> dict[str, float] | None:
        return self.values.get(name)


def searchable(type_line: str, oracle_text: str | None, faces: Any = ()) -> str:
    """Type line and oracle text across every face, with reminder text removed.

    Reminder text restates rules a card does not itself do — Psychic Whorl's
    parenthetical explains surveil — so matching it would count the explanation
    as the effect.
    """
    parts = [type_line or "", oracle_text or ""]
    for face in faces or ():
        parts.append(getattr(face, "type_line", None) or "")
        parts.append(getattr(face, "oracle_text", None) or "")
    return _REMINDER.sub("", "\n".join(parts)).lower()


def _compile(patterns: list[str], *, where: str) -> tuple[re.Pattern[str], ...]:
    compiled = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern, re.I))
        except re.error as exc:
            raise ToolError(
                "pattern_invalid",
                {"category": where, "pattern": pattern, "reason": str(exc)},
                "Fix the pattern in data/categories.json.",
            ) from exc
    return tuple(compiled)


def read_rules(path: Path, *, display: str | None = None) -> Rules:
    payload, digest = _load(path, display or path.name, "categories")
    categories = []
    for name, body in (payload.get("categories") or {}).items():
        kind = body.get("kind")
        if kind not in (VIOLATION, METRIC):
            raise ToolError(
                "category_kind_unknown",
                {"category": name, "kind": kind},
                f"Set kind to {VIOLATION!r} or {METRIC!r} in data/categories.json.",
            )
        if kind == METRIC and (body.get("include") or body.get("exclude")):
            raise ToolError(
                "correction_list_on_a_metric",
                {"category": name},
                "Only violation categories carry include/exclude lists (ADR-0009).",
            )
        categories.append(
            Category(
                name=name,
                kind=kind,
                patterns=_compile(body.get("patterns") or [], where=name),
                not_patterns=_compile(body.get("not_patterns") or [], where=name),
                include=frozenset(body.get("include") or []),
                exclude=frozenset(body.get("exclude") or []),
                types_excluded=tuple(body.get("types_excluded") or []),
            )
        )
    return Rules(
        version=payload.get("version", ""),
        content_hash=digest,
        source=payload.get("source") or {},
        categories=tuple(sorted(categories, key=lambda c: c.name)),
    )


def read_targets(path: Path, *, display: str | None = None) -> Targets:
    payload, digest = _load(path, display or path.name, "targets")
    return Targets(
        version=payload.get("version", ""),
        content_hash=digest,
        values={str(k): dict(v) for k, v in (payload.get("targets") or {}).items()},
    )


def _load(path: Path, shown: str, what: str) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise ToolError(
            f"{what}_not_found",
            {"path": shown},
            f"Restore data/{what}.json; it is hand-edited and committed.",
        ) from exc
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ToolError(
            f"{what}_unreadable", {"path": shown}, f"Fix the JSON in data/{what}.json."
        ) from exc
    if payload.get("schema") != SCHEMA:
        raise ToolError(
            f"{what}_schema_unknown",
            {"path": shown, "schema": payload.get("schema"), "expected": SCHEMA},
            "Regenerate the file; this project does not migrate schemas (ADR-0007).",
        )
    return payload, digest
