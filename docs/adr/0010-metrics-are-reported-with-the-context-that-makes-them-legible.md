# ADR-0010 — Metrics are reported with the context that makes them legible: pool ceilings beside targets, balance as spread without a threshold

**Status:** Accepted (2026-09-20)

## Context

Gen 1's build reported shortfalls against default targets in one shape, when they
were three different things.

Its white-black deck held 0 sweepers against a target of 2. The owned pool holds
exactly three sweepers and all three are red, so in white-black that target is
unreachable and always will be.

The same deck held 2 ramp against a target of 10. The owned white-black pool
supplies more ramp than the deck took, but still fewer distinct cards than the
target asks for — a shortfall that can be narrowed and never closed.

A blue-red deck at the same table held 0 sweepers where the pool offers several in
those colours. That one was a build choice.

Nothing in the report separated the three. A target that cannot be met is read once
and then ignored, and the shortfalls that are build choices get ignored with it.

Balance was decided as a metric rather than a gate. A band was proposed, calibrated
from gen 1's three hero decks, and validated by the observation that it trips gen
1's villain deck. That validation does not transfer: this table is symmetric and has
no deck built to differ. The band would have been a threshold supported only by
examples that pass it.

## Decision

**Every metric target is reported beside the pool ceiling** for that deck's colour
identity — the most the owned collection could supply. `ramp 2 (target 10, ceiling
2)` distinguishes a build failure from a collection fact at a glance.

**The ceiling is computed from colour identity alone.** Cross-deck contention is
reported separately rather than folded into the ceiling, because a ceiling that
moves with build order cannot be reasoned about.

**A ceiling counts distinct card names, not copies.** Singleton caps every nonbasic
at one per deck, so four copies of a card supply one slot, not four. Counting copies
inflates every ceiling and does it invisibly, since the inflated number is still
plausible. This applies to every category; basics are the only cards whose ceiling
is a copy count.

**A target the collection structurally cannot meet is still reported.** Sweepers
stay at a target of 2 against a pool holding one. With the ceiling beside it, the
number says the collection is a sweeper short, which is actionable.

**Balance is reported as the spread across the four decks** on land count, average
mana value, creature count and interaction count, with no threshold on any axis.

**The table review states the four spreads.** An unthresholded number fails by going
unread; requiring the review to cite it makes that failure a visibly missing section
instead of a silent pass.

Rejected: a calibrated balance band. The only example that would have failed it is a
deck type this table does not have, so the threshold would have been invention
presented as calibration, and cargo-culted into later tables.

Rejected: dropping targets the collection cannot meet. That hides a real gap in the
collection, which is information worth having.

## Consequences

Nothing about balance fires automatically. Drift is caught by a reader, and the
review requirement is what guarantees there is one.

A threshold becomes worth setting once a table has been played and a deck felt off.
That is one data point and a minute's work, and it will be grounded in something.

`check` computes a ceiling per category per deck, which is more work than reporting
the count alone.
