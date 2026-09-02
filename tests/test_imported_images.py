# ruff: noqa: S101
import asyncio
from types import SimpleNamespace

import httpx
import pytest

from src.trackers import common
from src.trackers.common import filter_imported_screenshots, is_screenshot_shape, read_image_dimensions


@pytest.mark.parametrize(
    ("image", "video", "expected"),
    [
        ((1024, 1024), (1920, 960), False),
        ((178, 100), (1920, 1036), False),
        ((3000, 1200), (1920, 804), True),
        ((784, 308), (1920, 800), True),
        ((720, 480), (853, 480), True),
    ],
)
def test_is_screenshot_shape(image: tuple[int, int], video: tuple[int, int], expected: bool) -> None:
    assert is_screenshot_shape(*image, *video) is expected


def test_read_image_dimensions_from_png_and_jpeg_headers(monkeypatch) -> None:
    png = b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR" + (1920).to_bytes(4, "big") + (804).to_bytes(4, "big")
    jpeg = (
        b"\xff\xd8"
        + b"\xff\xe0\x00\x04\x00\x00"
        + b"\xff\xc0\x00\x0b\x08"
        + (960).to_bytes(2, "big")
        + (1920).to_bytes(2, "big")
        + b"\x00\x00\x00\x00"
    )
    headers = {"https://example.test/image.png": png, "https://example.test/image.jpg": jpeg}
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(206, content=headers[str(request.url)])

    async_client = httpx.AsyncClient

    def client(*args, **kwargs):
        return async_client(*args, transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(common.httpx, "AsyncClient", client)

    assert asyncio.run(read_image_dimensions("https://example.test/image.png")) == (1920, 804)
    assert asyncio.run(read_image_dimensions("https://example.test/image.jpg")) == (1920, 960)
    assert all(request.headers["Range"] == "bytes=0-65535" for request in requests)


@pytest.mark.parametrize(
    "meta",
    [
        SimpleNamespace(video_width=None, video_height=960, is_disc=False),
        SimpleNamespace(video_width=1920, video_height=960, is_disc="BDMV"),
    ],
)
def test_filter_keeps_all_images_without_reliable_video_shape(meta, monkeypatch) -> None:
    images = [{"raw_url": "https://example.test/logo.png"}]
    called = False

    async def unexpected_read(_url: str) -> tuple[int, int] | None:
        nonlocal called
        called = True
        return 1024, 1024

    monkeypatch.setattr(common, "read_image_dimensions", unexpected_read)

    assert asyncio.run(filter_imported_screenshots(images, meta)) == images
    assert called is False


def test_filter_keeps_image_when_dimensions_cannot_be_read(monkeypatch) -> None:
    images = [
        {"raw_url": "https://example.test/logo"},
        {"raw_url": "https://example.test/screenshot"},
        {"raw_url": "https://example.test/unknown"},
    ]
    meta = SimpleNamespace(video_width=1920, video_height=960, is_disc=False)

    async def dimensions(url: str) -> tuple[int, int] | None:
        return {
            "https://example.test/logo": (1024, 1024),
            "https://example.test/screenshot": (1920, 960),
            "https://example.test/unknown": None,
        }[url]

    monkeypatch.setattr(common, "read_image_dimensions", dimensions)

    assert asyncio.run(filter_imported_screenshots(images, meta)) == images[1:]
