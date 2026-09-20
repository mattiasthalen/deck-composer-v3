from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from deck_composer import facts as facts_module
from deck_composer import manabox, scryfall
from deck_composer.facts import CardFacts
from tests.helpers import EXPORT, FakeScryfall


@pytest.fixture
def export() -> manabox.Export:
    return manabox.read_export(EXPORT, display="collection.csv")


@pytest.fixture
def transport() -> FakeScryfall:
    return FakeScryfall()


@pytest.fixture
def card_facts(tmp_path: Path, export: manabox.Export, transport: FakeScryfall) -> CardFacts:
    result = facts_module.refresh(
        export,
        tmp_path / "card_facts.json",
        client=scryfall.Client(transport=transport, sleep=lambda _: None),
        today=date(2026, 9, 20),
    )
    return result.facts
