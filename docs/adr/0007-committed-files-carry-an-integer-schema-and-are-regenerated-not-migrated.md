# ADR-0007 — Committed files carry an integer schema and are regenerated, never migrated

**Status:** Accepted (2026-09-20)

## Context

The project commits card facts, deck files and a table file. All of them will change
shape as the design moves.

Every input is re-obtainable: the collection from a ManaBox export, the card facts
from Scryfall, the decks from the composer against a pinned snapshot.

## Decision

**Every committed file carries an integer `schema` field.** A reader that meets an
unknown value fails loudly rather than guessing.

**A schema change is handled by regenerating the file, not by migrating it.** No
migration code is written.

**Every table records the export's sha256 and the card facts' refresh date.** A
table states the snapshot it was built against, so a later table can be compared to
it and a re-run can be told apart from a rebuild on new cards.

Rejected: migration code from one schema to the next. Because the source is always
re-obtainable, a migration would be written once and run once.

## Consequences

Committed data can be thrown away and rebuilt at any point, which makes schema
changes cheap and makes the files safe to treat as derived rather than precious.

Regenerating card facts costs Scryfall requests, so a schema change is not free
while offline.

Deck files are the exception in spirit: they hold the composer's judgment and
cannot be regenerated identically, which is why they are committed and pinned to a
snapshot rather than treated as a cache.
