# ADR-0002 — The builder asserts no fact about its own picks

**Status:** Accepted (2026-09-20)

## Context

Gen 1's table review, written against its own output, recorded two failures of the
same kind.

Its quota for board wipes read green because *wipe* was a tag the builder had
assigned to cards it had chosen. Its theme floor read green for the same reason:
the review's words were that theme is "a tag the build assigns to its own picks,
where creature-ness is an Oracle fact."

Separately, a deck shipped with four copies of Uncharted Haven against a green
singleton check, because that check inspected nonland cards only.

Both were caught by a human reading the output afterwards.

## Decision

**Every number in `check`'s output, and every number in any artifact, derives from
Scryfall card facts.** A category is re-derived from oracle data at check time. A
count of creatures reads `type_line`. A tribal count reads `type_line` and oracle
text, not a label the composer applied.

**The checker and the builder share no state.** The checker receives deck files —
card names and quantities — and the card facts. It does not receive the composer's
reasoning, its tags, or its intent.

Rejected: builder-supplied tags with review as the backstop. Gen 1 ran exactly
that. The review did catch it, by hand, once. A check that requires a human to
verify it is not a check, and the same review missed nothing only because someone
read all four decks closely.

## Consequences

The checker needs its own detection for any category it reports — the mechanism is
not yet decided and is tracked separately.

A playbook cannot cite a number the checker did not measure. This is the intended
constraint and it is what makes the playbooks trustworthy to someone piloting a
deck cold.

Duplicating detection in the checker costs more than reading the composer's tags.
That cost is the point.
