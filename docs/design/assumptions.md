# Assumptions record

Standing assumptions the design depends on, each with the observation that would
show it stopped holding, plus the facts this project has measured. Maintained by
design interviews.

An assumption is a statement the design treats as true without the code enforcing
it. When one stops holding, every branch that hangs off it needs a second look.

First entries from the system design interview of 2026-09-20.

## Standing assumptions

| ID | Assumption | Area | Status | You would know it stopped holding when |
|---|---|---|---|---|
| A1 | The collection is unchanged since gen 1 built against it. | Ingest | Verified 2026-09-20: the current export and `manabase/collection.csv` hold the same 1,354 cards, 603 names and 649 Bloomburrow cards. Row counts differ (869 vs 934) from lot splitting only | A new export differing in cards or names. |
| A2 | The export holds the owner's true basic-land supply; basics are finite. | Analyzer, composer | Stated by the owner, 2026-09-20, correcting an earlier draft that exempted basics | Basics bought, borrowed or proxied without re-exporting. |
| A3 | Bracket 2 is close to free for this collection. | Analyzer | Measured: 1 Game Changer owned (Vampiric Tutor), 0 extra-turn cards, 0 mass land denial | A `refresh` flipping `game_changer` on an owned card, or WotC changing the bracket definitions. |
| A4 | The whole owned pool fits in one context window. | Composer | Measured 2026-09-20: 31,000 tokens with oracle text; colour slices 11,000 to 18,000 | The collection reaching roughly five times its current size. Then ADR-0003 is revisited. |
| A5 | The ManaBox deck import format is `// Commander`, `// Mainboard` and `// Maybeboard` sections. An owned pinned printing is `N Name (SET) CollectorNumber`; a basic land or an unowned maybeboard entry is the bare `N Name`. | Artifacts | Verified 2026-09-20 against gen 1's four imported decks. A parser requiring the set suffix drops every basic | A failed import, or a land count that omits basics. |
| A6 | The tribal core ceiling is 15 to 19 cards per creature type within a commander's colour identity, counting only cards eligible for the 99 and so excluding the commander itself. Every Bloomburrow commander here is a member of its own tribe, so the including-commander reading is exactly one higher throughout and reaches 20. | Composer | Measured across all 24 owned legendary creatures, 2026-09-20; convention confirmed 2026-09-20 after the build session measured the including-commander reading | New cards, or a tribe the collection does not currently support. |
| A7 | At most two black decks can sit at one table. | Composer, analyzer | Derived from 38 Swamps against a 35-land floor with Wick mandatory, assuming an even split of basics across each deck's colours. **Measured once, against gen 1's table: conservative on four basics, exact on one, generous on none, largest error Plains at 6.** Three reasons that is weaker than it reads — every gen 1 deck is two colours where Wick is three; two of the four split their basics exactly evenly (15/15, 17/17), so an even-split model may be being checked against a builder using the same rule; and the margin comes mostly from nonbasic lands absorbing 1 to 6 slots per deck, not from the split being accurate | Acquiring Swamps; or the first three-colour deck's measured basics diverging generous, which the two-colour evidence cannot predict. |
| A8 | Two-card infinite combos are absent from this collection. | Analyzer | **Unverified.** Not computable from oracle text; model judgment only, never a green check | A combo found at the table in a deck that passed `check`. |
| A9 | Scryfall is the only card data source needed. | Card data | Holds. Bracket criteria beyond the Game Changer flag are local rules; combos are judgment | A rule needing data Scryfall does not carry. |
| A10 | Playbooks target a pilot who has never seen the deck. | Artifacts | Confirmed by the owner, 2026-09-20: friends come over and pick up three of the four decks | The decks stop being lent out. |
| A11 | Every ManaBox export row carries a Scryfall ID. | Ingest | Verified 869 of 869 rows on the 2026-08-26 export, re-checked 2026-09-20 | A row without one, such as a custom or proxy card. |
| A12 | The ManaBox `Name` column equals the exact Scryfall name. | Ingest, card data | Verified 869 of 869 rows against Scryfall by ID during gen 2 | A name mismatch on a card data build, most likely a rename on one side. |
| A13 | The oracle-text patterns for extra turns and mass land denial correctly detect those categories. | Analyzer | **Weakly held.** Zero hits and zero false positives against the owned pool, 2026-09-20 — which confirms A3 but exercises neither pattern. Tested only against a committed known-positive fixture (ADR-0009) | A card of either kind entering the collection and not being flagged. |

## Measured facts

Source: the owner's ManaBox export, collection dated 2026-08-26, profiled 2026-09-20.
`sha256:463504c90131fd7f4208eb434fc6b0ac4ff6d8e74ce9fb7e3d712a5190a82a1c`

| Fact | Value |
|---|---|
| Rows / physical cards / distinct names | 869 / 1,354 / 603 |
| Encoding | ASCII, CRLF, no BOM, `en` only, one binder, no deck rows |
| Bloomburrow | 402 rows, 649 cards, 229 names — 48% of the collection by quantity |
| Basics | 223: Forest 54, Island 49, Mountain 42, Plains 40, Swamp 38 |
| Nonbasic lands | 19 names, 47 copies; Uncharted Haven is 14 of them but singleton caps it at 4 across a table |
| Legal owned nonland names | 555, of which 215 have a Bloomburrow printing (586 copies) |
| Commander candidates | 24 legendary creatures, none with partner, none saying "can be your commander" |
| Not Commander-legal | 1, Prophet of Kruphix (banned) |
| Game Changers owned | 1, Vampiric Tutor |
| Extra-turn cards / mass land denial | 0 / 0. Candidate detection patterns return 0 hits and 0 false positives over the pool, so both are untested by it |
| Four-deck fill feasibility | 1,535 of 1,771 three-commander sets alongside Wick fill four decks of 62 spells completely; the best sets do so using only Bloomburrow-printed spells |
| Tribal core by commander (commander excluded) | Mabel/Mouse 19, Baylen/Rabbit 18, Alania/Otter 18, Wick/Rat 17, Gev/Lizard 17, Finneas/Rabbit 17, Vren/Rat 16, Muerra/Raccoon 16, Zoraline/Bat 15, Camellia/Squirrel 15 |
| Tribe contention | None. Tribe cores are near-disjoint; four tribes coexist at full size |
| Context cost | Whole pool with oracle text 31k tokens; Wick's colour slice 18k; Mabel's 11k |

Source: gen 1's table review, 2026-08-20, against the same collection. Still true as
pool facts.

| Fact | Value |
|---|---|
| Mana rocks in the owned Orzhov nonland pool | 0. Narrower than it looks — ramp is the broader category and white-black holds several. It is still short of a target of 10: 5 distinct names, 11 copies, and singleton makes 5 the ceiling |
| Ramp effects in the free Simic nonland pool | 6 |
| Real board sweepers in the whole owned pool | 3 by pattern — Brotherhood's End, Splatter Technique, Wildfire Howl — all red, so the sweeper ceiling in any deck without red is 0. Gen 1's review counted 1 under a stricter reading |
