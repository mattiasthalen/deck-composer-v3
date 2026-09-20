# deck-composer-v3

Compose a Commander **table** — four decks, mutually disjoint in the physical
cards they use — from a ManaBox export of the owner's collection.

The tool is two verbs. The model composes.

```sh
uv sync
uv run deck-composer refresh exports/ManaBox_Collection.csv
uv run deck-composer check --commander "Wick, the Whorled Mind" --commander "Mabel, Heir to Cragflame"
uv run deck-composer check decks/*.deck.txt
```

`refresh` reads the export and Scryfall and writes `data/card_facts.json`.
`check` reads the four deck files together and returns violations and metrics.
Everything the tool reports derives from Scryfall card facts — never from a label
the composer applied to its own picks.

Decisions are in [`docs/adr/`](docs/adr/), vocabulary in
[`docs/lexicon.md`](docs/lexicon.md), and what the design takes on trust in
[`docs/design/assumptions.md`](docs/design/assumptions.md).
