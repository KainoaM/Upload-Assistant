import asyncio

import pytest

from src.meta import _TRACKER_ID_ALIASES, Meta
from src.trackers.UNIT3D.dreadvault import DreadVault
from src.trackersetup import TrackerSetup, tracker_class_map


def _tracker() -> DreadVault:
    return DreadVault({"TRACKERS": {"DREADVAULT": {"api_key": ""}}})


def test_dreadvault_is_registered_with_full_tracker_name():
    assert tracker_class_map["DREADVAULT"] is DreadVault  # noqa: S101
    assert DreadVault.display_name == "DreadVault"  # noqa: S101
    assert DreadVault.supported_categories == ("TV", "MOVIE", "BOOK")  # noqa: S101


def test_dreadvault_dvl_alias_resolves_to_the_canonical_name():
    # DVL is the site's own abbreviation, confirmed by DreadVault staff.
    assert _TRACKER_ID_ALIASES["DVL"] == "DREADVAULT"  # noqa: S101
    assert Meta().canonical_tracker_name("dvl") == "DREADVAULT"  # noqa: S101


def test_dreadvault_dvl_cli_alias_is_canonicalized_before_tracker_checks():
    meta = Meta(category="MOVIE", trackers=["DVL"])
    setup = TrackerSetup({"TRACKERS": {"DREADVAULT": {"api_key": "test-token"}}})

    setup.filter_unsupported_trackers(meta)

    assert meta.trackers == ["DREADVAULT"]  # noqa: S101


def test_dreadvault_bans_the_published_groups():
    # Published on the site's rules page 2026-08-24, extended 2026-09-06; DreadVault exposes no
    # /api/bannedReleaseGroups endpoint, so this list is maintained by hand.
    assert set(DreadVault.banned_groups) == {  # noqa: S101
        "AOC",
        "AOS",
        "BONE",
        "EVO",
        "FGT",
        "LAMA",
        "NeoNoir",
        "PSA",
        "RARBG",
        "VXT",
        "YIFY",
        "YTS",
    }


@pytest.mark.parametrize(
    "combined_genres",
    [
        "Horror",
        "Horror, Thriller",
        "Horror, Mystery, Thriller",
        "Thriller, Horror",
        ["Horror"],
        ["Horror", "Thriller"],
    ],
)
def test_dreadvault_accepts_horror_regardless_of_genre_order(combined_genres):
    tracker = _tracker()
    meta = Meta(combined_genres=combined_genres, unattended=True)
    assert asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


def test_dreadvault_accepts_horror_from_keywords():
    tracker = _tracker()
    meta = Meta(combined_genres="", keywords=["horror"], unattended=True)
    assert asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


def test_dreadvault_accepts_horror_inside_a_compound_keyword():
    tracker = _tracker()
    meta = Meta(combined_genres="Drama, Thriller", keywords=["psychological horror"], unattended=True)
    assert asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


def test_dreadvault_accepts_horror_with_incidental_mature_keywords():
    tracker = _tracker()
    meta = Meta(combined_genres="Horror, Thriller", keywords=["adult animation", "orgy", "erotic"], unattended=True)
    assert asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


def test_dreadvault_rejects_non_horror_when_unattended():
    tracker = _tracker()
    meta = Meta(combined_genres="Action, Comedy", unattended=True)
    assert not asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


def test_dreadvault_rejects_movie_without_genre_metadata_when_unattended():
    tracker = _tracker()
    meta = Meta(category="MOVIE", combined_genres="", keywords=[], unattended=True)
    assert not asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


def test_dreadvault_only_blocks_exact_duplicates():
    assert DreadVault.exact_match_only is True  # noqa: S101


def test_dreadvault_adult_keyword_skips_when_unattended():
    tracker = _tracker()
    meta = Meta(combined_genres="Horror", keywords=["porn"], unattended=True)
    assert not asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


def test_dreadvault_rejects_adult_content():
    tracker = _tracker()
    meta = Meta(combined_genres="Horror", keywords=["porn"], unattended=True)
    assert not asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


@pytest.mark.parametrize(
    ("ocr", "source", "expected"),
    [
        (True, "SCAN", "Liu Cixin - The Three-Body Problem Revised Edition 2008 PDF OCR 9780765377067-GROUP"),
        (False, "scan", "Liu Cixin - The Three-Body Problem Revised Edition 2008 PDF SCAN 9780765377067-GROUP"),
        (False, "RETAIL", "Liu Cixin - The Three-Body Problem Revised Edition 2008 PDF 9780765377067-GROUP"),
    ],
)
def test_dreadvault_ebook_name_includes_edition_type_isbn_and_tag(ocr, source, expected):
    meta = Meta(
        category="BOOK",
        author="Liu Cixin",
        title="The Three-Body Problem",
        edition="Revised Edition",
        year=2008,
        type="PDF",
        ocr=ocr,
        source=source,
        isbn="978-0765377067",
        tag="-GROUP",
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == expected  # noqa: S101


@pytest.mark.parametrize("book_format", ["EPUB", "CBR"])
def test_dreadvault_ebook_name_omits_absent_edition_and_isbn(book_format):
    meta = Meta(category="BOOK", author="Author Name", title="Book Title", year=2026, type=book_format, tag="GROUP")

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == f"Author Name - Book Title 2026 {book_format}-GROUP"  # noqa: S101


def test_dreadvault_ebook_name_prefers_manual_edition():
    meta = Meta(category="BOOK", author="Author Name", title="Book Title", edition="First Edition", manual_edition="Second Edition", year=2026, type="EPUB")

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Author Name - Book Title Second Edition 2026 EPUB"  # noqa: S101


def test_dreadvault_book_name_never_uses_publisher_as_author():
    meta = Meta(category="BOOK", publisher="Publisher Name", title="Book Title", year=2026, type="EPUB", isbn="978-0-123456-47-2")

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Book Title 2026 EPUB 9780123456472"  # noqa: S101


@pytest.mark.parametrize(("author", "expected_author"), [("", "Book Author"), ("Author Name", "Author Name")])
def test_dreadvault_book_name_falls_back_to_book_author(author, expected_author):
    meta = Meta(category="BOOK", author=author, book_author="Book Author", publisher="Publisher Name", title="Book Title", year=2026, type="EPUB")

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == f"{expected_author} - Book Title 2026 EPUB"  # noqa: S101


@pytest.mark.parametrize(
    ("manual_source", "source", "ocr", "expected"),
    [
        ("scan", "RETAIL", False, "Book Title 2026 PDF SCAN"),
        ("RETAIL", "SCAN", False, "Book Title 2026 PDF"),
        ("SCAN", "RETAIL", True, "Book Title 2026 PDF OCR"),
    ],
)
def test_dreadvault_book_name_prefers_manual_source_and_ocr(manual_source, source, ocr, expected):
    meta = Meta(category="BOOK", title="Book Title", year=2026, type="PDF", manual_source=manual_source, source=source, ocr=ocr)

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == expected  # noqa: S101


@pytest.mark.parametrize(("book_format", "type_id"), [("EPUB", "8"), ("PDF", "7"), ("CBR", "9")])
@pytest.mark.parametrize("format_field", ["type", "container"])
def test_dreadvault_ebook_category_type_and_resolution_ids(book_format, type_id, format_field):
    tracker = _tracker()
    meta = Meta(category="BOOK", resolution="Other", **{format_field: f" .{book_format.lower()} "})

    assert asyncio.run(tracker.get_category_id(meta)) == {"category_id": "3"}  # noqa: S101
    assert asyncio.run(tracker.get_type_id(meta)) == {"type_id": type_id}  # noqa: S101
    assert asyncio.run(tracker.get_resolution_id(meta)) == {"resolution_id": "10"}  # noqa: S101


@pytest.mark.parametrize("book_format", ["MOBI", "AZW", "AZW3", "CBZ", "TXT", "DJVU", "LIT", "ENCODE", ""])
def test_dreadvault_rejects_unsupported_ebook_formats(book_format, caplog):
    meta = Meta(category="BOOK", type=book_format, keywords=["Horror fiction"], unattended=True)

    assert not asyncio.run(_tracker().get_additional_checks(meta))  # noqa: S101
    assert "DREADVAULT" in caplog.text  # noqa: S101
    assert "format" in caplog.text.lower()  # noqa: S101
    assert book_format in caplog.text  # noqa: S101


@pytest.mark.parametrize("unattended", [False, True])
def test_dreadvault_rejects_audiobooks(unattended, caplog):
    meta = Meta(category="BOOK", audiobook=True, type="EPUB", keywords=["Horror fiction"], unattended=unattended)

    assert not asyncio.run(_tracker().get_additional_checks(meta))  # noqa: S101
    assert "DREADVAULT" in caplog.text  # noqa: S101
    assert "audiobook" in caplog.text.lower()  # noqa: S101


@pytest.mark.parametrize("category", ["MOVIE", "TV"])
@pytest.mark.parametrize(("combined_genres", "accepted"), [("Horror", True), ("Comedy", False)])
def test_dreadvault_audiobook_flag_preserves_movie_and_tv_horror_checks(category, combined_genres, accepted):
    meta = Meta(category=category, audiobook=True, combined_genres=combined_genres, unattended=True)

    assert asyncio.run(_tracker().get_additional_checks(meta)) is accepted  # noqa: S101


@pytest.mark.parametrize(
    ("combined_genres", "keywords", "accepted"),
    [
        ("", ["Horror fiction"], True),
        ("", ["Romance"], False),
        ("", [], True),
        (["Juvenile Fiction"], [], False),
        (["Fiction / Horror"], [], True),
    ],
)
def test_dreadvault_ebook_horror_checks_when_unattended(combined_genres, keywords, accepted, caplog):
    meta = Meta(category="BOOK", type="EPUB", combined_genres=combined_genres, keywords=keywords, unattended=True)

    assert asyncio.run(_tracker().get_additional_checks(meta)) is accepted  # noqa: S101
    if not combined_genres and not keywords:
        assert caplog.text.count("Horror gate could not be evaluated because the book has no genre metadata; trusting the uploader's selection.") == 1  # noqa: S101


def test_dreadvault_ebook_does_not_add_identifier_payload_fields():
    meta = Meta(category="BOOK", type="EPUB", openlibrary="OL123M", isbn="9780765377067")

    assert asyncio.run(_tracker().get_additional_data(meta)) == {}  # noqa: S101


def test_dreadvault_formats_dvdrip_with_resolution_and_encode_after_audio():
    meta = Meta(
        name="Example Movie 2001 PAL DVD x264 DVDRip DD 2.0-GRP",
        type="DVDRIP",
        source="PAL DVD",
        resolution="480p",
        video_encode=" x264",
        audio="DD 2.0",
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Movie 2001 480p DVDRip DD 2.0 x264-GRP"  # noqa: S101


def test_dreadvault_formats_dvd_disc_with_resolution_codec_region_and_source():
    meta = Meta(
        name="Example Movie 2001 R1 NTSC DVD DVD9 DD 5.1-GRP",
        type="DISC",
        is_disc="DVD",
        source="NTSC DVD",
        resolution="480p",
        region="R1",
        video_codec="MPEG-2",
        audio="DD 5.1",
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Movie 2001 480p R1 NTSC DVD DVD9 MPEG-2 DD 5.1-GRP"  # noqa: S101


def test_dreadvault_formats_dvd_remux_with_resolution_before_source():
    meta = Meta(
        name="Example Movie 2001 PAL DVD REMUX DD 5.1-GRP",
        type="REMUX",
        source="PAL DVD",
        resolution="576p",
        video_codec="MPEG-2",
        audio="DD 5.1",
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Movie 2001 576p PAL DVD REMUX MPEG-2 DD 5.1-GRP"  # noqa: S101


def test_dreadvault_adds_foreign_audio_language_before_encode_resolution():
    meta = Meta(
        name="Example Movie 2001 1080p BluRay DD 5.1 x264-GRP",
        type="ENCODE",
        source="BluRay",
        resolution="1080p",
        audio_languages=["Japanese"],
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Movie 2001 JAPANESE 1080p BluRay DD 5.1 x264-GRP"  # noqa: S101


def test_dreadvault_omits_foreign_audio_language_from_bdmv_disc():
    meta = Meta(
        name="Example Movie 2001 1080p BluRay AVC DD 5.1-GRP",
        type="DISC",
        is_disc="BDMV",
        source="BluRay",
        resolution="1080p",
        audio_languages=["Japanese"],
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Movie 2001 1080p BluRay AVC DD 5.1-GRP"  # noqa: S101


def test_dreadvault_omits_language_marker_when_audio_includes_english():
    meta = Meta(
        name="Example Movie 2001 1080p BluRay DD 5.1 x264-GRP",
        type="ENCODE",
        source="BluRay",
        resolution="1080p",
        audio_languages=["Japanese", "English"],
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Movie 2001 1080p BluRay DD 5.1 x264-GRP"  # noqa: S101


def test_dreadvault_adds_foreign_audio_language_to_a_dvdrip():
    # The DVDRip template carries no resolution of its own, so a language pass that ran before the
    # DVDRip branch had nothing to anchor to and dropped the marker (kainoa 2026-09-09).
    meta = Meta(
        name="Suicide Dolls 1999 NTSC DVD x264 DVDRip DD 2.0-GVXXI",
        type="DVDRIP",
        source="NTSC DVD",
        resolution="480p",
        audio="DD 2.0",
        video_encode=" x264",
        audio_languages=["Japanese"],
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Suicide Dolls 1999 JAPANESE 480p DVDRip DD 2.0 x264-GVXXI"  # noqa: S101


def test_dreadvault_adds_foreign_audio_language_to_a_dvd_full_disc():
    meta = Meta(
        name="Hausu 1977 USA NTSC DVD DVD9 LPCM 2.0",
        year=1977,
        type="DISC",
        is_disc="DVD",
        source="NTSC DVD",
        resolution="480p",
        region="USA",
        video_codec="MPEG-2",
        audio="LPCM 2.0",
        audio_languages=["Japanese"],
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name.startswith("Hausu 1977 JAPANESE 480p USA NTSC DVD")  # noqa: S101


def test_dreadvault_adds_foreign_audio_language_after_year_for_dvd_remux():
    meta = Meta(
        name="Example Movie 2001 PAL DVD REMUX DD 5.1-GRP",
        year=2001,
        type="REMUX",
        source="PAL DVD",
        resolution="576p",
        video_codec="MPEG-2",
        audio="DD 5.1",
        audio_languages=["Japanese"],
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Movie 2001 JAPANESE 576p PAL DVD REMUX MPEG-2 DD 5.1-GRP"  # noqa: S101


def test_dreadvault_never_adds_trump_suffix_for_exact_match():
    meta = Meta(
        name="Example Movie 2001 1080p BluRay DD 5.1 x264-GRP",
        trump_reason="exact_match",
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert not name.endswith("- TRUMP")  # noqa: S101


def test_dreadvault_moves_tv_aka_before_year():
    meta = Meta(
        category="TV",
        year=2024,
        search_year=2024,
        name="Example Show 2024 AKA Alternate Show S01 1080p WEB-DL",
        aka="AKA Alternate Show",
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Show AKA Alternate Show 2024 S01 1080p WEB-DL"  # noqa: S101
