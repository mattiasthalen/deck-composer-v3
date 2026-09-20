# ADR-0001 — The tool is two verbs, `refresh` and `check`; the model composes

**Status:** Accepted (2026-09-20)

## Context

Two earlier generations attacked this problem. `manabase` shipped no application
code: vendored skills, committed card data, the model doing the composing. It
produced a four-deck table. Its own review then found that the checks it passed
were reading tags the builder had written about its own picks, and that one deck
had shipped with four copies of a nonbasic land against a green singleton check.

`deck-composer-v2` rebuilt the deterministic floor properly — eight modules,
thirteen ADRs, a rules file, a category golden. It stopped one step before a deck
existed.

v3 needs the independent checking gen 1 lacked without the surface that stalled
gen 2.

## Decision

**Two verbs.** `refresh` reads the ManaBox export and Scryfall and writes the card
facts. `check` reads deck files and returns violations and metrics.

**`check` takes all four deck files in one call.** Cross-deck contention and the
basic budget are properties of the table, not of a deck, and are not computable
from one list.

**New facts go inside `check`'s output, never into a new verb.** This is the guard
against gen 2's accretion, and it is part of the decision rather than a style note.

**The model composes.** Choosing commanders, picking cards and writing prose are
judgment. The tool computes; it does not select.

Python and uv, matching the other repositories here.

Rejected: gen 1's shape, no application code with the model checking its own work.
It cannot satisfy [ADR-0002](0002-the-builder-asserts-no-fact-about-its-own-picks.md),
and its one attempt at self-checking shipped a false green.

Rejected: gen 2's eight-module CLI. The surface grew for a year of imagined
callers before any output existed, and the project ended with a complete data
model and no deck.

## Consequences

`check` is a deep module behind a small interface: a caller knows two commands and
supplies deck files.

Every cross-deck fact is available because all four decks arrive together.

Pressure to add a verb will recur whenever a new fact is wanted. The decision is
that such a fact is a field in `check`'s output. A genuinely new verb requires
superseding this ADR.
