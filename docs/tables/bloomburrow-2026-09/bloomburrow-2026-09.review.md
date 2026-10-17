# Table review — bloomburrow-2026-09

The one table-level document (ADR-0010). Commanders: Vren, the Relentless, Camellia, the Seedmiser, Alania, Divergent Storm, Finneas, Ace Archer. Bracket 2.

Vren replaced Wick, the Whorled Mind on 2026-10-17 at the owner's request. The
owner chose the commander (ADR-0008); the seat was rebuilt from the pool, with
most of Wick's blue and black cards moving across. Camellia, Alania and Finneas
are unchanged.

`check` over the four deck files: `passed` True, `table.passed` True, no
violations. Snapshot: export `sha256:c0d0c4a373549035252081aea7f40ef730b5d3e6e3609fc38ecbc3fff486ed5c`, card facts refreshed 2026-10-04,
bracket rules 2026-09-20 (`sha256:2de25d1be64d5fabf70085b84d3432c4fa9dffd65cd5513d89aa96a35f264dae`), house targets 2026-09-20.
Every number in this document and in the eight playbooks is that run's output,
rendered into the prose, never retyped. The judged findings below name cards
rather than counts, because a count I made would be a fact the builder asserts
about its own picks (ADR-0002).

House targets for reference: draw 10, ramp 10, targeted interaction 8, sweepers 2; lands 35–37; average mana value 2.5–3.2.

## The measured table

| Commander | CI | Lands | Creatures | Avg MV | Tribal core (type+text of ceiling) | Draw (ceiling) | Ramp (ceiling) | Interaction (ceiling) | Sweepers (ceiling) |
|---|---|---|---|---|---|---|---|---|---|
| Vren, the Relentless | UB | 36 | 24 | 2.91 | 10+2=12 of 16 | 8 (49) | 4 (8) | 27 (44) | 0 (0) |
| Camellia, the Seedmiser | BG | 36 | 33 | 2.78 | 12+3=15 of 15 | 10 (31) | 10 (26) | 15 (38) | 0 (0) |
| Alania, Divergent Storm | UR | 36 | 26 | 2.97 | 10+7=17 of 18 | 21 (57) | 4 (19) | 12 (35) | 2 (4) |
| Finneas, Ace Archer | WG | 35 | 33 | 2.75 | 12+5=17 of 17 | 13 (27) | 7 (27) | 10 (23) | 0 (0) |

### The four spreads

Stated as ADR-0010 requires; no threshold on any axis.

| Axis | Values (alania, camellia, finneas, vren) | Min | Max | Spread |
|---|---|---|---|---|
| Land count | 36 / 36 / 35 / 36 | 35 | 36 | 1 |
| Average mana value | 2.97 / 2.78 / 2.75 / 2.91 | 2.75 | 2.97 | 0.22 |
| Creature count | 26 / 33 / 33 / 24 | 24 | 33 | 9 |
| Targeted interaction | 12 / 15 / 10 / 27 | 10 | 27 | 17 |

### The basic budget, estimate against measurement (ADR-0005)

Basis: measured from the lists. Overcommitted: none. Basics the estimate was
generous for: none.

| Basic | Owned | Used | Estimated | Divergence | Remaining |
|---|---|---|---|---|---|
| Forest | 54 | 31 | 35 | -4 | 23 |
| Island | 50 | 32 | 35 | -3 | 18 |
| Mountain | 42 | 14 | 18 | -4 | 28 |
| Plains | 40 | 16 | 18 | -2 | 24 |
| Swamp | 39 | 30 | 35 | -5 | 9 |

Verdict: every divergence is negative, so the estimate stayed on the safe side.
Swamp is still the tightest basic, now with 9 spare. Vren is a two-colour seat
on 15 Swamp against Wick's 11; dropping red freed seven Mountains.

## The judged half

### Evasion

Not clustered on one deck, but not even either.

- **Vren** flies with Moonstone Harbinger, Glidedive Duo, Starlit Soothsayer,
  Starscape Cleric, Deep-Cavern Bat, Spectral Sailor,
  Plumecreed Escort and Maha, Its Feathers Night. Its unblockable or
  near-unblockable Rats are Shoreline Looter, Nightwhorl Hermit (at threshold)
  and Azure Beastbinder, with menace on Tidecaller Mentor and Thought-Stalker
  Warlock.
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
Camellia; Barkform Harvester in Vren and Alania. Camellia is the seat most
exposed to flyers and holds Pawpatch Formation and Glorious Decay against
them. Vren's flyers are mostly small; the one that decides games is Maha.

### Interaction asymmetry

The counted spread grew with this change, and it is real. Vren is a removal
deck: its commander turns every creature it kills into a Rat, so the seat was
built to hold the most answers at the table. The checker counts pattern matches
over oracle text (ADR-0009) and misses fight and conditional removal:
Finneas's Longstalk Brawl, Polliwallop, Hunter's Talent, Sonar Strike, Parting
Gust and Prayer of Binding are real answers it does not count, while Camellia's
count includes artifact and enchantment removal (Scrapshooter, Reclamation
Sage, Hivespine Wolverine, Bumbleflower's Sharepot, Witherbloom Charm). Read
the four counts as "creature and permanent removal the pattern recognises",
not as total interaction. Even so, Vren holds roughly twice what any other
seat does.

Stack interaction is a colour fact: only Vren and Alania are blue. Alania holds
Negate, Essence Scatter, Dazzling Denial and Spellgyre. Vren holds Essence
Scatter, Long River's Pull, Cancel, Devious Cover-Up and Spellgyre. Camellia and Finneas have none. With Wick, this was one blue deck
holding counters; now it is two, and Vren holds one more.
The two sweepers (Brotherhood's End, Splatter Technique) stay in Alania; every
sweeper the collection owns is red, so Vren's sweeper ceiling is zero.

Verdict: Vren is the seat most likely to feel oppressive to cold pilots,
because it answers nearly everything one card at a time and gets a body for
each answer. That was the owner's intent: the deck was built to beat a
ramp-into-huge-creatures opponent outside this table. If it dominates the pod,
the first change is to cut counters (Cancel, Devious Cover-Up) for Rat bodies.
Alania's counters are unchanged; Negate out for Griptide is still the first
swap if hers dominate.

### Piloting load

Ordered from easiest to hardest, for the three friends who pick a deck up cold
(A10):

1. **Finneas** — play creatures, attack with Finneas every turn, count to
   ten. The playbook's only real decisions are when to hold Dawn's Truce and
   whether to promise the gift on Parting Gust.
2. **Camellia** — one recurring decision: forage by exiling three or by
   sacrificing a Food, and when. Removal choices are plentiful but forgiving.
3. **Vren** — two colours and a simple engine, but most turns ask whether to
   hold mana for a counter or spend it on removal, and which answer fits which
   threat. Medium; the playbook carries it.
4. **Alania** — the copy trigger is optional per spell and asks who should
   draw; counters need holding; a copy is not a cast. Recommended for the
   owner, or for the most experienced guest.

If a guest wants Alania, the one rule that prevents most mistakes: copy draw
spells and removal, skip the trigger when the copy is worth less than the card
you would give.

### Speed and shape

Finneas is on the table on turn two, Camellia on three, Vren on four, Alania on
five. The average mana values in the spread table put Finneas and Camellia
lightest and Alania heaviest, with Vren just under her.
Expect Finneas and Camellia to apply the early pressure and Vren and Alania to
take over later: Vren by grinding the board down into Rats, Alania once her
engine is online. Alania still has to survive to five mana with the fewest
creatures at the table; her bounce spells and the two sweepers buy that time.

### Ramp

Vren and Alania report ramp far under the house target, and much of that is
the collection's ceiling: blue-black can field 8. The ramp pattern strips
reminder text (ADR-0009), so a card that makes a Treasure token is not counted
— Blooming Blast in Alania. Both lists are on 36 lands. Not a change; a note
for the reader of the counts.

### Bracket and combos

Vampiric Tutor, the one Game Changer owned, is in no deck. The checker found no
extra-turn card and no mass land denial. A8 (two-card infinite combos absent) is
judgment, not a check: I read the four lists for loops and found none. Vren's
Rats come one per creature exiled, Alania's copies are capped at three a turn,
Camellia's Squirrel tokens need a Food each, and Finneas's counters are once per
attack.

### Physical cards

The four decks are disjoint in physical cards, which `check` enforces by name
against the export; every pinned printing in the deck files is one the export
holds, and no printing is pinned more times than it is owned. Three Tree Mascot
is owned three times and sits in Vren, Camellia and Finneas; Alania has none.
Five cards Wick had and Vren wanted are single copies already in Camellia or
Alania (Bitter Triumph, Consumed by Greed, Curse of the Swine, Huskburster
Swarm, Osteomancer Adept); they stayed where they were.

Fountainport is in Vren. The export of 2026-10-04 records one, and Finneas
still runs Rapier Wit in the slot it once held.

## What I would change after the first session

- If Vren's answers decide games: Cancel and Devious Cover-Up out for Rats.
- If Alania's counters decide games: Negate for Griptide (tempo, not denial).
- If Camellia loses to the air: Plummet is owned twice and Finneas holds one.
- If Finneas runs out of cards: Heirloom Epic and Rapier Wit are in; Follow the
  Lumarets is the next draw effect in green-white.
- Balance thresholds stay unset until a game has been played (ADR-0010).
