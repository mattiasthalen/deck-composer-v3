# Lexicon

The design vocabulary for deck-composer-v3. Use these words, and only these, in
design discussions, tickets, code identifiers and documentation.

A term is admitted only when a design branch closes needing it, and only if getting
it wrong would produce divergent implementations. An entry that restates the
ordinary meaning of a word is noise; delete it. Target size is roughly 20 to 30
entries — past that, adding one means arguing another out.

Entries marked #1 come from the system design interview of 2026-09-20.

| Term | Meaning | Since |
|---|---|---|
| table | Four decks composed together from one collection snapshot, mutually disjoint in the physical cards they use. The unit `check` operates on. | #1 |
| card facts | The committed Scryfall projection for every card the project has seen. Authoritative for what a card is. Gen 1 called this the Oracle and gen 2 the catalog; this project uses one name. | #1 |
| violation | A hard-rule failure with a reason. Blocks artifacts. Reported as data, not as an error (ADR-0006). | #1 |
| metric | A measurement with a reference target. Informs judgment, never blocks. | #1 |
| tribal core | The cards relevant to a commander's creature type that its colour identity can actually field. Two numbers, never one: creatures matching the type line, and cards whose oracle text names the type. Roughly 15 to 19 in this collection, which is a core rather than a typal deck. | #1 |
| basic budget | The table-level supply of basic lands, allocated across all four decks before any land base is fixed (ADR-0005). | #1 |
| playbook | Per-deck piloting prose written for someone who has never seen the deck. Every number in it renders from measured output, so it cannot claim something `check` did not measure. | #1 |
| table review | The one table-level document. Carries the judged half of balance — the cross-deck qualitative findings no check can compute. | #1 |
