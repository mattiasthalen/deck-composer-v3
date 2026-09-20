# ADR-0012 — The ManaBox decklist is the deck file

**Status:** Accepted (2026-09-20)

## Context

The output the owner actually wants is a decklist he can import into ManaBox.
[ADR-0007](0007-committed-files-carry-an-integer-schema-and-are-regenerated-not-migrated.md)
requires every committed file to carry an integer `schema`, and a decklist is
plain text with no obvious slot for one.

`deck-composer-v2` resolved this with a JSON deck file (its ADR-0009), rendering
the decklist as a separate artifact. Its stated objection to using the text
directly was that the text has nowhere to put a schema, an `origin`, or a
commander except a comment line.

Two of those three no longer apply. v3 has no `origin` concept — gen 2's
built/owned/external distinction never entered this design — and the commander
has its own `// Commander` section in the format. Only the schema was ever a real
gap.

Gen 1's four decks, which imported successfully, already lead with a free comment
line naming the deck, so ManaBox demonstrably ignores comments it does not know.

## Decision

**The deck file is the ManaBox decklist itself.** There is no parallel JSON
representation.

**The schema rides in a comment, `// schema: 1`, as the first line.** ManaBox
ignores it; this project reads it and fails loudly on an unknown value.

**`schema` is the only thing that may ride in a comment.** Every table-level
fact — the export's sha256, the card facts' refresh date, which four decks form
the table — lives in the table file.

**The maybeboard never counts.** It holds cards the owner does not own, so it
contributes to no violation and no metric.

Rejected: v2's JSON deck file plus a rendered decklist. Two representations of
one list drift, and the rendered one is the only one anybody uses. Keeping both
means every change is made twice and verified once.

## Consequences

What the checker reads is byte-for-byte what the owner imports, so a deck cannot
pass a check in one form and fail to import in another.

A parser for this format must not require the set suffix. An owned pinned
printing is `1 Name (SET) COLLECTOR`; a basic land or an unowned maybeboard entry
is the bare `15 Plains`. A parser demanding the suffix silently drops every
basic, which is precisely the quantity ADR-0005 makes load-bearing.

If a second fact ever wants a comment slot, that is the signal that the decklist
is the wrong canonical form. The answer then is to supersede this ADR, not to
accrete another comment — a bespoke format wearing ManaBox clothes is worse than
either honest option.

Deck files hold the composer's judgment and cannot be regenerated identically,
which is why ADR-0007 treats them as committed rather than as a cache.
