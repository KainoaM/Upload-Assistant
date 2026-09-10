"""Regression tests for LST-specific upload payloads."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from src.meta import Meta
from src.trackers.UNIT3D.lst import LST


@pytest.mark.parametrize(
    ("openlibrary", "openlibrary_id", "openlibrary_book_id", "expected_id"),
    [
        ("OL123W", "OL456W", "OL789W", "OL123W"),
        (None, "OL456W", "OL789W", "OL456W"),
        ("", "", "OL789W", "OL789W"),
        (None, None, None, ""),
        ("", "", "", ""),
    ],
)
@pytest.mark.parametrize(("isbn", "extra_ids"), [("9781234567890", "OL456W"), ("", ""), (None, None)])
def test_lst_book_payload_preserves_legacy_fields_and_order(monkeypatch, openlibrary, openlibrary_id, openlibrary_book_id, expected_id, isbn, extra_ids):
    tracker = LST({"DEFAULT": {}, "TRACKERS": {"LST": {}}})
    monkeypatch.setattr(tracker, "get_description", AsyncMock(return_value={"description": "Book description"}))
    monkeypatch.setattr(tracker.common, "unit3d_distributor_ids", AsyncMock(return_value="42"))
    meta = Meta(
        category="BOOK",
        type="EPUB",
        author="Author",
        title="Book",
        year=2026,
        edition="Limited Edition",
        region="CZE",
        exclusive=True,
        openlibrary=openlibrary,
        openlibrary_id=openlibrary_id,
        openlibrary_book_id=openlibrary_book_id,
        isbn=isbn,
        extra_openlibrary_ids=extra_ids,
    )

    data = asyncio.run(tracker.get_data(meta))

    assert list(data.items()) == [
        ("name", "Author - Book Limited Edition 2026 EPUB" + (f" {isbn}" if isbn else "")),
        ("description", "Book description"),
        ("mediainfo", ""),
        ("bdinfo", ""),
        ("category_id", "9"),
        ("type_id", "15"),
        ("resolution_id", "10"),
        ("tmdb", "0"),
        ("imdb", "0"),
        ("tvdb", "0"),
        ("mal", "0"),
        ("igdb", "0"),
        ("anonymous", "0"),
        ("stream", "False"),
        ("sd", "False"),
        ("keywords", ""),
        ("personal_release", "0"),
        ("internal", "0"),
        ("featured", "0"),
        ("free", "0"),
        ("doubleup", "0"),
        ("sticky", "0"),
        ("mod_queue_opt_in", "0"),
        ("draft_queue_opt_in", "0"),
        ("edition_id", 6),
        ("book_exists_on_openlibrary", "1"),
        ("openlibrary_book_id", expected_id),
        ("openlibrary_isbn", isbn or ""),
        ("extra_openlibrary_ids", extra_ids or ""),
        ("region_id", "244"),
        ("distributor_id", "42"),
        ("exclusive", "1"),
    ]


def test_lst_music_payload_includes_discogs_release_and_master_ids():
    meta = Meta(
        category="MUSIC",
        music_release={"external_ids": {"discogs_release": "https://www.discogs.com/release/12345-example", "discogs_master": "master/67890"}},
    )

    data = asyncio.run(LST({"DEFAULT": {}, "TRACKERS": {"LST": {}}}).get_additional_data(meta))

    assert data["release_exists_on_discogs"] == "1"
    assert data["discogs"] == "12345"
    assert data["discogs_master_id"] == "67890"
    assert data["extra_discogs_ids"] == ""
    assert data["extra_discogs_master_ids"] == ""


def test_lst_music_payload_omits_discogs_existence_flag_for_invalid_ids():
    meta = Meta(category="MUSIC", music_release={"external_ids": {"discogs_release": "not-an-id"}})

    data = asyncio.run(LST({"DEFAULT": {}, "TRACKERS": {"LST": {}}}).get_additional_data(meta))

    assert "release_exists_on_discogs" not in data


def test_lst_music_name_uses_technical_fields_for_lossless_releases():
    meta = Meta(
        category="MUSIC",
        tag="-FiVE0",
        music_release={
            "fields": {
                "artist": {"value": "Taylor Swift"},
                "album": {"value": "Red"},
                "release_year": {"value": "2012"},
                "media": {"value": "WEB"},
            },
            "tracks": [{"codec": "FLAC", "bit_depth": 16, "sample_rate": 44100}],
        },
    )

    name = asyncio.run(LST({"DEFAULT": {}, "TRACKERS": {"LST": {}}}).get_name(meta))["name"]

    assert name == "Taylor Swift - Red 2012 WEB FLAC 16-bit 44.1 kHz-FiVE0"


def test_lst_music_name_ignores_invalid_sample_rate():
    meta = Meta(
        category="MUSIC",
        music_release={
            "fields": {
                "artist": {"value": "Artist"},
                "album": {"value": "Album"},
                "release_year": {"value": "2000"},
                "media": {"value": "CD"},
                "nfo_sample_rate": {"value": "unknown"},
            },
            "tracks": [{"codec": "FLAC", "bit_depth": 16}],
        },
    )

    name = asyncio.run(LST({"DEFAULT": {}, "TRACKERS": {"LST": {}}}).get_name(meta))["name"]

    assert name == "Artist - Album 2000 CD FLAC 16-bit"


def test_lst_audiobook_name_omits_lossy_technical_fields():
    meta = Meta(category="BOOK", audiobook=True, author="Ernest Cline", title="Ready Player One", year=2011, source="WEB", type="M4B", tag="zeno")

    name = asyncio.run(LST({"DEFAULT": {}, "TRACKERS": {"LST": {}}}).get_name(meta))["name"]

    assert name == "Ernest Cline - Ready Player One 2011 WEB M4B-zeno"


def test_lst_ebook_name_includes_edition_type_and_isbn():
    meta = Meta(
        category="BOOK",
        author="Liu Cixin",
        title="The Three-Body Problem",
        edition="Revised Edition",
        year=2008,
        type="PDF",
        ocr=True,
        isbn="978-0765377067",
        tag="-GROUP",
    )

    name = asyncio.run(LST({"DEFAULT": {}, "TRACKERS": {"LST": {}}}).get_name(meta))["name"]

    assert name == "Liu Cixin - The Three-Body Problem Revised Edition 2008 PDF OCR 9780765377067-GROUP"
