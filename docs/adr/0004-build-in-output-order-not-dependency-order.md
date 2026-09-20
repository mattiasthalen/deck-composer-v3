# ADR-0004 — Build in output order, not dependency order

**Status:** Accepted (2026-09-20)

## Context

`deck-composer-v2` built in dependency order: project scaffold, ManaBox ingest,
Scryfall client, catalog, collection view, then the deck analyzer's design. Each
step was well made and each was a prerequisite for the next. The project ended with
a complete data model, thirteen ADRs, and no deck.

`manabase` reached output. The difference between them was sequencing, not
architecture — gen 2's design was the better one and never ran.

The owner's stated want for v3 is four decklists now, with a system that extends to
a new table next month.

## Decision

**Build in the order the output needs.** Four importable decklists exist before
`check` is complete. `check` thickens underneath them afterwards.

Rejected: dependency order, the floor first and the composer last. It is the more
orderly sequence and it is what gen 2 did.

## Consequences

Early decks pass a weaker check than later ones. A deck committed before a rule
exists may violate that rule once it is added; re-running `check` over committed
decks is cheap and is expected to find things.

The first decklists carry more of the composer's unverified judgment than later
ones will. This is a known and accepted cost of reaching output early, not an
oversight to be corrected by delaying output.

Ordering work this way makes partial systems useful, which is the property gen 2
lacked.
