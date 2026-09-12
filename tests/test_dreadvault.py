import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from src.meta import _TRACKER_ID_ALIASES, Meta
from src.trackers.UNIT3D.dreadvault import DreadVault
from src.trackersetup import TrackerSetup, tracker_class_map
from src.trackerstatus import TrackerStatusManager


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


@pytest.mark.parametrize("field", ["combined_genres", "keywords"])
@pytest.mark.parametrize(
    "subject",
    [
        "Ghost stories",
        "Ghost story collections",
        "Vampires",
        "Occult fiction",
        "Monsters",
        "Demonic",
        "Demon possession",
        "Spirit possession",
        "Haunted houses",
        "Haunted places",
        "Witchcraft",
        "Zombies",
        "Undead",
        "Werewolf",
        "Werewolves",
        "Lycanthropes",
        "Lycanthropy",
        "Creature features",
        "Killer dolls",
        "Killer objects",
        "Slasher",
        "Lovecraftian fiction",
        "Eldritch",
        "Giallo",
        "J-Horror",
        "K-Horror",
    ],
)
def test_dreadvault_accepts_horror_taxonomy_from_book_subjects(field, subject):
    meta = Meta(category="BOOK", type="EPUB", unattended=True, **{field: [subject]})

    assert asyncio.run(_tracker().get_additional_checks(meta))  # noqa: S101


@pytest.mark.parametrize(
    "subject",
    [
        "Supernatural",
        "Possession",
        "Witch",
        "Religious",
        "Death",
        "Afterlife",
        "Animals",
        "Insects",
        "Aquatic",
        "Sea",
        "Psychological",
        "Home invasion",
        "Survival",
        "Road",
        "Alien",
        "Cosmic",
        "Science fiction",
        "Literary criticism",
        "Romance",
        "Western",
        "Business",
        "Body",
        "Medical",
        "Gore",
        "Splatter",
        "Found footage",
        "Analog",
        "Anthology",
        "Folk",
        "Comedy",
        "Dark fantasy",
        "Thai",
        "Spanish",
        "French",
        "Italian",
        "British",
        "American",
        "Graphic violence",
        "Thriller",
        "Ghostwriter",
        "Switches",
        "Demonstrations",
        "Haunted",
        "House",
        "Place",
        "Creature",
        "Feature",
        "Killer",
        "Doll",
        "Object",
    ],
)
def test_dreadvault_ambiguous_subjects_need_horror_qualification(subject):
    meta = Meta(category="BOOK", type="EPUB", combined_genres=subject, unattended=True)

    assert not asyncio.run(_tracker().get_additional_checks(meta))  # noqa: S101

    meta.combined_genres = f"{subject} horror"
    assert asyncio.run(_tracker().get_additional_checks(meta))  # noqa: S101


def test_dreadvault_horror_phrases_must_occur_in_one_term():
    meta = Meta(category="BOOK", type="EPUB", combined_genres=["Haunted", "Killer"], keywords=["House", "Doll"], unattended=True)

    assert not asyncio.run(_tracker().get_additional_checks(meta))  # noqa: S101


def test_dreadvault_accepts_horror_with_incidental_mature_keywords():
    tracker = _tracker()
    meta = Meta(combined_genres="Horror, Thriller", keywords=["adult animation", "orgy", "erotic"], unattended=True)
    assert asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


def test_dreadvault_rejects_non_horror_when_unattended():
    tracker = _tracker()
    meta = Meta(combined_genres="Action, Comedy", unattended=True)
    assert not asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101


@pytest.mark.parametrize("category", ["MOVIE", "TV"])
@pytest.mark.parametrize("combined_genres", ["", "Fiction"])
def test_dreadvault_rejects_video_without_horror_evidence_when_unattended(category, combined_genres, caplog):
    tracker = _tracker()
    meta = Meta(category=category, combined_genres=combined_genres, keywords=[], unattended=True)
    assert not asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101
    assert not any(record.levelname == "WARNING" for record in caplog.records)  # noqa: S101


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


@pytest.mark.parametrize("tracker_name", ["LASTDIGITALUNDERGROUND", "DREADVAULT"])
@pytest.mark.parametrize("missing_field", ["title", "author", "year", "book_language"])
def test_book_required_fields_skip_only_when_required(tracker_name, missing_field, monkeypatch, caplog):
    meta = Meta(
        category="BOOK",
        trackers=[tracker_name],
        unattended=True,
        title="Book Title",
        author="Author Name",
        year=2026,
        book_language="English",
        book_language_iso="eng",
        type="EPUB",
        combined_genres="Horror",
    )
    meta[missing_field] = ""
    config = {"TRACKERS": {tracker_name: {"api_key": "test-token", "announce_url": "https://example.com/announce"}}}
    search = AsyncMock(return_value=[])
    monkeypatch.setattr(TrackerSetup, "check_banned_group", AsyncMock(return_value=False))
    monkeypatch.setattr(TrackerSetup, "get_torrent_claims", AsyncMock(return_value=False))
    monkeypatch.setattr(tracker_class_map[tracker_name], "search_existing", search)
    monkeypatch.setattr("src.trackerstatus.DupeChecker.filter_dupes", AsyncMock(return_value=[]))

    count = asyncio.run(TrackerStatusManager(config).process_all_trackers(meta))

    skipped = tracker_name != "DREADVAULT" or missing_field != "year"
    assert meta.tracker_status[tracker_name]["skipped"] is skipped  # noqa: S101
    assert meta.tracker_status[tracker_name]["upload"] is not skipped  # noqa: S101
    assert count == int(not skipped)  # noqa: S101
    assert search.await_count == int(not skipped)  # noqa: S101
    assert meta[missing_field] == ""  # noqa: S101
    if skipped:
        messages = [record.message for record in caplog.records if "required BOOK fields are missing" in record.message]
        assert len(messages) == 1  # noqa: S101
        assert missing_field in messages[0]  # noqa: S101
        assert "re-run attended" in messages[0]  # noqa: S101


@pytest.mark.parametrize(
    ("trackers", "fields"),
    [
        (["LASTDIGITALUNDERGROUND"], ["title", "author", "year", "language"]),
        (["DREADVAULT"], ["title", "author", "language"]),
        (["DREADVAULT", "LASTDIGITALUNDERGROUND"], ["title", "author", "language", "year"]),
        ([], ["title", "author", "year", "language"]),
    ],
)
def test_book_prompt_uses_selected_trackers_required_fields(trackers, fields, monkeypatch):
    import upload

    ui = Mock()
    ui.ask_string.return_value = ""
    monkeypatch.setattr(upload, "CLI_UI", ui)
    meta = Meta(category="BOOK", trackers=trackers, artwork_url="https://example.com/cover.jpg")

    assert asyncio.run(upload._prompt_book_meta(meta))  # noqa: S101

    assert [call.args[0] for call in ui.ask_string.call_args_list] == [f"Enter {field} (leave blank to skip): " for field in fields]  # noqa: S101


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
        ("  ,  ", ["", "  "], True),
        (["", "  "], [], True),
        (["Juvenile Fiction"], [], True),
        (["Fiction / Horror"], [], True),
        (["Fiction", "Romance"], [], False),
        (["Fiction"], ["Romance"], False),
        (["Romance"], ["Fiction"], False),
        (["Fiction / Romance"], [], False),
        (["Fiction", "Ghost stories"], [], True),
        (["Fiction"], ["Ghost stories"], True),
    ],
)
def test_dreadvault_ebook_horror_checks_when_unattended(combined_genres, keywords, accepted, caplog):
    meta = Meta(category="BOOK", type="EPUB", combined_genres=combined_genres, keywords=keywords, unattended=True)

    assert asyncio.run(_tracker().get_additional_checks(meta)) is accepted  # noqa: S101
    if not combined_genres and not keywords:
        assert "no genre metadata is available" in caplog.text  # noqa: S101
    if not accepted or "Ghost stories" in combined_genres or "Ghost stories" in keywords:
        assert not any(record.levelname == "WARNING" for record in caplog.records)  # noqa: S101


@pytest.mark.parametrize(
    ("combined_genres", "keywords", "reason"),
    [
        (["", "  "], ["  "], "no genre metadata is available (genres and keywords are empty)"),
        (["Fiction"], ["Fiction"], "the only genre evidence is non-specific; the horror gate could not be evaluated"),
        (["Fiction", "General"], [], "the only genre evidence is non-specific; the horror gate could not be evaluated"),
        ([], ["Nonfiction", "Non-fiction", "Literature", "Literary", "Juvenile fiction", "Young adult fiction", "Ebook", "Books"],
         "the only genre evidence is non-specific; the horror gate could not be evaluated"),
    ],
)
@pytest.mark.parametrize("unattended", [False, True])
@pytest.mark.parametrize("skip_mam_source", [None, "cli", "config"])
def test_dreadvault_book_without_informative_genres_warns_and_continues(combined_genres, keywords, reason, unattended, skip_mam_source, monkeypatch, caplog):
    tracker = _tracker()
    tracker.config["DEFAULT"] = {"book_skip_mam": skip_mam_source == "config"}
    meta = Meta(category="BOOK", type="EPUB", combined_genres=combined_genres, keywords=keywords, unattended=unattended, book_skip_mam=skip_mam_source == "cli")
    prompt = Mock(side_effect=AssertionError("Books without genre evidence must not prompt"))
    monkeypatch.setattr("src.trackers.UNIT3D.dreadvault.cli_ui.ask_yes_no", prompt)

    assert asyncio.run(tracker.get_additional_checks(meta))  # noqa: S101

    messages = [record for record in caplog.records if "BOOK:" in record.message]
    assert len(messages) == 1  # noqa: S101
    assert messages[0].levelname == "WARNING"  # noqa: S101
    assert reason in messages[0].message  # noqa: S101
    assert "continuing on uploader responsibility" in messages[0].message  # noqa: S101
    assert "Verify that this book qualifies as horror" in messages[0].message  # noqa: S101
    assert ("book_skip_mam is enabled; disable it" in messages[0].message) is bool(skip_mam_source)  # noqa: S101
    prompt.assert_not_called()


@pytest.mark.parametrize("combined_genres", ["", ["Fiction"], ["Fiction", "General"]])
def test_dreadvault_book_without_informative_genres_still_checks_adult_media(combined_genres, caplog):
    meta = Meta(category="BOOK", type="EPUB", combined_genres=combined_genres, adult_media=True, unattended=True)

    assert not asyncio.run(_tracker().get_additional_checks(meta))  # noqa: S101
    assert "Porn/xxx" in caplog.text  # noqa: S101


@pytest.mark.parametrize("category", ["MOVIE", "TV"])
@pytest.mark.parametrize("combined_genres", ["", "Fiction"])
@pytest.mark.parametrize("response", [False, True])
def test_dreadvault_video_without_horror_evidence_requires_attended_override(category, combined_genres, response, monkeypatch, caplog):
    meta = Meta(category=category, combined_genres=combined_genres, unattended=False)
    prompt = Mock(return_value=response)
    monkeypatch.setattr("src.trackers.UNIT3D.dreadvault.cli_ui.ask_yes_no", prompt)

    assert asyncio.run(_tracker().get_additional_checks(meta)) is response  # noqa: S101
    assert not any(record.levelname == "WARNING" for record in caplog.records)  # noqa: S101
    prompt.assert_called_once_with("Do you want to upload anyway?", default=False)


@pytest.mark.parametrize(
    ("evidence", "warning"),
    [
        ({"keywords": ["Romance"]}, "Only horror content"),
        ({"combined_genres": ["Survival"]}, "Only horror content"),
        ({"combined_genres": "Horror", "keywords": ["porn"]}, "Porn/xxx"),
        ({"combined_genres": "Horror", "adult_media": True}, "Porn/xxx"),
        ({"combined_genres": ["Ghost stories"], "keywords": ["porn"]}, "Porn/xxx"),
        ({"combined_genres": ["Vampires"], "keywords": ["xxx"]}, "Porn/xxx"),
        ({"combined_genres": ["Occult fiction"], "adult_media": True}, "Porn/xxx"),
        ({"combined_genres": ["Fiction", "Ghost stories"], "keywords": ["porn"]}, "Porn/xxx"),
        ({"combined_genres": ["Fiction", "Ghost stories"], "keywords": ["xxx"]}, "Porn/xxx"),
        ({"combined_genres": ["Fiction"], "adult_media": True}, "Porn/xxx"),
    ],
)
@pytest.mark.parametrize(
    ("unattended", "unattended_confirm", "response", "accepted"),
    [(True, False, True, False), (True, True, True, False), (False, False, False, False), (False, False, True, True)],
)
def test_dreadvault_content_rules_require_attended_override(evidence, warning, unattended, unattended_confirm, response, accepted, monkeypatch, caplog):
    meta = Meta(category="BOOK", type="EPUB", unattended=unattended, unattended_confirm=unattended_confirm, **evidence)
    prompt = Mock(return_value=response)
    monkeypatch.setattr("src.trackers.UNIT3D.dreadvault.cli_ui.ask_yes_no", prompt)

    assert asyncio.run(_tracker().get_additional_checks(meta)) is accepted  # noqa: S101

    assert warning in caplog.text  # noqa: S101
    assert "re-run attended" in caplog.text  # noqa: S101
    if unattended:
        prompt.assert_not_called()
    else:
        prompt.assert_called_once_with("Do you want to upload anyway?", default=False)


def test_dreadvault_ebook_has_no_tracker_specific_additional_data():
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


def test_dreadvault_names_a_dvd_sourced_encode_as_a_dvdrip():
    meta = Meta(
        name="Ghost 1984 480p NTSC DD 2.0 x264-SaL",
        type="ENCODE",
        source="NTSC",
        resolution="480p",
        video_encode="x264",
        audio="DD 2.0",
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Ghost 1984 480p DVDRip DD 2.0 x264-SaL"  # noqa: S101


def test_dreadvault_keeps_the_episode_on_a_dvd_sourced_encode():
    meta = Meta(
        name="Example Show 1989 S04E02 Unrated REPACK 480p PAL DD 2.0 x264-GRP",
        category="TV",
        type="ENCODE",
        source="PAL",
        resolution="480p",
        edition="Unrated",
        repack="REPACK",
        video_encode="x264",
        audio="DD 2.0",
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Show 1989 S04E02 480p DVDRip DD 2.0 x264-GRP"  # noqa: S101


def test_dreadvault_drops_edition_and_repack_from_a_dvd_sourced_encode():
    meta = Meta(
        name="Example Movie 1994 Uncut REPACK3 480p NTSC DD 5.1 x264-GRP",
        type="ENCODE",
        source="NTSC",
        resolution="480p",
        edition="Uncut",
        repack="REPACK3",
        video_encode="x264",
        audio="DD 5.1",
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Movie 1994 480p DVDRip DD 5.1 x264-GRP"  # noqa: S101


def test_dreadvault_formats_hi10p_dvdrip_with_encode_after_audio():
    meta = Meta(
        name="Example Movie 2001 PAL DVD Hi10P x264 DVDRip DD 2.0-GRP",
        type="DVDRIP",
        source="PAL DVD",
        resolution="480p",
        video_encode="Hi10P x264",
        audio="DD 2.0",
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Movie 2001 480p DVDRip DD 2.0 Hi10P x264-GRP"  # noqa: S101


def test_dreadvault_preserves_title_spaces_when_dvdrip_source_and_encode_are_empty():
    meta = Meta(
        name="Example Movie 1990 DVDRip DD 2.0-GRP",
        type="DVDRIP",
        source="",
        resolution="480p",
        video_encode="",
        audio="DD 2.0",
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Example Movie 1990 480p DVDRip DD 2.0-GRP"  # noqa: S101


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


@pytest.mark.parametrize("audio_language", ["No", "Undetermined"])
def test_dreadvault_omits_language_marker_for_non_linguistic_audio(audio_language):
    meta = Meta(
        name="Ghost 1984 NTSC x264 DVDRip DD 2.0-SaL",
        type="DVDRIP",
        source="NTSC",
        resolution="480p",
        video_encode=" x264",
        audio="DD 2.0",
        audio_languages=[audio_language],
        language_checked=True,
    )

    name = asyncio.run(_tracker().get_name(meta))["name"]

    assert name == "Ghost 1984 480p DVDRip DD 2.0 x264-SaL"  # noqa: S101


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
