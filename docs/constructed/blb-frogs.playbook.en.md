# BLB Frogs — playbook

Deck file: `decks/constructed/blb-frogs.deck.txt`. Colours: green-blue.
Constructed, built to play against `decks/constructed/blb-lizards.deck.txt`.
`check` does not read constructed decks (ADR-0013), so no figure here is
measured; every number below is printed on a card.

## What the deck is

A Frog deck that wins by making its creatures enter the battlefield again and
again. Most of them do something when they enter: Pond Prophet draws a card,
Bellowing Crier draws and then discards, Sunshower Druid puts a +1/+1 counter on
a creature and gains you 1 life, Dreamdew Entrancer locks a creature down with
stun counters, Treeguard Duo pumps an attacker. The rest of the deck makes them
enter again. Mistbreath Elder and Stickytongue Sentinel return a creature to your
hand to cast again; Lilysplash Mentor, Skyskipper Duo and Long River Lurker exile
one and return it. Three Tree Scribe puts a +1/+1 counter on one of your
creatures every time that happens. Removal is Polliwallop, Longstalk Brawl and
Dire Downdraft. Green is the main colour; blue brings the card draw, the flyers
and the flicker.

Words on the cards:

- **Enters.** "When this creature enters" triggers every time it enters the
  battlefield: when you cast it, when it comes back from exile, when you cast it
  again after a bounce.
- **Bounce.** Return a permanent to its owner's hand. Mistbreath Elder's is not
  optional: at your upkeep, if you control another creature, you must return
  one. Only when the Elder is your sole creature may you return it instead, or
  keep it.
- **Flicker.** Exile a creature and return it. It comes back as a new creature:
  untapped, without its old counters, unable to attack this turn, and what it
  does when it enters happens again.
- **Leaves the battlefield without dying** (Three Tree Scribe). Dying means
  going to the graveyard. A bounce or a flicker counts, and the Scribe triggers
  for itself too.
- **Reach** can block flyers. **Flying** can be blocked only by flyers and
  reach. **Vigilance**: attacking does not tap it, so it can still block.
- **Ward {1}.** When an opponent targets it with a spell or ability, that spell
  or ability is countered unless they pay {1}. Long River Lurker has it and gives
  it to every other Frog.
- **Stun counter.** When the creature would untap, a stun counter is removed
  instead. Dreamdew Entrancer's three keep a creature tapped through three untap
  steps.
- **Affinity for Frogs** (Polliwallop). It costs {1} less for each Frog you
  control; only the generic part shrinks, so {G} is the floor.
- **Gift a tapped Fish** (Longstalk Brawl). As you cast it you may promise the
  opponent the gift: they create a tapped 1/1 blue Fish, and your creature gets a
  +1/+1 counter before the fight.
- **Fight.** Each creature deals damage equal to its power to the other.
  Polliwallop is not a fight: only your creature deals damage, twice its power,
  and it takes none.
- **Hybrid mana.** Pond Prophet's {G/U} is paid with either colour.
- Skyskipper Duo is a Bird Frog and Treeguard Duo a Frog Rabbit: both count as
  Frogs.

## How to pilot it

1. Keep a hand with two to four lands and a creature that costs one or two.
   Green matters first. Sunshower Druid and Mistbreath Elder are the one-drops;
   Pond Prophet, Three Tree Scribe and Bellowing Crier the two-drops.
2. The early turns are for bodies. The Lizards attack from turn one with
   creatures that need two blockers each; a board of small Frogs is what stops
   them. Sunshower Druid's counter can go on itself.
3. The basic loop: Mistbreath Elder or Stickytongue Sentinel returns Pond
   Prophet or Sunshower Druid to your hand, you cast it again, and what it does
   when it enters happens again. The Elder grows each time, and Three Tree
   Scribe adds a counter.
4. Cast creatures before combat. Waterspout Warden flies only if another
   creature entered under your control this turn; Treeguard Duo's pump and Long
   River Lurker's "can't be blocked" are meant for the attack that follows.
5. Long River Lurker: make Dreamdew Entrancer or Stickytongue Sentinel
   unblockable. After it deals combat damage, flicker it: it comes back
   untapped to block, and what it does when it enters happens again.
6. Lilysplash Mentor is the engine from four mana. Each turn, after combat, pay
   {1}{G}{U} to flicker your best enter creature: it returns with a +1/+1
   counter and does its thing again — Pond Prophet draws, Dreamdew Entrancer
   stuns another creature. Flicker before combat and that creature cannot
   attack. Skyskipper Duo does the same once: cast it after combat and the
   creature it exiles is back at the end of the turn.
7. Removal. Polliwallop is the main answer and an instant: with three Frogs out
   it costs {G}. Let your biggest creature deal the damage. Longstalk Brawl is a
   one-mana fight; promise the gift when the extra counter decides it. Dire
   Downdraft costs {1} less against an attacking or tapped creature: cast it
   during the Lizards' attack, or on a Kindlespark Duo that has just pinged you.
8. Finish with Treeguard Duo: one attacker gets +X/+X and vigilance, where X is
   the number of creatures you control, the Duo included. The Duo entering also
   makes Waterspout Warden fly this turn — pump the Warden and send it over the
   top. Only Frilled Sparkshooter and Glidedive Duo can block your flyers.
9. Mistbreath Elder must return another creature at each of your upkeeps if you
   control one. Keep a cheap enter creature on the battlefield for it — Pond
   Prophet, Sunshower Druid, Bellowing Crier — or it returns one of your big
   ones.

## What to watch

- The Lizards get damage through without combat: Kindlespark Duo pings,
  Agate-Blade Assassin and Glidedive Duo drain, Steampath Charger pings when it
  dies, Gev, Scaled Scorch pings whenever they cast a Lizard, Hearthborn
  Battler hits for 2 on second spells. Count that damage before you take a hit
  you could have blocked.
- Kill first: Valley Flamecaller (each of their Lizards' damage is 1 higher,
  pings included), Kindlespark Duo (a ping every turn, and another after each
  instant they cast), Gev (each Lizard they cast pings you and enters bigger).
  Gev has ward — pay 2 life: targeting him costs you 2 life.
- Menace: block with two creatures or not at all. Cindering Cutthroat can gain
  menace for {1}{B/R}, but only before you declare blockers.
- Do not stun Kindlespark Duo: its untap trigger removes a stun counter each
  time they cast an instant. Stun a big attacker or the reach blocker, Frilled
  Sparkshooter. With no good target, stun your own Pond Prophet to draw two,
  then bounce or flicker it to clear the counters.
- Hearthborn Battler deals 2 damage to you whenever any player casts their
  second spell in a turn — you included. While it is out, cast one spell a turn
  unless the second is worth 2 life.
- Reptilian Recruiter takes one of your creatures until end of turn, untapped
  and with haste. While Long River Lurker is out, the Lizards pay {1} more for
  that and for every removal spell aimed at a Frog.
- Their removal: Take Out the Trash (3 damage), Savor (-2/-2), Nocturnal Hunger
  (destroy). Nocturnal Hunger may come with a Food for you as the gift: {2},
  {T}, sacrifice it: gain 3 life.
- Your own bounce and flicker wipe counters. A creature grown by Sunshower Druid
  or Three Tree Scribe loses them when it leaves; Lilysplash Mentor gives back
  only one.
