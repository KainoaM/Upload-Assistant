# ruff: noqa: S101
import logging
import posixpath
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch
from urllib.parse import unquote

import pytest
from PIL import Image

from src.console import logger
from src.meta import Meta
from src.takescreens import extract_epub_cover, prepare_book_cover


def _write_epub(path: Path, declaration: str, opf_path: str = "OEBPS/package.opf", href: str = "images/cover.jpg", *, missing_cover: bool = False) -> bytes:
    image = BytesIO()
    Image.new("RGB", (600, 900), "blue").save(image, format="JPEG")
    cover_bytes = image.getvalue()
    properties = ' properties="cover-image"' if declaration == "properties" else ""
    metadata = '<meta name="cover" content="retail-artwork"/>' if declaration == "meta" else ""
    item_id = "coverimg" if declaration == "properties" else "retail-artwork"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "META-INF/container.xml",
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
            f'<rootfiles><rootfile full-path="{opf_path}" media-type="application/oebps-package+xml"/></rootfiles></container>',
        )
        archive.writestr(
            opf_path,
            '<package xmlns="http://www.idpf.org/2007/opf" version="3.0">'
            f'<metadata>{metadata}</metadata><manifest>'
            f'<item id="{item_id}" href="{href}" media-type="image/jpeg"{properties}/>'
            "</manifest></package>",
        )
        if not missing_cover:
            archive.writestr(posixpath.normpath(posixpath.join(posixpath.dirname(opf_path), unquote(href))), cover_bytes)
    return cover_bytes


@pytest.mark.asyncio
@pytest.mark.parametrize("declaration", ["properties", "meta"])
@pytest.mark.parametrize("opf_path", ["OEBPS/package.opf", "OEBPS/Package/package.opf"])
@pytest.mark.parametrize("href", ["images/cover.jpg", "../images/cover%20art.jpg"])
@pytest.mark.parametrize("confirmed_only", [True, False])
async def test_declared_epub_cover_preserves_full_image(tmp_path: Path, declaration: str, opf_path: str, href: str, confirmed_only: bool) -> None:
    book = tmp_path / "book.epub"
    cover_bytes = _write_epub(book, declaration, opf_path, href)
    destination = tmp_path / "cover.jpg"

    assert await extract_epub_cover(str(book), str(destination), confirmed_only=confirmed_only)
    assert destination.read_bytes() == cover_bytes
    with Image.open(destination) as cover:
        cover.load()
        assert cover.format == "JPEG"
        assert cover.size == (600, 900)


@pytest.mark.asyncio
async def test_missing_declared_epub_cover_logs_and_falls_through(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    book = tmp_path / "book.epub"
    cover_bytes = _write_epub(book, "properties", missing_cover=True)
    destination = tmp_path / "cover.jpg"
    caplog.set_level(logging.DEBUG, logger=logger.name)

    assert not await extract_epub_cover(str(book), str(destination), confirmed_only=True)
    assert not destination.exists()
    assert any(
        record.levelno == logging.DEBUG
        and "OEBPS/images/cover.jpg" in record.message
        and ("missing" in record.message.lower() or "not found" in record.message.lower())
        for record in caplog.records
    )

    meta = Meta(category="BOOK", base_dir=str(tmp_path), uuid="book-cover", artwork_url="https://example.com/cover.jpg")

    async def download(_meta, destination, *, force):
        Path(destination).write_bytes(cover_bytes)
        return True

    with patch("src.takescreens.download_artwork_from_meta", new=AsyncMock(side_effect=download)) as provider:
        result = await prepare_book_cover(str(book), meta.uuid, meta.base_dir, meta)

    provider.assert_awaited_once()
    assert result == meta.artwork_path
    assert Path(result).read_bytes() == cover_bytes


@pytest.mark.asyncio
async def test_malformed_epub_opf_logs_parse_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    book = tmp_path / "malformed.epub"
    destination = tmp_path / "cover.jpg"
    with zipfile.ZipFile(book, "w") as archive:
        archive.writestr("OEBPS/package.opf", "<package><manifest></package>")
    caplog.set_level(logging.DEBUG, logger=logger.name)

    assert not await extract_epub_cover(str(book), str(destination), confirmed_only=True)
    assert not destination.exists()
    assert any(record.levelno == logging.DEBUG and str(book) in record.message and "mismatched tag" in record.message for record in caplog.records)
