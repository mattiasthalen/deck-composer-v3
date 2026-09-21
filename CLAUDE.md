# deck-composer-v3

Deterministic tools behind the deck composer. The tool computes; it does not
select. Read [`docs/adr/`](docs/adr/) before changing behaviour — several
decisions here consciously reject what the two earlier generations did, and the
rejections carry the reasons.

## Commands

```sh
uv sync                                          # once; installs dev tools too
uv run deck-composer refresh exports/ManaBox_Collection.csv
uv run deck-composer refresh exports/ManaBox_Collection.csv --all   # re-fetch everything
uv run deck-composer check decks/*.deck.txt
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run pyright
```

## The two verbs (ADR-0001)

There are exactly two, and a new fact is a **field in `check`'s output, never a
new verb**. A genuinely new verb supersedes ADR-0001.

`check --commander` serves ADR-0008's selection checkpoint and is the same verb
only while it returns **the same table-shaped object with the deck-dependent
fields absent** — a table with commanders and no decks is that table earlier. It
becomes a third verb the moment it returns something different: enumerating
candidate sets, ranking them, or emitting anything shaped like a recommendation.
That would also take work ADR-0002 gives the composer. Counting verbs does not
catch this, because the count stays at two; the test asserts the output's shape
instead.

`check` takes the whole table in one call, because cross-deck contention and the
basic budget are properties of the table and are not computable from one list.

## Tool contract

- Success: exactly one JSON object on stdout, exit 0, always with a `next`
  sentence saying what to do now.
- Contract failure: one JSON object on stderr, `{"error", "detail", "next"}`,
  exit 1, nothing on stdout. Usage error: exit 2.
- **`check` exits 0 whether or not it found violations** (ADR-0006). Violations
  are data. Exit 1 means an unreadable deck file, an unknown schema, or a card
  name the card facts do not carry.
- Raise `ToolError(error, detail, next_step)` from `deck_composer.errors`. Every
  failure says what to do next. Never echo a price.
- A field the design has not settled is **absent** from the output — never null
  and never a guessed default. A null invites a zero; an absent field cannot be
  cited by a playbook. This is a corollary of ADR-0002 and ADR-0006.
- Every metric reports its **ceiling beside its target** (ADR-0010):
  `ramp 2 (target 10, ceiling 11)` tells a build choice from a collection wall.
  The ceiling comes from colour identity alone; contention is reported apart.
- **Balance has no threshold.** `check` reports the spread across the four decks
  on land count, average mana value, creature count and interaction count, and
  judges none of them. The table review is required to state all four.

## The independence rule (ADR-0002)

**Every number the tool reports derives from Scryfall card facts.** The checker
receives deck files and card facts, and nothing else — not the composer's
reasoning, tags or intent. A creature count reads `type_line`. A tribal count
reads `type_line` and oracle text.

Concretely: `check` reports the tribal core for **every** creature subtype on the
commander's type line, never the one tribe the builder had in mind. The composer
names which it built around; the tool only measures.

Gen 1 shipped `4 Uncharted Haven` against a green singleton check that inspected
nonland cards only. `tests/test_check.py` opens with that regression. Keep it
first.

## Data layout

| Path | What | Committed |
|---|---|---|
| `exports/` | ManaBox exports (carry prices) | never |
| `data/card_facts.json` | the **card facts**: the Scryfall projection plus ownership | yes |
| `data/categories.json` | bracket category patterns; WotC's data, with the document and date | yes |
| `data/targets.json` | house metric targets; ours, and on a different authority | yes |
| `decks/*.deck.txt` | the **deck files**: ManaBox decklists, schema in a comment | yes |
| `tests/fixtures/` | rows cut from the real export, prices blanked; goldens | yes |

Every committed file carries an integer `schema`, fails loudly on an unknown
value, and is **regenerated rather than migrated** (ADR-0007). No migration code.

## Module ownership

| Module | Owns exclusively |
|---|---|
| `manabox.py` | Both ManaBox formats: the CSV export and the decklist |
| `scryfall.py` | The API surface and the projection from an object to a record |
| `facts.py` | `data/card_facts.json` and the `refresh` operation |
| `rules.py` | `data/categories.json` and `data/targets.json`: patterns, corrections, matching |
| `check.py` | The rules and the measurements |
| `cli.py` | Argument parsing, JSON rendering, exit codes, project root |

A module never parses another module's format.

## Traps the collection actually contains

- **Set codes are uppercase in the export and lowercase on Scryfall.** Ingest
  lowercases; nothing else normalizes.
- **A printing in a token set is a token, whatever layout Scryfall gives it.**
  Role tokens have layout `flip`, dungeons `normal`.
- **Eight token lots share a card's name.** Starscape Cleric is six copies of a
  card and two of a token. **Ownership joins through printings, never by name.**
- **A decklist line is not uniformly `N Name (SET) COLLECTOR`.** Basics and
  unowned maybeboard entries are the bare `15 Plains`. A parser requiring the
  suffix drops every basic — the quantity ADR-0005 makes load-bearing.
- **The maybeboard holds unowned cards** and counts towards nothing.
- 25 names contain `//`; the export is CRLF; `edhrec_rank` is absent on tokens
  and seven owned cards.

## Fixture policy

Fixtures are real rows from the owner's export with `Purchase price` blanked.
Never commit an export. Never put a non-empty price in a fixture. Cached Scryfall
responses are scrubbed of the keys the projection does not carry, and a test
enforces that no price, image or purchase key reaches the committed file.

`tests/fixtures/golden/card_facts.json` locks the file layout byte-for-byte and
`tests/fixtures/golden/categories.json` locks category membership over the owned
pool. Both regenerate **only** on explicit request:

```sh
DECK_COMPOSER_REGENERATE_GOLDEN=1 uv run pytest
```

Nothing regenerates a golden automatically on failure. Regeneration is what puts
the diff in front of a human, and it stops working the moment it is automatic
(ADR-0009).

`tests/fixtures/scryfall/known_positive.json` holds cards the owned pool cannot
exercise — Time Warp, Armageddon, Ruination and friends. Extra turns and mass
land denial have zero owned examples, so without this fixture both violation
patterns would be untested assertions.

## Vocabulary

Use the words in [`docs/lexicon.md`](docs/lexicon.md) and only those, in code
identifiers, tests and docs.
