"""Regression tests for shared UNIT3D book upload payloads."""

# ruff: noqa: S101

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.meta import Meta
from src.trackers.UNIT3D import UNIT3D
from src.trackers.UNIT3D.dreadvault import DreadVault
from src.trackers.UNIT3D.seedpool import Seedpool


@pytest.fixture(params=[DreadVault, Seedpool])
def tracker(request, monkeypatch):
    instance = request.param({"DEFAULT": {}, "TRACKERS": {}})
    monkeypatch.setattr(instance, "get_description", AsyncMock(return_value={"description": "Description"}))
    monkeypatch.setattr(instance, "get_mediainfo", AsyncMock(return_value={"mediainfo": ""}))
    return instance


@pytest.mark.parametrize(
    ("openlibrary", "openlibrary_id", "openlibrary_book_id", "expected_id"),
    [
        ("OL123W", "OL456W", "OL789W", "OL123W"),
        (None, "OL456W", "OL789W", "OL456W"),
        ("", None, "OL789W", "OL789W"),
    ],
)
@pytest.mark.parametrize(("isbn", "extra_ids"), [("9780765377067", "OL321W,OL654W"), (None, None)])
def test_book_payload_includes_openlibrary_identifiers(tracker, openlibrary, openlibrary_id, openlibrary_book_id, expected_id, isbn, extra_ids):
    meta = Meta(category="BOOK", type="EPUB", isbn=isbn)
    expected = asyncio.run(tracker.get_data(meta))
    meta.openlibrary = openlibrary
    meta.openlibrary_id = openlibrary_id
    meta.openlibrary_book_id = openlibrary_book_id
    meta.extra_openlibrary_ids = extra_ids

    expected.update(
        {
            "book_exists_on_openlibrary": "1",
            "openlibrary_book_id": expected_id,
            "openlibrary_isbn": isbn or "",
            "extra_openlibrary_ids": extra_ids or "",
        }
    )

    assert asyncio.run(tracker.get_data(meta)) == expected


@pytest.mark.parametrize("missing_id", [None, ""])
def test_book_payload_without_openlibrary_id_keeps_fields_absent(tracker, missing_id):
    meta = Meta(
        category="BOOK",
        type="EPUB",
        openlibrary=missing_id,
        openlibrary_id=missing_id,
        openlibrary_book_id=missing_id,
        isbn="9780765377067",
        extra_openlibrary_ids="OL321W",
    )

    data = asyncio.run(tracker.get_data(meta))

    assert {"book_exists_on_openlibrary", "openlibrary_book_id", "openlibrary_isbn", "extra_openlibrary_ids"}.isdisjoint(data)


@pytest.mark.parametrize("category", ["MOVIE", "TV", "MUSIC", "GAME", "XXX"])
def test_non_book_payload_is_unchanged(tracker, category):
    meta = Meta(category=category, type="WEBDL", language_checked=True)
    expected = asyncio.run(tracker.get_data(meta))
    meta.openlibrary = "OL123W"
    meta.openlibrary_id = "OL456W"
    meta.openlibrary_book_id = "OL789W"
    meta.isbn = "9780765377067"
    meta.extra_openlibrary_ids = "OL321W"

    assert list(asyncio.run(tracker.get_data(meta)).items()) == list(expected.items())


def test_tracker_without_book_support_keeps_payload_unchanged(monkeypatch):
    tracker = UNIT3D({"DEFAULT": {}, "TRACKERS": {}}, tracker_name="UNIT3D")
    monkeypatch.setattr(tracker, "get_description", AsyncMock(return_value={"description": "Description"}))
    meta = Meta(category="BOOK", type="EPUB")
    expected = asyncio.run(tracker.get_data(meta))
    meta.openlibrary = "OL123W"
    meta.openlibrary_id = "OL456W"
    meta.openlibrary_book_id = "OL789W"
    meta.isbn = "9780765377067"
    meta.extra_openlibrary_ids = "OL321W"

    assert "BOOK" not in tracker.supported_categories
    assert list(asyncio.run(tracker.get_data(meta)).items()) == list(expected.items())
