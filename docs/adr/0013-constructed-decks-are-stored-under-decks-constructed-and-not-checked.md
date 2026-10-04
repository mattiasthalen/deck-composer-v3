# ADR-0013 — Constructed decks are stored under `decks/constructed/` and are not checked

**Status:** Accepted (2026-10-04)

## Context

The owner asked for a pair of 60-card decks to play against each other in
Standard or Modern: Frogs (GU) and Lizards (BR), built from the Bloomburrow cards
in the OmniHive binder of the 2026-10-04 export (sha256 `c0d0c4a3…ed5c`). The
four Commander decks in their own binders were left out of the pool.

Everything the tool does assumes Commander. `check` enforces singleton, 100
cards and colour identity, and a table is four decks (lexicon; ADR-0006). A
60-card deck given to `check` fails its rules and would be counted as a fifth or
sixth seat. The conventional invocation `check decks/*.deck.txt` would then fail
with more than four seats.

How a constructed deck should be modelled and checked — the format's rules, a
pair in place of a table, the basic budget, the selection checkpoint — has not
been designed. The owner wants the decks committed now and that design done
separately.

## Decision

**Constructed decks live in `decks/constructed/` as ManaBox decklists in the
deck-file grammar of
[ADR-0012](0012-the-manabox-decklist-is-the-deck-file.md):** `// schema: 1`, a
`// Mainboard` section, owned cards pinned to the printing they are pulled from,
basics bare. They import into ManaBox as-is.

**`check` does not read them.** The directory sits below the glob
`decks/*.deck.txt`, so the Commander table is checked exactly as before. Their
measurements — 60 cards, at most four copies of a nonbasic, every copy present in
the binder — were taken once, from the card facts and the export, by a script
outside the tool.

Rejected: placing them beside the Commander deck files. The table's invocation
would read them as seats.

Rejected: keeping them out of the repository. The owner wants the lists
versioned with the rest of the decks.

## Consequences

Nothing re-verifies these lists. A refresh that changes ownership, or an edit to
a list, can make one unbuildable from the binder without anything reporting it.

Nothing records which binder or export a constructed deck was built from except
this ADR; ADR-0012 admits no provenance comment and there is no pair-level file
to carry it.

The design of constructed decks as a checked format is open, and supersedes
this ADR when it lands.
