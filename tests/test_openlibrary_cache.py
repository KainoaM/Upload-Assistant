# ruff: noqa: S101

import asyncio
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from src.metadata_cache import cache_for, is_cache_miss
from src.openlibrary import openlibrary_manager


def _fail_if_network(*_args, **_kwargs):
    raise AssertionError("OpenLibrary cache hit attempted a network request")


class _Response:
    status_code = 200

    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data

    def raise_for_status(self):
        return None


class _Client:
    def __init__(self, data):
        self.data = data
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, *_args, **_kwargs):
        self.requests.append((_args, _kwargs))
        return _Response(self.data)


def test_openlibrary_uses_central_cache_for_metadata_and_authors(tmp_path, monkeypatch):
    async def run():
        monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", _fail_if_network)
        cache = cache_for(tmp_path)
        await cache.set("openlibrary", "work", "OL1W", {"title": "Cached work"})
        await cache.set("openlibrary", "isbn", "9780000000001", {"title": "Cached ISBN"})
        await cache.set("openlibrary", "author", "OL1A", {"name": "Cached author"})
        await cache.set("openlibrary", "work", "OL404W", {"not_found": True}, negative=True)

        assert await openlibrary_manager.search_by_work_id("OL1W", tmp_path) == {"title": "Cached work"}
        assert await openlibrary_manager.search_by_isbn("978-0000000001", tmp_path) == {"title": "Cached ISBN"}
        assert await openlibrary_manager.get_author_name("/authors/OL1A", None, cache) == "Cached author"
        assert await openlibrary_manager.search_by_work_id("OL404W", tmp_path) is None
        assert not (tmp_path / "tmp" / "openlibrary_cache").exists()

    asyncio.run(run())


def test_openlibrary_ignores_null_cover_ids(tmp_path, monkeypatch):
    async def run():
        monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", lambda **_kwargs: _Client({"title": "No cover", "covers": [None]}))

        metadata = await openlibrary_manager.search_by_work_id("OL2W", tmp_path)

        assert metadata == {"title": "No cover", "openlibrary": "OL2W"}

    asyncio.run(run())


def test_openlibrary_title_author_matches_exactly_and_caches_work_id(tmp_path, monkeypatch):
    async def run():
        client = _Client(
            {
                "docs": [
                    {"key": "/works/OL1W", "title": "The Troop", "author_name": ["Nick Cutter"]},
                    {"key": "/works/OL2W", "title": "The Troop Collection", "author_name": ["Nick Cutter"]},
                ]
            }
        )
        monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", lambda **_kwargs: client)
        metadata = {"title": "The Troop", "keywords": ["Horror fiction"], "genres": ["Horror fiction"], "openlibrary": "OL1W"}
        await cache_for(tmp_path).set("openlibrary", "work", "OL1W", metadata)

        assert await openlibrary_manager.search_by_title_author("  THE   TROOP ", "Nick  Cutter", tmp_path) == metadata
        assert client.requests[0][0] == ("https://openlibrary.org/search.json",)
        assert client.requests[0][1]["params"] == {"title": "the troop", "author": "nick cutter", "fields": "key,title,author_name", "limit": 10}
        assert await cache_for(tmp_path).get("openlibrary", "title_author", "the troop\nnick cutter") == {"work_id": "OL1W"}

        network = Mock(side_effect=_fail_if_network)
        monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", network)
        assert await openlibrary_manager.search_by_title_author("The Troop", "Nick Cutter", tmp_path) == metadata
        network.assert_not_called()

    asyncio.run(run())


@pytest.mark.parametrize(
    "docs",
    [
        [],
        [{"key": "/works/OL1W", "title": "The Troop Collection", "author_name": ["Nick Cutter"]}],
        [{"key": "/works/OL1W", "title": "The Troop", "author_name": ["Other Author"]}],
        [{"key": "/works/OL1W", "title": "The Troop"}],
        [{"title": "The Troop", "author_name": ["Nick Cutter"]}],
        [{"key": "/books/OL1M", "title": "The Troop", "author_name": ["Nick Cutter"]}],
        [
            {"key": "/works/OL1W", "title": "The Troop", "author_name": ["Nick Cutter"]},
            {"key": "/works/OL2W", "title": "The Troop", "author_name": ["Nick Cutter"]},
        ],
    ],
)
def test_openlibrary_title_author_rejects_missing_wrong_or_ambiguous_matches(tmp_path, monkeypatch, docs):
    async def run():
        monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", lambda **_kwargs: _Client({"docs": docs}))
        work_search = AsyncMock()
        monkeypatch.setattr(openlibrary_manager, "search_by_work_id", work_search)

        assert await openlibrary_manager.search_by_title_author("The Troop", "Nick Cutter", tmp_path) is None
        work_search.assert_not_awaited()
        assert await cache_for(tmp_path).get("openlibrary", "title_author", "the troop\nnick cutter") == {"not_found": True}
        network = Mock(side_effect=_fail_if_network)
        monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", network)
        assert await openlibrary_manager.search_by_title_author("The Troop", "Nick Cutter", tmp_path) is None
        network.assert_not_called()

    asyncio.run(run())


def test_openlibrary_title_author_rejects_truncated_results(tmp_path, monkeypatch):
    async def run():
        data = {"numFound": 11, "docs": [{"key": "/works/OL1W", "title": "The Troop", "author_name": ["Nick Cutter"]}]}
        monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", lambda **_kwargs: _Client(data))
        work_search = AsyncMock()
        monkeypatch.setattr(openlibrary_manager, "search_by_work_id", work_search)

        assert await openlibrary_manager.search_by_title_author("The Troop", "Nick Cutter", tmp_path) is None
        work_search.assert_not_awaited()

    asyncio.run(run())


@pytest.mark.parametrize(("title", "author"), [("", "Nick Cutter"), ("The Troop", "  ")])
def test_openlibrary_title_author_requires_both_identity_fields(tmp_path, monkeypatch, title, author):
    monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", _fail_if_network)
    assert asyncio.run(openlibrary_manager.search_by_title_author(title, author, tmp_path)) is None


@pytest.mark.parametrize("failure", [httpx.ReadTimeout("Timed out"), httpx.HTTPStatusError("Service unavailable", request=None, response=None)])
def test_openlibrary_title_author_does_not_cache_network_failures(tmp_path, monkeypatch, failure):
    async def run():
        client = _Client({})
        client.get = AsyncMock(side_effect=failure)
        monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", lambda **_kwargs: client)

        assert await openlibrary_manager.search_by_title_author("The Troop", "Nick Cutter", tmp_path) is None
        assert is_cache_miss(await cache_for(tmp_path).get("openlibrary", "title_author", "the troop\nnick cutter"))

    asyncio.run(run())


def test_openlibrary_preserves_work_subjects_beyond_tenth(tmp_path, monkeypatch):
    async def run():
        subjects = [f"Subject {index}" for index in range(10)] + [" Horror fiction ", "", " ", None]
        monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", lambda **_kwargs: _Client({"title": "The Troop", "subjects": subjects}))

        metadata = await openlibrary_manager.search_by_work_id("OL1W", tmp_path)

        assert metadata["genres"] == metadata["keywords"] == [*subjects[:10], "Horror fiction"]
        assert metadata["genres"] is not metadata["keywords"]

    asyncio.run(run())


@pytest.mark.parametrize("work", [None, {"title": "The Troop", "openlibrary": "OL1W"}])
def test_openlibrary_preserves_edition_subjects_without_work_subjects(tmp_path, monkeypatch, work):
    async def run():
        details = {"title": "The Troop", "subjects": [" Horror fiction ", ""], "works": [{"key": "/works/OL1W"}]}
        monkeypatch.setattr("src.openlibrary.httpx.AsyncClient", lambda **_kwargs: _Client({"ISBN:9780000000001": {"details": details}}))
        monkeypatch.setattr(openlibrary_manager, "search_by_work_id", AsyncMock(return_value=work))

        metadata = await openlibrary_manager.search_by_isbn("9780000000001", tmp_path)

        assert metadata["genres"] == metadata["keywords"] == ["Horror fiction"]

    asyncio.run(run())
