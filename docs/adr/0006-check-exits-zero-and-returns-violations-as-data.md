# ADR-0006 — `check` exits zero and returns violations as data

**Status:** Accepted (2026-09-20)

## Context

The caller of `check` is a model reading JSON, in a loop, while composing. A deck
with violations is the normal state of a deck being built, not an error.

## Decision

**`check` exits 0 and reports violations in its output.** A table with violations
and a table without one are both successful runs.

**Exit 1 is reserved for contract failure:** an unreadable or malformed deck file,
an unknown schema version, or a card name absent from the card facts.

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
