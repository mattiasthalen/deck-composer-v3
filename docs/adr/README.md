# Architecture Decision Records

Michael Nygard's format. An ADR is superseded, never edited to change its decision.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-two-verbs-refresh-and-check-the-model-composes.md) | The tool is two verbs, `refresh` and `check`; the model composes | Accepted (2026-09-20) |
| [0002](0002-the-builder-asserts-no-fact-about-its-own-picks.md) | The builder asserts no fact about its own picks | Accepted (2026-09-20) |
| [0003](0003-the-composer-reads-the-whole-pool-no-filter-layer.md) | The composer reads the whole card pool; there is no filter layer | Accepted (2026-09-20) |
| [0004](0004-build-in-output-order-not-dependency-order.md) | Build in output order, not dependency order | Accepted (2026-09-20) |
| [0005](0005-basics-are-counted-against-the-export-and-allocated-at-the-table.md) | Basic lands are counted against the export and allocated at the table | Accepted (2026-09-20) |
| [0006](0006-check-exits-zero-and-returns-violations-as-data.md) | `check` exits zero and returns violations as data | Accepted (2026-09-20) |
| [0007](0007-committed-files-carry-an-integer-schema-and-are-regenerated-not-migrated.md) | Committed files carry an integer schema and are regenerated, never migrated | Accepted (2026-09-20) |
| [0008](0008-the-owner-picks-the-commanders-at-a-checkpoint-before-building.md) | The owner picks the commanders at a checkpoint before any deck is built | Accepted (2026-09-20) |

## Prior art in other repositories

Two earlier generations of this project carry their own decision records. They are
not binding here and several are consciously rejected above, but they hold the
reasons an option was ruled out and are worth reading before re-proposing one.

- `deck-composer-v2` — `docs/adr/`, thirteen ADRs covering ingest, the Scryfall
  catalog, the collection view, deck files, bracket rules and the analyzer.
  ADR-0003 above rejects its ADR-0005.
- `manabase` — `docs/adr/`, four ADRs covering repository layout and vendored
  skills. Its `decks/1v3-commander.table-review.txt` is the most useful document in
  either repository: it is a review that found its own system's checks reading the
  builder's tags, which is the finding behind ADR-0002 above.
