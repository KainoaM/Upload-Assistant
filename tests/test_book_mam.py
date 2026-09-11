"""Regression tests for MyAnonamouse's place in per-book metadata lookup."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.args import Args
from src.book_prep import gather_book_prep
from src.google_books import google_books_manager
from src.meta import Meta
from src.myanonamouse import myanonamouse_manager
from src.openlibrary import openlibrary_manager
from src.trackers.UNIT3D.dreadvault import DreadVault


@pytest.fixture
def book_lookup(tmp_path, monkeypatch):
    monkeypatch.delenv("MAM_API_KEY", raising=False)
    monkeypatch.delenv("MAM_ID", raising=False)
    book = tmp_path / "The Hidden City.epub"
    book.write_bytes(b"ebook")
    embedded = {"title": "The Hidden City", "author": "Local Author", "overview": "Embedded synopsis", "isbn": "9780000000002"}
    mam = myanonamouse_manager._parse_torrent_info(
        {
            "title": "The Hidden City (Illustrated)",
            "author_info": '{"42": "MAM Author"}',
            "description": "MAM torrent description",
            "isbn": "978-0-000000-00-3",
            "catname": "Ebooks - Horror",
        }
    )
    google = {"title": "Google Book", "author": "Google Author", "overview": "Google synopsis"}
    openlibrary = {"title": "OpenLibrary Book", "author": "OpenLibrary Author", "overview": "OpenLibrary synopsis"}
    mam_search = AsyncMock(return_value=mam)
    google_search = AsyncMock(return_value=google)
    openlibrary_search = AsyncMock(return_value=openlibrary)
    openlibrary_title_search = AsyncMock(return_value=None)
    info = Mock()
    monkeypatch.setattr("src.book_prep._get_epubmeta_output", lambda _: "")
    monkeypatch.setattr("src.book_prep._extract_epub_metadata", lambda _: embedded)
    monkeypatch.setattr("src.book_prep.export_info", AsyncMock(return_value={}))
    monkeypatch.setattr("src.book_prep.logger.info", info)
    monkeypatch.setattr(myanonamouse_manager, "search_by_id", mam_search)
    monkeypatch.setattr(google_books_manager, "search_by_isbn", google_search)
    monkeypatch.setattr(openlibrary_manager, "search_by_isbn", openlibrary_search)
    monkeypatch.setattr(openlibrary_manager, "search_by_title_author", openlibrary_title_search)
    meta = Meta(
        path=str(book),
        filelist=[str(book)],
        skip_auto_torrent=True,
        torrent_comments=[{"trackers": "https://tracker.myanonamouse.net/announce", "comment": "MID=123"}],
    )
    return SimpleNamespace(
        path=str(book),
        base_dir=str(tmp_path),
        config={"DEFAULT": {"screens": 1}},
        meta=meta,
        embedded=embedded,
        mam=mam,
        mam_search=mam_search,
        google=google,
        google_search=google_search,
        openlibrary=openlibrary,
        openlibrary_search=openlibrary_search,
        openlibrary_title_search=openlibrary_title_search,
        info=info,
    )


@pytest.mark.parametrize("opt_out", ["cli", "config"])
@pytest.mark.parametrize("provider", ["google", "openlibrary"])
def test_mam_opt_out_skips_existing_torrent_comment(book_lookup, opt_out, provider):
    lookup = book_lookup
    if opt_out == "cli":
        lookup.meta, _, _ = Args(lookup.config).parse([lookup.path, "--book-skip-mam"], lookup.meta)
        assert lookup.meta.book_skip_mam is True
    else:
        lookup.config["DEFAULT"]["book_skip_mam"] = True
    if provider == "openlibrary":
        lookup.google_search.return_value = None

    asyncio.run(gather_book_prep(lookup.meta, lookup.path, lookup.base_dir, lookup.config))

    lookup.mam_search.assert_not_awaited()
    assert not lookup.meta.genres
    assert not lookup.meta.keywords
    lookup.google_search.assert_awaited_once_with(lookup.embedded["isbn"], base_dir=lookup.base_dir, api_key="")
    lookup.openlibrary_search.assert_awaited_once_with(lookup.embedded["isbn"], base_dir=lookup.base_dir)
    expected = getattr(lookup, provider)
    assert (lookup.meta.title, lookup.meta.author, lookup.meta.overview, lookup.meta.isbn) == (
        expected["title"], expected["author"], expected["overview"], lookup.embedded["isbn"]
    )


def test_mam_opt_out_also_skips_torrent_client_discovery(book_lookup, monkeypatch):
    lookup = book_lookup
    lookup.meta.torrent_comments = []
    lookup.meta.skip_auto_torrent = False
    lookup.config["DEFAULT"]["book_skip_mam"] = True
    client_search = AsyncMock()
    monkeypatch.setattr("src.clients.Clients.get_pathed_torrents", client_search)

    asyncio.run(gather_book_prep(lookup.meta, lookup.path, lookup.base_dir, lookup.config))

    client_search.assert_not_awaited()
    lookup.mam_search.assert_not_awaited()
    assert lookup.meta.isbn == lookup.embedded["isbn"]


@pytest.mark.parametrize("config_value", [None, False])
def test_mam_enabled_by_default_preserves_metadata_precedence(book_lookup, config_value):
    lookup = book_lookup
    if config_value is not None:
        lookup.config["DEFAULT"]["book_skip_mam"] = config_value

    asyncio.run(gather_book_prep(lookup.meta, lookup.path, lookup.base_dir, lookup.config))

    lookup.mam_search.assert_awaited_once_with("123", base_dir=lookup.base_dir, api_key="")
    lookup.google_search.assert_awaited_once_with(lookup.mam["isbn"], base_dir=lookup.base_dir, api_key="")
    lookup.openlibrary_search.assert_awaited_once_with(lookup.mam["isbn"], base_dir=lookup.base_dir)
    assert (lookup.meta.title, lookup.meta.author, lookup.meta.overview, lookup.meta.isbn) == (
        lookup.mam["title"], lookup.mam["author"], lookup.mam["overview"], lookup.mam["isbn"]
    )
    lookup.info.assert_not_called()


@pytest.mark.parametrize("mam_title", ["Saga - Books 1-3", "Saga: 3-book collection", "Saga: 3 novels", "Saga - Volumes 1-4", "Saga - Books 1\u20133"])
@pytest.mark.parametrize("provider", ["google", "openlibrary"])
def test_mam_collection_does_not_replace_single_book_metadata(book_lookup, mam_title, provider):
    lookup = book_lookup
    lookup.mam["title"] = mam_title
    if provider == "openlibrary":
        lookup.google_search.return_value = None

    asyncio.run(gather_book_prep(lookup.meta, lookup.path, lookup.base_dir, lookup.config))

    lookup.mam_search.assert_awaited_once()
    lookup.google_search.assert_awaited_once_with(lookup.embedded["isbn"], base_dir=lookup.base_dir, api_key="")
    lookup.openlibrary_search.assert_awaited_once_with(lookup.embedded["isbn"], base_dir=lookup.base_dir)
    expected = getattr(lookup, provider)
    assert (lookup.meta.title, lookup.meta.author, lookup.meta.overview, lookup.meta.isbn) == (
        expected["title"], expected["author"], expected["overview"], lookup.embedded["isbn"]
    )
    lookup.info.assert_called_once()
    message = lookup.info.call_args.args[0].lower()
    assert "myanonamouse" in message or "mam" in message
    assert "set aside" in message
    assert "single" in message and ("collection" in message or "multiple" in message)
    assert not lookup.meta.genres
    assert not lookup.meta.keywords


@pytest.mark.parametrize(
    "case",
    ["comics_category", "same_title", "contained_title", "ordinary_wording", "missing_title", "same_isbn", "local_collection", "local_omnibus", "multiple_files"],
)
def test_mam_identity_check_preserves_ambiguous_or_matching_records(book_lookup, case, tmp_path):
    lookup = book_lookup
    lookup.mam["title"] = "Saga - Books 1-3"
    if case == "comics_category":
        lookup.mam.update(myanonamouse_manager._parse_torrent_info({"title": "The Hidden City", "catname": "Ebooks - Comics/Graphic novels"}))
    elif case == "same_title":
        lookup.embedded["title"] = "SAGA: Books 1-3"
    elif case == "contained_title":
        lookup.embedded["title"] = "The Lord of the Rings"
        lookup.mam["title"] = "The Lord of the Rings (3 books)"
    elif case == "ordinary_wording":
        lookup.mam["title"] = "How to Read 100 Books a Year"
    elif case == "missing_title":
        lookup.embedded.pop("title")
    elif case == "same_isbn":
        lookup.embedded["isbn"] = "978-0-000000-00-3"
    elif case == "local_collection":
        lookup.embedded["title"] = "The Hidden City Collection"
    elif case == "local_omnibus":
        lookup.embedded["title"] = "The Hidden City Omnibus"
    elif case == "multiple_files":
        second_book = tmp_path / "The Second Book.epub"
        second_book.write_bytes(b"ebook")
        lookup.meta.filelist.append(str(second_book))

    asyncio.run(gather_book_prep(lookup.meta, lookup.path, lookup.base_dir, lookup.config))

    assert (lookup.meta.title, lookup.meta.author, lookup.meta.overview, lookup.meta.isbn) == (
        lookup.mam["title"], lookup.mam["author"], lookup.mam["overview"], lookup.mam["isbn"]
    )
    lookup.info.assert_not_called()


@pytest.mark.parametrize("policy", ["only_id", "skip_tracker_descriptions", "config_ids"])
@pytest.mark.parametrize("provider", ["google", "openlibrary"])
def test_ids_policy_allows_per_book_overview_without_mam_description(book_lookup, policy, provider):
    lookup = book_lookup
    if policy == "config_ids":
        lookup.config["DEFAULT"]["tracker_description_mode"] = "ids"
    elif policy == "only_id":
        lookup.meta, _, _ = Args(lookup.config).parse([lookup.path, "--onlyID"], lookup.meta)
        assert lookup.meta.only_id is True
    else:
        lookup.meta.skip_tracker_descriptions = True
    if provider == "openlibrary":
        lookup.google_search.return_value = None

    asyncio.run(gather_book_prep(lookup.meta, lookup.path, lookup.base_dir, lookup.config))

    lookup.mam_search.assert_awaited_once()
    assert lookup.meta.overview == getattr(lookup, provider)["overview"]
    assert (lookup.meta.title, lookup.meta.author, lookup.meta.isbn) == (lookup.mam["title"], lookup.mam["author"], lookup.mam["isbn"])
    assert lookup.mam["overview"] == "MAM torrent description"


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("Ebooks - Horror", "Horror"),
        ("Audiobooks - Fantasy", "Fantasy"),
        ("Ebooks - Crime/Thriller", "Crime/Thriller"),
        ("Ebooks - Comics/Graphic novels", "Comics/Graphic novels"),
        ("Ebooks - Science Fiction &amp; Fantasy", "Science Fiction & Fantasy"),
    ],
)
def test_mam_category_is_genre_evidence(category, expected):
    metadata = myanonamouse_manager._parse_torrent_info({"catname": category, "tags": "horror retail collection"})

    assert metadata["genres"] == [expected]
    assert metadata["keywords"] == [expected]


def test_mam_tags_alone_are_not_genre_evidence():
    metadata = myanonamouse_manager._parse_torrent_info({"tags": "horror retail collection"})

    assert "genres" not in metadata
    assert "keywords" not in metadata


@pytest.mark.parametrize(("subjects", "accepted"), [(["Horrorroman"], True), (["Romance"], False), ([], True)])
def test_no_isbn_book_uses_openlibrary_evidence_with_mam_skipped(book_lookup, subjects, accepted):
    lookup = book_lookup
    lookup.embedded.pop("isbn")
    lookup.embedded.update(title="The Troop", author="Nick Cutter")
    lookup.meta.book_skip_mam = True
    lookup.meta.category = "BOOK"
    lookup.meta.type = "EPUB"
    lookup.meta.unattended = True
    lookup.openlibrary_title_search.return_value = {"genres": subjects, "keywords": subjects, "openlibrary": "OL19979107W"}

    asyncio.run(gather_book_prep(lookup.meta, lookup.path, lookup.base_dir, lookup.config))

    lookup.mam_search.assert_not_awaited()
    lookup.google_search.assert_not_awaited()
    lookup.openlibrary_search.assert_not_awaited()
    lookup.openlibrary_title_search.assert_awaited_once_with("The Troop", "Nick Cutter", base_dir=lookup.base_dir)
    assert lookup.meta.genres == subjects
    assert lookup.meta.keywords == subjects
    assert not lookup.meta.isbn
    assert asyncio.run(DreadVault({"TRACKERS": {"DREADVAULT": {}}}).get_additional_checks(lookup.meta)) is accepted


def test_book_genres_combine_accepted_providers_without_changing_keyword_override(book_lookup):
    lookup = book_lookup
    lookup.meta.keywords = ["manual keyword"]
    lookup.embedded["genres"] = ["Local subject"]
    lookup.mam["genres"] = ["Fiction"]
    lookup.google["genres"] = ["fiction", "Thriller"]
    lookup.openlibrary["genres"] = ["Horror fiction"]

    asyncio.run(gather_book_prep(lookup.meta, lookup.path, lookup.base_dir, lookup.config))

    assert lookup.meta.genres == ["Fiction", "Thriller", "Horror fiction", "Local subject"]
    assert lookup.meta.combined_genres == "Fiction, Thriller, Horror fiction, Local subject"
    assert lookup.meta.keywords == ["manual keyword"]
    assert lookup.meta.title == lookup.mam["title"]
