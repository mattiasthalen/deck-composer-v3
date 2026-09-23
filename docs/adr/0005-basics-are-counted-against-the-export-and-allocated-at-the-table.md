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

That caveat carries weight at the commander checkpoint of
[ADR-0008](0008-the-owner-picks-the-commanders-at-a-checkpoint-before-building.md),
where no lists exist yet and headroom can only be the estimate. The owner chooses
commanders partly on that number, and a commander choice is the most expensive
decision at the table to revisit. So the estimate is labelled as one wherever it is
shown, and once lists exist the measured budget is compared against it: a material
divergence is reported, because it means a choice was made on a figure that did not
hold.

**Decks are built least-reliable-claim first, and the table spans built and
unbuilt seats.** The estimate is least reliable exactly where this ADR's constraint
binds: a three-colour deck's primary colour, which for a mandatory black commander
is the Swamp count against the smallest basic supply in the collection. No
correction factor is available that would not be invented, and the checkpoint has
no lists to measure. Build order is the lever that invents nothing.

The scarcest basic is the one with the least projected headroom — owned, less
measured, less estimated for the unbuilt seats — not the one least owned; 39 of 40
Plains claimed is scarcer than 10 of 38 Swamps. Among the seats claiming it, the
first built is the one with the most colours, because an even split errs by about
±2 for two colours and by 3 to 6 in the generous direction for three. Ties break
to the largest claim, and an exact tie on both to the commander name that sorts
first. That last tie is the common case, not an edge: under an even split, seats
with the same colour count make the same claim, so once the three-colour seat is
built the two-colour seats claiming the same basic tie every time. The break is
arbitrary and the rule says so; what it must not be is the composer's input order,
which would let the order a list was written in steer a tool decision. Building
the named seat first turns the least reliable estimate at the table into a
measurement while three decks are still unbuilt.

Rejected: building the seat with the largest point-estimate claim first. Under an
even split a two-colour black seat claims about 18 Swamps and a three-colour one
about 12, so that rule builds a two-colour seat first at every table tested and
never the three-colour one — retiring the most Swamps from the estimate column and
the least uncertainty. Colour count is an oracle fact, so the chosen rule invents
nothing the rejected one did not.

It works only if a part-built table is expressible. A seat that exists is charged
at its measured basics, one that does not is charged at its estimate, and the
remaining budget spans both. Checking a finished deck on its own reports the
opposite of the truth — the first deck looks cheap because the other three seats
are missing from the baseline, which is precisely the reassurance building it
first was meant to deny. A table with an unbuilt seat reports no overall pass, for
the reason a checkpoint does not.

A projection that overruns is reported and does not block, because part of it is an
estimate. Measured overuse is already an ownership violation.

Acquiring basics changes the constraint and is the cheapest way to widen the
commander options.
