# ADR-0006 — `check` exits zero and returns violations as data

**Status:** Accepted (2026-09-20)

## Context

The caller of `check` is a model reading JSON, in a loop, while composing. A deck
with violations is the normal state of a deck being built, not an error.

## Decision

**`check` exits 0 and reports violations in its output.** A table with violations
and a table without one are both successful runs.

**Exit 1 is reserved for contract failure:** an unreadable or malformed deck file,
an unknown schema version, a card name absent from the card facts, more than four
seats, or the same deck given twice. Fewer than four seats is not a failure — a
part-built table is a defined state and the output says which seats are missing —
but a table of five is not a table, and there is no output that would be correct
for it.

Rejected: a distinct exit code for "violations found". It widens the contract of
the tool for a caller that reads the JSON either way, and every future caller then
has three cases to handle instead of two.

## Consequences

A shell caller cannot distinguish a clean table from a violating one by exit status
and must read the output. This is accepted: the intended caller always reads the
output.

A card name the card facts do not carry is a contract failure rather than a
violation, which keeps name resolution out of `check` and in the operation that
writes the card facts.

**A verdict field is present only when the thing it judges exists in full.** The
table's `passed` and the table-level `passed` need exactly four decks, all built,
and are absent until then — counted, not inferred from which flags were passed; a
deck's `passed` needs that deck and is present once it is built. A
`passed: true` whose subject does not yet exist is vacuously true — `all()` over
nothing — and reads as a pass. Gen 1 shipped that shape and it was caught by hand.
The rule is about the subject, not the depth: dropping every `passed` at a
part-built table would discard a built deck's real result to remove a vacuous one,
and a consumer would then have to derive legality from an empty `violations` list.
The `next` sentence follows the same rule and never certifies what a withheld
verdict withholds.

Every vacuous verdict or reason found in this project so far had the same
mechanism: `all()` or its equivalent over a collection that was empty — zero
decks, zero rival claimants, a flag standing in for a seat count. The asymmetry
is the useful part: `all()` over nothing is true and so certifies; `any()` over
nothing is false and so does not. A verdict or reason computed by `all()` over a
collection that can be empty is suspect until the empty case is handled by name,
and a reviewer should read every such site with that in mind.
