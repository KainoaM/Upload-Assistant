# ruff: noqa: S101
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from PIL import Image

from src.artwork import is_valid_cover_image
from src.google_books import google_books_manager
from src.meta import Meta
from src.takescreens import extract_epub_cover, prepare_book_cover


@pytest.mark.parametrize("query", ["id=volume&zoom=1&edge=curl", "edge=curl&zoom=1&id=volume", "id=volume&zoom=1&edge=curl&printsec=frontcover"])
def test_google_books_requests_large_cover_without_curl(query: str) -> None:
    metadata = google_books_manager._parse_volume_info(
        {"totalItems": 1, "items": [{"id": "volume", "volumeInfo": {"imageLinks": {"thumbnail": f"https://books.google.com/books/content?{query}"}}}]},
        "9780000000002",
    )

    assert metadata is not None
    cover_url = urlsplit(metadata["artwork_url"])
    expected_query = parse_qs(query)
    expected_query["zoom"] = ["0"]
    del expected_query["edge"]
    assert parse_qs(cover_url.query) == expected_query
    assert (cover_url.scheme, cover_url.netloc, cover_url.path) == ("https", "books.google.com", "/books/content")


@pytest.mark.asyncio
@pytest.mark.parametrize("audiobook", [False, True], ids=["epub", "audiobook"])
async def test_invalid_confirmed_cover_falls_through_to_provider(tmp_path: Path, audiobook: bool) -> None:
    meta = Meta(category="BOOK", base_dir=str(tmp_path), uuid="book-cover", audiobook=audiobook, artwork_url="https://example.com/cover.png")

    async def extract(_source, destination, *, confirmed_only):
        assert confirmed_only
        Path(destination).write_bytes(b"invalid extracted image")
        return True

    async def download(_meta, destination, *, force):
        assert not meta.artwork_path
        assert not is_valid_cover_image(destination)
        Image.new("RGB", (32, 48), "green").save(destination)
        return True

    extractor = "extract_embedded_cover_from_audiobook" if audiobook else "extract_epub_cover"
    with (
        patch(f"src.takescreens.{extractor}", new=AsyncMock(side_effect=extract)),
        patch("src.takescreens.download_artwork_from_meta", new=AsyncMock(side_effect=download)) as provider,
    ):
        result = await prepare_book_cover("book.epub", meta.uuid, meta.base_dir, meta)

    provider.assert_awaited_once()
    assert result == meta.artwork_path
    assert is_valid_cover_image(result)
    with Image.open(result) as cover:
        assert cover.getpixel((0, 0)) == (0, 128, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("extension", "audiobook", "extractor"),
    [("epub", False, "extract_epub_cover"), ("m4b", True, "extract_embedded_cover_from_audiobook"), ("pdf", False, "extract_document_cover")],
)
async def test_invalid_fallback_cover_is_not_adopted(tmp_path: Path, extension: str, audiobook: bool, extractor: str) -> None:
    meta = Meta(category="BOOK", base_dir=str(tmp_path), uuid="book-cover", audiobook=audiobook)

    async def extract(_source, destination, *, confirmed_only=False):
        if confirmed_only:
            return False
        Path(destination).write_bytes(b"invalid extracted image")
        return True

    with (
        patch(f"src.takescreens.{extractor}", new=AsyncMock(side_effect=extract)) as extraction,
        patch("src.takescreens.download_artwork_from_meta", new=AsyncMock(return_value=False)) as provider,
    ):
        result = await prepare_book_cover(f"book.{extension}", meta.uuid, meta.base_dir, meta)

    assert result is None
    assert not meta.artwork_path
    assert extraction.await_count == (1 if extension == "pdf" else 2)
    provider.assert_awaited_once()


@pytest.mark.asyncio
async def test_epub_cover_filename_fallback_skips_svg(tmp_path: Path) -> None:
    raster = tmp_path / "source.png"
    Image.new("RGB", (32, 48), "blue").save(raster)
    book = tmp_path / "book.epub"
    with zipfile.ZipFile(book, "w") as archive:
        archive.writestr("content.opf", "<package><manifest/></package>")
        archive.writestr("cover.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
        archive.writestr("cover.png", raster.read_bytes())
    destination = tmp_path / "POSTER.png"

    assert await extract_epub_cover(str(book), str(destination))
    assert destination.read_bytes() == raster.read_bytes()
