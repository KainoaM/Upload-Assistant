# ruff: noqa: S101

import asyncio
from unittest.mock import Mock

from src.google_books import google_books_manager
from src.metadata_cache import cache_for


def test_google_books_normalizes_cached_cover_url(tmp_path, monkeypatch):
    async def run():
        isbn = "9780000000001"
        metadata = {
            "isbn": isbn,
            "title": "Cached book",
            "artwork_url": "http://books.google.com/books/content?id=volume&zoom=1&edge=curl&source=gbs_api",
        }
        cache = cache_for(tmp_path)
        await cache.set("google_books", "isbn", isbn, metadata)
        network = Mock(side_effect=AssertionError("Google Books cache hit attempted a network request"))
        monkeypatch.setattr("src.google_books.httpx.AsyncClient", network)

        result = await google_books_manager.search_by_isbn(isbn, str(tmp_path))

        assert result == {**metadata, "artwork_url": "http://books.google.com/books/content?id=volume&zoom=0&source=gbs_api"}
        network.assert_not_called()

    asyncio.run(run())
