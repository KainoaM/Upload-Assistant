# ruff: noqa: S101

import asyncio

import pytest

from src.get_desc import DescriptionBuilder
from src.meta import Meta


def _image(name):
    return {"web_url": f"https://example.com/{name}", "raw_url": f"https://example.com/{name}.jpg", "img_url": f"https://example.com/{name}-thumb.jpg"}


@pytest.fixture
def book(tmp_path):
    (tmp_path / "tmp" / "book").mkdir(parents=True)
    builder = DescriptionBuilder("TEST", {"DEFAULT": {}, "TRACKERS": {"TEST": {}}})
    meta = Meta(base_dir=str(tmp_path), uuid="book", category="BOOK", author="An Author", overview="Book overview.", description="Release notes.", screens=2, filelist=["Book.epub"])
    return builder, meta


def _render(builder, meta, **kwargs):
    return asyncio.run(
        builder.general_description_generator(
            meta,
            audio_spectrogram=False,
            bluray=False,
            custom_header=False,
            custom_signature=False,
            game=False,
            languages=False,
            logo=False,
            mediainfo=False,
            menu_screenshots=False,
            nfo=False,
            tonemapped_header=False,
            tv_info=False,
            ua_signature=False,
            user_description=False,
            music=False,
            dynamic_hdr_plot=False,
            **kwargs,
        )
    )


@pytest.mark.parametrize(
    "tracker,config,cover_tag,center,details",
    [
        ("TEST", {}, "[url=https://example.com/cover][img=350]https://example.com/cover.jpg[/img][/url] ", "[center]", "[h2]Technical Details[/h2]"),
        ("TEST", {"thumbnail_size": 240}, "[url=https://example.com/cover][img=240]https://example.com/cover.jpg[/img][/url] ", "[center]", "[h2]Technical Details[/h2]"),
        ("BJSHARE", {}, "[url=https://example.com/cover][img]https://example.com/cover.jpg[/img][/url] ", "[align=center]", "[size=3][b]Technical Details"),
        ("IPTORRENTS", {}, "[url=https://example.com/cover][img]https://example.com/cover-thumb.jpg[/img][/url]\n", "[center]", "[b]Technical Details[/b]"),
    ],
    ids=["stock", "thumbnail-size", "alignment", "plain-details"],
)
def test_book_hosted_cover_precedes_details(book, tracker, config, cover_tag, center, details):
    _, meta = book
    builder = DescriptionBuilder(tracker, {"DEFAULT": {}, "TRACKERS": {tracker: config}})
    meta.hosted_artwork = [_image("cover")]

    description = _render(builder, meta)

    assert description.startswith(center + cover_tag)
    assert description.count(cover_tag) == 1
    assert description.index(cover_tag) < description.index(details)


def test_book_without_hosted_cover_is_unchanged(book):
    builder, meta = book
    meta.artwork_url = "https://example.com/provider-cover.jpg"
    meta.image_list = [_image("page")]

    description = _render(builder, meta)

    assert description.encode("utf-8") == (
        b"[h2]Technical Details[/h2]\n\n"
        b"[table]\n[tr][td][b]Author[/b][/td][td]An Author[/td][/tr]\n[/table]\n\n"
        b"[h2]Overview[/h2]\nBook overview.\nRelease notes.\n"
        b"\n[center][url=https://example.com/page][img=350]https://example.com/page.jpg[/img][/url] [/center]"
    )


def test_non_book_with_hosted_artwork_is_unchanged(book):
    builder, meta = book
    meta.category = "MOVIE"
    meta.hosted_artwork = [_image("cover")]
    meta.rehosted_artwork_url = meta.hosted_artwork[0]["raw_url"]
    meta.image_list = [_image("cover")]

    description = _render(builder, meta)

    assert description.encode("utf-8") == (
        b"Release notes.\n\n[center][url=https://example.com/cover][img=350]https://example.com/cover.jpg[/img][/url] [/center]"
    )


@pytest.mark.parametrize("tracker_override", [False, True])
def test_book_cover_in_screenshots_is_rendered_once_at_top(book, tracker_override):
    builder, meta = book
    cover = _image("cover")
    screenshots = [cover, _image("page")]
    meta.hosted_artwork = [cover]
    meta.image_list = screenshots
    if tracker_override:
        meta.image_list = [_image("unused")]
        meta.tracker_image_collections = {"TEST": {"screenshots": screenshots}}

    description = _render(builder, meta)

    assert description.count("[img=350]https://example.com/cover.jpg[/img]") == 1
    assert description.index(cover["raw_url"]) < description.index("Technical Details")
    assert _image("page")["raw_url"] in description
    assert screenshots == [cover, _image("page")]


def test_book_with_only_rehosted_cover_and_no_details(book):
    builder, meta = book
    meta.author = ""
    meta.overview = ""
    meta.description = ""
    meta.rehosted_artwork_url = "https://example.com/cover.jpg"

    description = _render(builder, meta, screenshots=False)

    assert description == "[center][url=https://example.com/cover.jpg][img=350]https://example.com/cover.jpg[/img][/url] [/center]"
