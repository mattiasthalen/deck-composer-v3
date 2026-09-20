# ADR-0005 — Basic lands are counted against the export and allocated at the table

**Status:** Accepted (2026-09-20)

## Context

Basic lands are unlimited in the rules of the game and finite in a shoebox. The
owner's position is that the export holds what he actually has.

The export holds 223 basics: Forest 54, Island 49, Mountain 42, Plains 40, Swamp 38.

Four decks at a 35-land floor want roughly 140 lands. Nonbasic lands cover very
little of that: 19 names and 47 copies, but singleton caps each name at one per
deck, so a name owned in fourteen copies supplies at most four lands across the
table.

With Wick fixed as a commander, and therefore one black deck mandatory, a
table-level allocation across candidate commander sets shows Swamps as the binding
resource. Sets containing three black decks exceed the 38 available; sets with two
do not.

## Decision

**Basics are counted against the export with no exemption.** They are subject to
the same ownership check as every other card.

**The basic budget is computed across all four decks before any land base is
fixed.** A deck built alone will take thirty Swamps without noticing that two other
decks need them.

**The land floor is 35 per deck.** Gen 1 shipped 35 to 36 and its review recorded a
collision between a ticket asking for 33 to 34 and a profile floor of 35. One number
settles it.

Rejected: treating basics as unlimited. It is the game's rule and not the owner's
situation, and at this table basics are the only genuinely contended resource.

## Consequences

Commander selection is constrained by the land base: at most two black decks while
Wick is mandatory. This rules out several otherwise attractive commander sets and
must be known before decks are built, not after.

`check` computes the budget from the actual lists. The analysis behind this ADR
assumed an even split of basics across each deck's colours, which no real deck has;
the direction holds and the exact threshold moves with colour weighting.

Acquiring basics changes the constraint and is the cheapest way to widen the
commander options.
