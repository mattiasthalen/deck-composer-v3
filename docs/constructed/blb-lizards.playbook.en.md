# BLB Lizards — playbook

Deck file: `decks/constructed/blb-lizards.deck.txt`. Colours: black-red.
Constructed, built to play against `decks/constructed/blb-frogs.deck.txt`.
`check` does not read constructed decks (ADR-0013), so no figure here is
measured; every number below is printed on a card.

## What the deck is

An aggressive Lizard deck that goes for the opponent's life total. Cheap
creatures attack from turn one, and a second stream of damage never touches
combat: Kindlespark Duo pings, Agate-Blade Assassin and Glidedive Duo drain,
Steampath Charger pings when it dies, Gev, Scaled Scorch pings whenever you cast
a Lizard, and Hearthborn Battler hits whenever a player casts their second spell
in a turn. Many Lizards get better once an opponent has lost life this turn:
Cindering Cutthroat and Frilled Sparkshooter enter with a +1/+1 counter,
Flamecache Gecko refunds {B}{R}, Thought-Stalker Warlock lets you pick the
discard, and Gev puts an extra counter on every other creature that enters under
your control. Take Out the Trash, Savor and Nocturnal Hunger clear blockers;
Reptilian Recruiter borrows one for the last attack. Both colours matter from
turn one: Ravine Raider is black, Steampath Charger red, Gev both.

Words on the cards:

- **An opponent lost life this turn.** Any loss counts — damage or "loses life"
  — even if they gained life back afterwards. It starts over every turn.
- **Menace.** It can't be blocked except by two or more creatures. Ravine
  Raider, Thought-Stalker Warlock and Frilled Sparkshooter have it; Cindering
  Cutthroat gains it for {1}{B/R}, which you must activate before blockers are
  declared.
- **Reach** (Frilled Sparkshooter) can block flyers. **Flying** (Glidedive Duo)
  can be blocked only by flyers and reach. **Trample** (Reptilian Recruiter):
  combat damage beyond what kills its blockers goes to the player. **Haste**
  (Hearthborn Battler): it can attack the turn it arrives.
- **Offspring {2}** (Steampath Charger). Pay {2} more as you cast it and you also
  get a 1/1 token copy when it enters. The copy is a Lizard and pings when it
  dies too, but it was not cast, so Gev does not trigger for it.
- **Gift a Food** (Nocturnal Hunger). As you cast it you may promise the
  opponent a Food; if you don't, you lose 2 life. A Food is an artifact token:
  {2}, {T}, sacrifice it: gain 3 life. Savor makes one for you.
- **Ward — pay 2 life** (Gev). A spell or ability an opponent aims at Gev is
  countered unless they pay 2 life.
- **Hybrid mana.** Cindering Cutthroat's {B/R} is paid with either colour.
- Kindlespark Duo is a Lizard Otter and Glidedive Duo a Bat Lizard: both are
  Lizards.
- Take Out the Trash's Raccoon clause never applies: neither deck has a Raccoon.

## How to pilot it

1. Keep a hand with two to four lands and at least two creatures that cost one
   or two. Mulligan slow hands: the Frogs get stronger every turn the game
   lasts.
2. Turn one Ravine Raider; turn two Agate-Blade Assassin, Steampath Charger or
   Gev; turn three Kindlespark Duo or Cindering Cutthroat. Attack every turn the
   Frogs cannot block well: with menace, each attacker needs two of their
   creatures.
3. Make them lose life first, then cast. Attack, then cast Cindering Cutthroat,
   Frilled Sparkshooter, Flamecache Gecko and Thought-Stalker Warlock after
   combat — they could not attack this turn anyway. Or ping with Kindlespark Duo
   before you cast. Flamecache Gecko's {B}{R} is gone at the end of the phase:
   spend it on the next creature right away.
4. Gev is the best two-drop. With him out, each Lizard you cast pings the
   opponent before it enters, so it enters with Gev's extra counter, and
   Cindering Cutthroat or Frilled Sparkshooter with their own as well. Offspring
   on Steampath Charger then makes two Lizards that both get the counter.
5. Kindlespark Duo pings once per untap, and each instant you cast untaps it for
   another. Ping in your own main phase when you want the bonuses this turn;
   otherwise wait for the end of the Frogs' turn, so it can block first.
6. Removal is for blockers. Kill Long River Lurker first: it gives every Frog
   ward {1}, so each spell aimed at a Frog costs {1} more while it lives — and it
   has ward itself. Then Lilysplash Mentor, which re-uses their best creature
   every turn, and Three Tree Scribe, which grows their team. Nocturnal Hunger is
   the answer to the big Frogs; Take Out the Trash and Savor handle the small
   ones.
7. Thought-Stalker Warlock after they lost life: you see their hand and take the
   card that hurts you most, usually Polliwallop.
8. Finish. Reptilian Recruiter takes their best blocker until end of turn and
   attacks with it. Glidedive Duo drains 2, Hearthborn Battler hits for 2 when
   you cast your second spell in a turn, and Valley Flamecaller makes each of
   your Lizards' damage 1 higher — combat, Kindlespark Duo, Gev, Hearthborn
   Battler and Steampath Charger alike. Count that damage before you commit.
   Ravine Raider takes spare black mana: {1}{B} for +1/+1.
9. Nocturnal Hunger: you are the attacker, so your life matters less than
   theirs. Take the 2 life loss rather than give them a Food, unless you are the
   one close to dying.

## What to watch

- The Frogs pull ahead in a long game: Pond Prophet, Bellowing Crier and
  Dreamdew Entrancer draw cards, and every bounce or flicker uses one of them
  again. Press early.
- Polliwallop is an instant and cheap with Frogs out: any attacker can be hit
  mid-combat, and their creature takes no damage. Dire Downdraft is {1} cheaper
  against an attacking or tapped creature — a tapped Kindlespark Duo is a cheap
  target. You choose whether the creature goes on top of your library or at the
  bottom; on top, you draw it again next turn instead of a new card.
- Dreamdew Entrancer taps a creature and puts three stun counters on it; each
  time it would untap, a counter comes off instead. On Kindlespark Duo, each
  instant you cast removes one.
- Their reach — Stickytongue Sentinel, Lilysplash Mentor, Dreamdew Entrancer —
  and Skyskipper Duo's flying stop Glidedive Duo. Their flyers: Skyskipper Duo,
  and Waterspout Warden when another creature entered under their control that
  turn. Frilled Sparkshooter has reach.
- Long River Lurker's ward also catches Reptilian Recruiter's trigger: keep {1}
  spare, or kill the Lurker first.
- Treeguard Duo gives one attacker +X/+X and vigilance, X being the number of
  creatures they control: a wide Frog board can hit hard out of nowhere. Keep a
  blocker back against one.
- Hearthborn Battler triggers on every player's second spell each turn, theirs
  included, and always hits the opponent.
