# ADR-0011 — One card-facts file carries both the Scryfall projection and ownership

**Status:** Accepted (2026-09-20)

## Context

`check` needs two things about a card: what it is, and how many copies exist in
the shoebox. The first comes from Scryfall, the second from the ManaBox export.
[ADR-0005](0005-basics-are-counted-against-the-export-and-allocated-at-the-table.md)
makes the second load-bearing, because basics are counted against the export with
no exemption and are the only genuinely contended resource at this table.

`deck-composer-v2` kept them in two committed files and decided, in its ADR-0003,
that the catalog would carry no ownership at all. Its reasoning was sound for the
shape it had: ownership in the catalog would be a second copy of what the
collection file already held, and the two would disagree in the window between an
ingest and a catalog build.

That project also exposed the trap that makes ownership non-obvious. Eight token
lots in this collection share a card's name — Starscape Cleric is six copies of a
Bloomburrow card and two copies of a Bloomburrow *token*. Summing owned quantity
by name answers eight. Its ADR-0013 fixed this by joining through printings.

## Decision

**One committed file, `data/card_facts.json`, carries the projection and
ownership together.** A card records `owned`, and each of its printings records
its own `owned`.

**Ownership joins through printings, never by name.** A lot contributes to the
card its Scryfall ID belongs to, so a token printing never inflates the card that
shares its name.

**Ownership is recomputed from the export on every refresh, offline.** Fetching
is incremental: only printings the file does not already carry. `refresh --all`
re-fetches everything and is the deliberate way to learn about legality and Game
Changer flips.

Rejected: v2's split into a collection file and a catalog. Its objection —
two files each claiming ownership, disagreeing between builds — is defeated
outright rather than ignored: with one file there is no second claimant and no
staleness window, because ownership and facts are written by the same operation
from the same pinned snapshot. The objection was to the duplication, not to
ownership living beside the facts.

Rejected: coupling ownership to fetching. Ownership changes every time the owner
re-exports; card facts change when Scryfall changes. Making a re-export cost a
full crawl would make the owner stop re-exporting, and the export is the only
source of the basic budget.

## Consequences

A re-export after a trade costs no Scryfall requests. Measured on the real
collection: the first refresh fetches 676 printings in 10 requests, and the
second makes none.

`refresh` is the only writer of ownership, so nothing else can disagree with it.
A consumer reading a card has everything it needs in one place, which is what
[ADR-0003](0003-the-composer-reads-the-whole-pool-no-filter-layer.md) asks for.

A card the project has seen but does not own is carried with `owned` of zero
rather than dropped, so a name the composer has resolved stays resolvable.

The file is derived and may be deleted and rebuilt, at the cost of the requests.
