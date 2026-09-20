# ADR-0008 — The owner picks the commanders at a checkpoint before any deck is built

**Status:** Accepted (2026-09-20)

## Context

The collection holds 24 legendary creatures. With Wick fixed, 1,535 of the 1,771
possible three-commander sets alongside him can fill four decks completely from the
owned pool, so the choice is not forced by supply. It is forced in part by the land
base ([ADR-0005](0005-basics-are-counted-against-the-export-and-allocated-at-the-table.md)),
which admits at most two black decks.

The sets that remain play very differently. A table of Mouse, Squirrel and Rabbit
goes wide on the ground; one containing Otters puts a spells deck at the table.
That difference is the owner's taste, and the owner asked to make the choice.

Building four decks is the expensive half of the work.

## Decision

**The composer presents the viable commander sets and the owner picks one before
any deck is built.** The presentation carries what actually distinguishes them: the
tribal core available to each commander, the basic-land headroom for the set as a
whole, and a one-line sketch of how each deck would play.

Rejected: composing four decks and presenting them for approval. A rejected set of
commanders discards all the deck-building work, and the commander choice is the
cheapest decision to get right.

Rejected: the composer choosing the commanders outright. The owner asked for the
choice, and the difference between viable sets is taste rather than correctness.

## Consequences

Composition has two phases with a human decision between them, so it is not a
single unattended run.

The information presented at the checkpoint must be computed before any deck exists,
which means tribal core and basic headroom are computable from the card facts and a
commander alone.
