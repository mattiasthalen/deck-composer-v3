# Table review — bloomburrow-2026-09

The one table-level document (ADR-0010). Commanders: Wick, the Whorled Mind, Camellia, the Seedmiser, Alania, Divergent Storm, Finneas, Ace Archer. Bracket 2.

`check` over the four deck files: `passed` True, `table.passed` True, no
violations. Snapshot: export `sha256:463504c90131fd7f4208eb434fc6b0ac4ff6d8e74ce9fb7e3d712a5190a82a1c`, card facts refreshed 2026-09-20,
bracket rules 2026-09-20 (`sha256:2de25d1be64d5fabf70085b84d3432c4fa9dffd65cd5513d89aa96a35f264dae`), house targets 2026-09-20.
Every number in this document and in the eight playbooks is that run's output,
rendered into the prose, never retyped. The judged findings below name cards
rather than counts, because a count I made would be a fact the builder asserts
about its own picks (ADR-0002).

House targets for reference: draw 10, ramp 10, targeted interaction 8, sweepers 2; lands 35–37; average mana value 2.5–3.2.

## The measured table

| Commander | CI | Lands | Creatures | Avg MV | Tribal core (type+text of ceiling) | Draw (ceiling) | Ramp (ceiling) | Interaction (ceiling) | Sweepers (ceiling) |
|---|---|---|---|---|---|---|---|---|---|
| Wick, the Whorled Mind | UBR | 36 | 33 | 3.14 | 13+4=17 of 17 | 15 (62) | 3 (13) | 16 (51) | 0 (3) |
| Camellia, the Seedmiser | BG | 36 | 33 | 2.78 | 12+3=15 of 15 | 10 (24) | 10 (19) | 15 (36) | 0 (0) |
| Alania, Divergent Storm | UR | 36 | 26 | 2.97 | 10+7=17 of 18 | 21 (51) | 4 (12) | 12 (31) | 2 (3) |
| Finneas, Ace Archer | WG | 36 | 33 | 2.77 | 12+5=17 of 17 | 12 (23) | 7 (20) | 10 (21) | 0 (0) |

### The four spreads

Stated as ADR-0010 requires; no threshold on any axis.

| Axis | Values (wick, camellia, alania, finneas) | Min | Max | Spread |
|---|---|---|---|---|
| Land count | 36 / 36 / 36 / 36 | 36 | 36 | 0 |
| Average mana value | 3.14 / 2.78 / 2.97 / 2.77 | 2.77 | 3.14 | 0.37 |
| Creature count | 33 / 33 / 26 / 33 | 26 | 33 | 7 |
| Targeted interaction | 16 / 15 / 12 / 10 | 10 | 16 | 6 |

### The basic budget, estimate against measurement (ADR-0005)

Basis: measured from the lists. Overcommitted: none. Basics the estimate was
generous for: none.

| Basic | Owned | Used | Estimated | Divergence | Remaining |
|---|---|---|---|---|---|
| Forest | 54 | 31 | 35 | -4 | 23 |
| Island | 49 | 28 | 29 | -1 | 21 |
| Mountain | 42 | 21 | 29 | -8 | 21 |
| Plains | 40 | 16 | 18 | -2 | 24 |
| Swamp | 38 | 26 | 29 | -3 | 12 |

Verdict: the commander set was chosen at the checkpoint on Swamp headroom under
an even-split estimate, and the risk recorded as A7 — that Wick would come out
black-primary and squeeze the second black seat — did not materialise. Wick's
Rat core in this collection is blue-heavy (Shoreline Looter, Thought Shucker,
Azure Beastbinder, Mindwhisker, Nightwhorl Hermit, Lightshell Duo) so the list
sits between blue and black, and every divergence in the table above is zero
or negative. The build order named by `check` was followed: Wick, then
Camellia, then Alania, then Finneas.

## The judged half

### Evasion

Not clustered on one deck, but not even either.

- **Wick** has the most ways past blockers: flyers Skyskipper Duo, Darkstar
  Augur, Maha, Its Feathers Night, Rapacious Dragon, Glidedive Duo, Bloodtithe
  Collector and Crow of Dark Tidings; unblockable or near-unblockable Rats in
  Shoreline Looter, Nightwhorl Hermit (at threshold), Azure Beastbinder, plus
  Long River Lurker and Gossip's Talent granting it; menace on Tidecaller
  Mentor and Thought-Stalker Warlock.
- **Camellia**'s evasion is one keyword on the whole team: menace from the
  commander, plus trample on Honored Dreyleader, Galewind Moose, Pest Mascot
  and Shopkeeper's Bane. Her only flyer is Glidedive Duo.
- **Alania** flies with Firespitter Whelp, Elemental Mascot and Spectacular
  Skywhale and otherwise wins through spells and pings.
- **Finneas** flies with Shrike Force, Inspiring Overseer, Dazzling Angel and
  Pileated Provisioner, grants it once with Feather of Flight, and goes wide on
  the ground.

Reach to hold the air: Finneas himself, Scrapshooter, Barkform Harvester and
Clifftop Lookout in Finneas; Scrapshooter, Barkform Harvester, Treetop
Sentries, Fecund Greenshell, Galewind Moose and Hivespine Wolverine's fight in
Camellia; Barkform Harvester in Wick and Alania. Camellia is the seat most
exposed to flyers and holds Pawpatch Formation and Glorious Decay against
them. If Wick's air force decides too many games, the first swap is Rapacious
Dragon for a ground Rat-adjacent body; the flyers that matter to Wick's plan
are Darkstar Augur and Maha.

### Interaction asymmetry

The counted spread above overstates the gap and understates one deck. The
checker counts pattern matches over oracle text (ADR-0009), and it misses fight
and conditional removal: Finneas's Longstalk Brawl, Polliwallop, Hunter's
Talent, Sonar Strike, Parting Gust and Prayer of Binding are real answers it
does not count, while Camellia's count includes artifact and enchantment
removal (Scrapshooter, Reclamation Sage, Hivespine Wolverine, Bumbleflower's
Sharepot, Witherbloom Charm). Read the four counts as "creature and permanent
removal the pattern recognises", not as total interaction.

Stack interaction is where the real asymmetry is, and it is a colour fact:
only Wick and Alania are blue. Alania holds Negate, Essence Scatter, Dazzling
Denial and Spellgyre; Wick holds one Dazzling Denial; Camellia and Finneas have
none. This is the shape gen 1's review flagged, at half the size. It was left
in because Alania is the deck whose plan is spells, and because the two
sweepers (Brotherhood's End, Splatter Technique) also had to live there — all
three sweepers the collection owns are red, and Wick's small-creature board
does not want them. Wildfire Howl, the third, was left out of every deck on
purpose: it kills Alania's own Otters and Wick's Rats.

Verdict: acceptable for a symmetric pod where the pilot of Alania is the owner
(see piloting load). If the counters feel oppressive to the cold pilots, the
first change is Negate out of Alania for a fourth bounce spell (Griptide is
owned), which keeps her answers but makes them tempo rather than denial.

### Piloting load

Ordered from easiest to hardest, for the three friends who pick a deck up cold
(A10):

1. **Finneas** — play creatures, attack with Finneas every turn, count to
   ten. The playbook's only real decisions are when to hold Dawn's Truce and
   whether to promise the gift on Parting Gust.
2. **Camellia** — one recurring decision: forage by exiling three or by
   sacrificing a Food, and when. Removal choices are plentiful but forgiving.
3. **Wick** — three colours, a graveyard threshold to track, a Snail to time,
   and hand-attack targeting. Medium-hard; the playbook carries it.
4. **Alania** — the copy trigger is optional per spell and asks who should
   draw; counters need holding; a copy is not a cast. Recommended for the
   owner, or for the most experienced guest.

If a guest wants Alania, the one rule that prevents most mistakes: copy draw
spells and removal, skip the trigger when the copy is worth less than the card
you would give.

### Speed and shape

Finneas is on the table on turn two, Camellia on three, Wick on four, Alania on
five, and the average mana values in the spread table run in the same order.
Expect Finneas and Camellia to apply the early pressure and Wick and Alania to
take over once their engines are online. Alania in particular has to survive to
five mana with the fewest creatures at the table; her bounce spells and the two
sweepers are what buy that time, and the cold pilots should expect her to be
the target early if she draws well.

### Ramp

Wick and Alania report ramp far under the house target, and only part of that is
the collection's ceiling. The ramp pattern strips reminder text (ADR-0009), so a
card that makes a Treasure token is not counted: Rapacious Dragon, Corsair
Captain, Seize the Spoils and Fountainport in Wick, Blooming Blast in Alania.
Both lists are on 36 lands with mana rocks and creatures the checker does
see. Not a change; a note for the reader of the counts.

### Bracket and combos

Vampiric Tutor, the one Game Changer owned, is in no deck. The checker found no
extra-turn card and no mass land denial. A8 (two-card infinite combos absent) is
judgment, not a check: I read the four lists for loops and found none. Wick's
engine is one Snail per sacrifice, Alania's copies are capped at three a turn,
Camellia's Squirrel tokens need a Food each, and Finneas's counters are once per
attack.

### Physical cards

The four decks are disjoint in physical cards, which `check` enforces by name
against the export; every pinned printing in the deck files is one the export
holds, and no printing is pinned more times than it is owned. Three Tree Mascot
is owned three times and sits in Wick, Camellia and Finneas; Alania has none,
which is the one allocation a future table might revisit.

## What I would change after the first session

- If Alania's counters decide games: Negate for Griptide (tempo, not denial).
- If Wick's flyers decide games: Rapacious Dragon for a ground body.
- If Camellia loses to the air: Plummet is owned twice and Finneas holds one.
- If Finneas runs out of cards: Fountainport and Heirloom Epic are in; Rapier
  Wit and Follow the Lumarets are the next draw effects in green-white.
- Balance thresholds stay unset until a game has been played (ADR-0010).
