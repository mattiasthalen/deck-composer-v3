# Artifacts

What the composer writes once a table passes `check`. These are conventions, not
decisions with a fork in them; a change here needs no ADR.

Nothing here is a verb. `check` measures, the composer writes (ADR-0001), and
every number in an artifact renders from `check`'s output — an artifact cannot
claim something the checker did not measure (ADR-0002).

## Files

For a table named `<table>` with four decks named `<deck>`:

| Path | What |
|---|---|
| `decks/<deck>.deck.txt` | the deck file: a ManaBox decklist, schema in a comment (ADR-0012) |
| `decks/<table>.table.json` | the table file: which four decks, the export sha256, the card facts' refresh date (ADR-0007) |
| `docs/tables/<table>/<deck>.playbook.en.md` | the playbook, English |
| `docs/tables/<table>/<deck>.playbook.sv.md` | the playbook, Swedish |
| `docs/tables/<table>/<table>.review.md` | the one table-level document |

Eight playbooks for four decks. **Separate files per language, never one file
holding both** — it is read at the table, in one language, under time pressure.

The Swedish is a translation of the English, not an independent write-up, so the
numbers cannot drift between them. Card names stay in English: they are what is
printed on the card and what ManaBox shows.

## The playbook

Written for a pilot who has never seen the deck (A10). Gen 1's three sections,
which worked:

1. **What the deck is** — the commander, the colours, and the measured shape:
   lands, creatures, average mana value, the tribal core's two numbers. Every
   figure from `check`.
2. **How to pilot it** — concrete numbered lines. What to keep, what the deck
   wants to be doing on each of the first few turns, what the commander is for.
3. **What to watch** — where the deck is weak, what beats it, what to hold.

No team playbook. Gen 1's was archenemy-specific — one parent against three
children — and nothing in it transfers to a symmetric pod.

## The table review

The only table-level document, and the only place cross-deck judgment lives.

`check` reports the spread of land count, creature count and average mana value
across the four decks. The review carries what no check computes: gen 1's real
imbalances were that evasion clustered on one deck — Zoraline flew with 13 bodies
against Alania's 4 and Finneas's 2 — and that one deck held four counterspells
against three decks with no stack interaction at all. Neither is computable from
oracle text; both decided how the games actually felt.

The review states a verdict per axis, names the decks and the cards, and says
what it would change. It is not a summary of `check`'s output; if a finding can
be computed, it belongs in `check` instead.
