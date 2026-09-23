"""Owns the Scryfall surface and the projection from an API object to a record.

Access rules are inherited from gen 2's ADR-0004, which this project adopts
wholesale: the collection endpoint only, never bulk files; at most 75 identifiers
per request; one request at a time, 100 ms apart; an identifying User-Agent; back
off on 429.

The projection is a whitelist. Prices, purchase links and images never pass.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from deck_composer.errors import ToolError

API = "https://api.scryfall.com"
COLLECTION_URL = f"{API}/cards/collection"
REPOSITORY = "https://github.com/mattiasthalen/deck-composer-v3"
BATCH = 75
SPACING = 0.1
TIMEOUT = 30.0
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
ATTEMPTS = 2

CARD_LAYOUTS = frozenset(
    {
        "normal", "split", "flip", "transform", "modal_dfc", "meld", "leveler",
        "class", "case", "saga", "adventure", "mutate", "prototype", "battle",
        "prepare", "reversible_card", "augment", "host",
    }
)  # fmt: skip
TOKEN_LAYOUTS = frozenset(
    {"token", "double_faced_token", "emblem", "art_series", "planar", "scheme", "vanguard"}
)
TOKEN_SET_TYPE = "token"
LEGALITIES = frozenset({"legal", "not_legal", "banned", "restricted"})

Transport = Callable[[str, str, dict[str, str], bytes], tuple[int, bytes]]


@dataclass(frozen=True, slots=True)
class Printing:
    scryfall_id: str
    set: str
    set_type: str
    collector_number: str
    rarity: str
    released_at: str


@dataclass(frozen=True, slots=True)
class Face:
    name: str
    mana_cost: str | None
    type_line: str | None
    colors: tuple[str, ...] | None
    oracle_text: str | None


@dataclass(frozen=True, slots=True)
class Card:
    """A card's Scryfall facts. Ownership is attached later, by the facts module."""

    name: str
    oracle_id: str
    layout: str
    type_line: str
    mana_cost: str | None
    cmc: float
    colors: tuple[str, ...] | None
    color_identity: tuple[str, ...]
    produced_mana: tuple[str, ...] | None
    oracle_text: str | None
    keywords: tuple[str, ...]
    legality: str
    game_changer: bool
    edhrec_rank: int | None
    faces: tuple[Face, ...] | None
    printings: tuple[Printing, ...] = ()


@dataclass(frozen=True, slots=True)
class Token:
    """A token. Kept apart from cards because eight token lots share a card's name."""

    oracle_id: str
    name: str
    layout: str
    type_line: str
    oracle_text: str | None
    printings: tuple[Printing, ...] = ()


def urllib_transport(
    method: str, url: str, headers: dict[str, str], body: bytes
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body or None, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except OSError as exc:
        raise ToolError(
            "scryfall_unreachable",
            {"reason": str(exc)},
            "Check the network, then run refresh again.",
        ) from exc


@dataclass
class Client:
    """One request at a time, spaced, with an identifying User-Agent."""

    transport: Transport | None = None
    sleep: Callable[[float], None] = time.sleep
    version: str = "unknown"
    requests: int = field(default=0, init=False)

    def _headers(self, *, body: bool) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": f"deck-composer/{self.version} (+{REPOSITORY})",
        }
        if body:
            headers["Content-Type"] = "application/json"
        return headers

    def _send(self, method: str, url: str, payload: Mapping[str, Any] | None) -> Any:
        body = json.dumps(payload).encode() if payload is not None else b""
        for attempt in range(ATTEMPTS):
            if self.requests:
                self.sleep(SPACING)
            self.requests += 1
            # Resolved per call, not bound at class definition, so the module
            # attribute stays patchable and a test cannot reach the network by
            # accident.
            send = self.transport or urllib_transport
            status, raw = send(method, url, self._headers(body=bool(body)), body)
            if status in RETRY_STATUSES and attempt + 1 < ATTEMPTS:
                continue
            if status == 404:
                return None
            if status != 200:
                raise ToolError(
                    "scryfall_error",
                    {"status": status, "endpoint": url.split("?")[0]},
                    "Retry; if it persists, check https://scryfall.com/docs/api.",
                )
            try:
                return json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ToolError(
                    "scryfall_unparseable",
                    {"endpoint": url.split("?")[0]},
                    "Retry; Scryfall returned something that is not JSON.",
                ) from exc
        raise ToolError(
            "scryfall_error",
            {"endpoint": url.split("?")[0]},
            "Scryfall kept returning a retryable status; try again later.",
        )

    def collection(
        self, identifiers: Sequence[Mapping[str, str]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch up to any number of identifiers, 75 per request. Returns (found, missing)."""
        found: list[dict[str, Any]] = []
        missing: list[dict[str, Any]] = []
        for start in range(0, len(identifiers), BATCH):
            chunk = [dict(entry) for entry in identifiers[start : start + BATCH]]
            payload = self._send("POST", COLLECTION_URL, {"identifiers": chunk})
            if payload is None:
                missing.extend(chunk)
                continue
            found.extend(payload.get("data", []))
            missing.extend(payload.get("not_found", []))
        return found, missing


# --- the projection ---------------------------------------------------------


def is_token(obj: Mapping[str, Any]) -> bool:
    """A printing in a token set is a token, whatever layout Scryfall gives it.

    Gen 2 learned this the hard way (its ADR-0008): the Role token
    "Monster // Sorcerer" has layout `flip`, and dungeons have layout `normal`.
    """
    layout = obj.get("layout")
    if layout not in TOKEN_LAYOUTS and layout not in CARD_LAYOUTS:
        raise ToolError(
            "layout_unknown",
            {"layout": layout, "card": obj.get("id") or obj.get("name")},
            "Add the layout to CARD_LAYOUTS or TOKEN_LAYOUTS in scryfall.py.",
        )
    return layout in TOKEN_LAYOUTS or obj.get("set_type") == TOKEN_SET_TYPE


def project(obj: Mapping[str, Any]) -> Card | Token:
    printing = _printing(obj)
    if is_token(obj):
        return Token(
            oracle_id=_oracle_id(obj),
            name=_text(obj, "name"),
            layout=_text(obj, "layout"),
            type_line=obj.get("type_line") or "",
            oracle_text=obj.get("oracle_text"),
            printings=(printing,),
        )
    legality = (obj.get("legalities") or {}).get("commander")
    if legality not in LEGALITIES:
        raise ToolError(
            "legality_unknown",
            {"legality": legality, "card": obj.get("id") or obj.get("name")},
            "Add the value to LEGALITIES in scryfall.py.",
        )
    return Card(
        name=_text(obj, "name"),
        oracle_id=_oracle_id(obj),
        layout=_text(obj, "layout"),
        type_line=obj.get("type_line") or "",
        mana_cost=obj.get("mana_cost"),
        cmc=_cmc(obj.get("cmc")),
        colors=_tuple(obj.get("colors")),
        color_identity=_tuple(obj.get("color_identity")) or (),
        produced_mana=_tuple(obj.get("produced_mana")),
        oracle_text=obj.get("oracle_text"),
        keywords=_tuple(obj.get("keywords")) or (),
        legality=legality,
        game_changer=bool(obj.get("game_changer", False)),
        edhrec_rank=_rank(obj.get("edhrec_rank")),
        faces=_faces(obj),
        printings=(printing,),
    )


def project_all(objects: Iterable[Mapping[str, Any]]) -> list[Card | Token]:
    return [project(obj) for obj in objects]


def _printing(obj: Mapping[str, Any]) -> Printing:
    return Printing(
        scryfall_id=_text(obj, "id"),
        set=_text(obj, "set"),
        set_type=obj.get("set_type") or "",
        collector_number=_text(obj, "collector_number"),
        rarity=obj.get("rarity") or "",
        released_at=obj.get("released_at") or "",
    )


def _text(obj: Mapping[str, Any], key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value:
        raise ToolError(
            "payload_invalid",
            {"field": key, "card": obj.get("id") or obj.get("name")},
            "Scryfall returned a card without a required field; retry the refresh.",
        )
    return value


def _oracle_id(obj: Mapping[str, Any]) -> str:
    value = obj.get("oracle_id")
    if isinstance(value, str) and value:
        return value
    for face in obj.get("card_faces") or ():  # reversible_card carries it per face
        if isinstance(face, dict) and isinstance(face.get("oracle_id"), str):
            return face["oracle_id"]
    return _text(obj, "oracle_id")


def _tuple(value: Any) -> tuple[str, ...] | None:
    return tuple(value) if isinstance(value, list) else None


def _cmc(value: Any) -> float:
    number = float(value or 0)
    return int(number) if number.is_integer() else number


def _rank(value: Any) -> int | None:
    """Two significant figures, so a refresh does not rewrite every line."""
    if not isinstance(value, int):
        return None
    digits = len(str(value))
    if digits <= 2:
        return value
    step = 10 ** (digits - 2)
    return (value + step // 2) // step * step


def _faces(obj: Mapping[str, Any]) -> tuple[Face, ...] | None:
    faces = obj.get("card_faces")
    if not isinstance(faces, list) or len(faces) < 2:
        return None
    return tuple(
        Face(
            name=_text(face, "name"),
            mana_cost=face.get("mana_cost"),
            type_line=face.get("type_line"),
            colors=_tuple(face.get("colors")),
            oracle_text=face.get("oracle_text"),
        )
        for face in faces
    )
