# ruff: noqa: S101
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from PIL import Image

from src.args import Args
from src.artwork import is_valid_cover_image, prepare_artwork
from src.meta import Meta
from src.temp_paths import artwork_dir
from src.trackerhandle import process_trackers
from src.trackers.UNIT3D import UNIT3D
from upload import _prompt_book_meta, _prompt_music_meta
import upload


@pytest.fixture(autouse=True)
def setup_globals():
    upload.load_heavy_globals()


@pytest.mark.asyncio
async def test_prompt_book_meta_accepts_file_path(tmp_path: Path) -> None:
    cover_file = tmp_path / "cover.jpg"
    Image.new("RGB", (32, 48), "red").save(cover_file)

    meta = Meta(category="BOOK", title="Test Book", author="Test Author", year=2024, book_language="English", book_language_iso="eng")

    with patch("upload.CLI_UI.ask_string", return_value=str(cover_file)):
        await _prompt_book_meta(meta)

    assert meta.artwork_path == str(cover_file.resolve())


@pytest.mark.asyncio
async def test_prompt_book_meta_accepts_url() -> None:
    meta = Meta(category="BOOK", title="Test Book", author="Test Author", year=2024, book_language="English", book_language_iso="eng")

    with patch("upload.CLI_UI.ask_string", return_value="https://example.com/cover.jpg"):
        await _prompt_book_meta(meta)

    assert meta.artwork_url == "https://example.com/cover.jpg"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("image_names", "expected", "single_file"),
    [
        (("book.jpg",), "book.jpg", False),
        (("cover.png",), "cover.png", False),
        (("alpha.jpg", "beta.png"), None, False),
        ((), None, False),
        (("book.JPEG", "cover.png"), "book.JPEG", False),
        (("FRONT.WebP", "random.jpg"), "FRONT.WebP", False),
        (("folder.png", "random.jpg"), "folder.png", False),
        (("poster.png", "random.jpg"), "poster.png", False),
        (("random.jpg",), "random.jpg", False),
        (("book.jpg", "cover.png"), "book.jpg", True),
    ],
)
async def test_book_artwork_discovers_release_cover(tmp_path: Path, image_names: tuple[str, ...], expected: str | None, single_file: bool) -> None:
    book = tmp_path / "book.epub"
    book.touch()
    for name in image_names:
        Image.new("RGB", (32, 48), "blue").save(tmp_path / name)
    originals = {name: (tmp_path / name).read_bytes() for name in image_names}
    meta = Meta(category="BOOK", path=str(book if single_file else tmp_path), base_dir=str(tmp_path), uuid="book-artwork")

    with patch("upload.logger.info") as log:
        assert await upload._ensure_valid_book_artwork(meta) is (expected is not None)

    if expected:
        cover = artwork_dir(meta.base_dir, meta.uuid) / "POSTER.png"
        assert Path(meta.artwork_path) == cover
        assert cover.is_file()
        assert is_valid_cover_image(cover)
        assert cover.read_bytes() == originals[expected]
        log.assert_any_call(f"[green]BOOK upload: using local cover artwork: {expected}[/green]")
    else:
        assert meta.artwork_path == ""
    for name, content in originals.items():
        assert (tmp_path / name).is_file()
        assert (tmp_path / name).read_bytes() == content


@pytest.mark.asyncio
async def test_book_artwork_skips_invalid_matching_image(tmp_path: Path) -> None:
    (tmp_path / "book.epub").touch()
    (tmp_path / "book.jpg").write_bytes(b"not an image")
    cover = tmp_path / "cover.png"
    Image.new("RGB", (32, 48), "green").save(cover)
    meta = Meta(category="BOOK", path=str(tmp_path), base_dir=str(tmp_path), uuid="book-artwork")

    assert await upload._ensure_valid_book_artwork(meta)
    assert Path(meta.artwork_path) == artwork_dir(meta.base_dir, meta.uuid) / "POSTER.png"
    assert is_valid_cover_image(meta.artwork_path)
    assert Path(meta.artwork_path).read_bytes() == cover.read_bytes()


@pytest.mark.asyncio
async def test_book_artwork_does_not_copy_poster_onto_itself(tmp_path: Path) -> None:
    meta = Meta(category="BOOK", base_dir=str(tmp_path), uuid="book-artwork")
    directory = artwork_dir(meta.base_dir, meta.uuid)
    (directory / "book.epub").touch()
    cover = directory / "POSTER.png"
    Image.new("RGB", (32, 48), "blue").save(cover)
    original = cover.read_bytes()
    meta.path = str(directory)

    with patch("upload.shutil.copy2") as copy:
        assert await upload._ensure_valid_book_artwork(meta)

    copy.assert_not_called()
    assert Path(meta.artwork_path) == cover
    assert is_valid_cover_image(cover)
    assert cover.read_bytes() == original


@pytest.mark.asyncio
@pytest.mark.parametrize("copy_error", [True, False], ids=["copy-error", "invalid-copy"])
async def test_book_artwork_rejects_failed_copy(tmp_path: Path, copy_error: bool) -> None:
    (tmp_path / "book.epub").touch()
    source = tmp_path / "book.jpg"
    Image.new("RGB", (32, 48), "blue").save(source)
    original = source.read_bytes()
    meta = Meta(category="BOOK", path=str(tmp_path), base_dir=str(tmp_path), uuid="book-artwork")

    def copy_cover(_source: Path, destination: Path) -> None:
        if copy_error:
            raise OSError("copy failed")
        destination.write_bytes(b"not an image")

    with patch("upload.shutil.copy2", side_effect=copy_cover):
        assert not await upload._ensure_valid_book_artwork(meta)

    assert meta.artwork_path == ""
    assert source.read_bytes() == original


@pytest.mark.asyncio
async def test_book_artwork_does_not_search_parent_or_nested_directories(tmp_path: Path) -> None:
    release = tmp_path / "release"
    nested = release / "unrelated"
    nested.mkdir(parents=True)
    (release / "book.epub").touch()
    for directory in (tmp_path, nested):
        Image.new("RGB", (32, 48), "blue").save(directory / "cover.jpg")
    meta = Meta(category="BOOK", path=str(release))

    assert not await upload._ensure_valid_book_artwork(meta)
    assert meta.artwork_path == ""


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("unattended", "responses"),
    [(False, ["", "", ""]), (False, [EOFError()]), (True, [])],
    ids=["empty", "eof", "unattended"],
)
@pytest.mark.parametrize("skip_mam", ["unset", "meta", "config"])
async def test_book_artwork_retry_stops_without_input(tmp_path: Path, unattended: bool, responses: list[str | Exception], skip_mam: str) -> None:
    meta = Meta(
        category="BOOK",
        path=str(tmp_path),
        base_dir=str(tmp_path),
        uuid="missing-cover",
        title="Test Book",
        author="Test Author",
        year=2024,
        book_language="English",
        book_language_iso="eng",
        imghost="imgbox",
        trackers=["TEST"],
        unattended=unattended,
        book_skip_mam=skip_mam == "meta",
    )
    (tmp_path / "tmp" / meta.uuid).mkdir(parents=True)
    defaults = {"auto_mode": unattended}
    if skip_mam == "config":
        defaults["book_skip_mam"] = True
    with (
        patch("upload.config", {"DEFAULT": defaults, "TRACKERS": {}}),
        patch("upload.Prep") as prep,
        patch("upload.name_manager.get_name", new=AsyncMock(return_value=("Test Book", "Test Book", "Test Book", []))),
        patch("upload.gen_desc", new=AsyncMock(return_value=meta)),
        patch("upload.UploadHelper.get_confirmation", new=AsyncMock(return_value=True)),
        patch("upload.CLI_UI.ask_string", side_effect=[*responses, AssertionError("BOOK artwork prompt did not terminate")]) as prompt,
        patch("upload.logger.info") as log,
    ):
        prep.return_value.gather_prep = AsyncMock(return_value=meta)
        assert await upload.process_meta(meta, str(tmp_path))

    assert prompt.call_count == len(responses)
    assert meta.trackers == []
    assert meta.artwork_path == ""
    assert meta.artwork_url == ""
    messages = [call.args[0] for call in log.call_args_list if "no valid cover could be obtained" in call.args[0]]
    assert len(messages) == 1
    assert "--poster with a cover image path or URL" in messages[0]
    assert ("book_skip_mam is enabled; disable it to try MAM cover lookup if you have a MAM account" in messages[0]) is (skip_mam != "unset")
    assert "\n" not in messages[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("skip_mam", ["unset", "meta", "config"])
@pytest.mark.parametrize("invalid_cover", [False, True])
async def test_book_upload_guard_explains_missing_cover(tmp_path: Path, skip_mam: str, invalid_cover: bool) -> None:
    meta = Meta(category="BOOK", trackers=["TEST"], tracker_status={"TEST": {"upload": True}}, book_skip_mam=skip_mam == "meta")
    if invalid_cover:
        cover = tmp_path / "cover.jpg"
        cover.write_bytes(b"not an image")
        meta.artwork_path = str(cover)
    defaults = {"smart_image_host_selection": False}
    if skip_mam == "config":
        defaults["book_skip_mam"] = True
    tracker = Mock()
    with (
        patch("src.trackerhandle.TrackerSetup.trackers_enabled", return_value=["TEST"]),
        patch("src.trackerhandle.logger.info") as log,
    ):
        await process_trackers(meta, {"DEFAULT": defaults, "TRACKERS": {}}, None, ["TEST"], {"TEST": tracker}, [], [])

    assert meta.tracker_status["TEST"]["upload"] is False
    message = meta.tracker_status["TEST"]["status_message"]
    assert "no valid BOOK cover could be obtained; supply --poster with a cover image path or URL" in message
    assert ("book_skip_mam is enabled; disable it to try MAM cover lookup if you have a MAM account" in message) is (skip_mam != "unset")
    assert "\n" not in message
    log.assert_any_call(f"[yellow]TEST: {message}[/yellow]")
    tracker.return_value.upload.assert_not_called()


@pytest.mark.asyncio
async def test_prompt_music_meta_accepts_file_path(tmp_path: Path) -> None:
    cover_file = tmp_path / "album_cover.png"
    Image.new("RGB", (32, 48), "purple").save(cover_file)

    meta = Meta(
        category="MUSIC",
        artist="Test Artist",
        title="Test Album",
        year=2024,
        source="CD",
        music_release={"fields": {"release_type": {"value": "Album"}}},
    )

    with patch("upload.CLI_UI.ask_string", return_value=str(cover_file)):
        await _prompt_music_meta(meta)

    assert meta.artwork_path == str(cover_file.resolve())


@pytest.mark.asyncio
async def test_prompt_music_meta_rejects_invalid_file_before_accepting_cover(tmp_path: Path) -> None:
    invalid_file = tmp_path / "invalid.png"
    invalid_file.write_bytes(b"not an image")
    valid_file = tmp_path / "valid.png"
    Image.new("RGB", (32, 48), "orange").save(valid_file)

    meta = Meta(
        category="MUSIC",
        artist="Test Artist",
        title="Test Album",
        year=2024,
        source="CD",
        music_release={"fields": {"release_type": {"value": "Album"}}},
    )

    with patch("upload.CLI_UI.ask_string", side_effect=[str(invalid_file), str(valid_file)]):
        await _prompt_music_meta(meta)

    assert meta.artwork_path == str(valid_file.resolve())


@pytest.mark.asyncio
async def test_generic_artwork_cli_args_normalize_local_images(tmp_path: Path) -> None:
    cover_file = tmp_path / "cli_cover.png"
    banner_file = tmp_path / "cli_banner.jpg"
    Image.new("RGB", (32, 48), "blue").save(cover_file)
    Image.new("RGB", (96, 32), "red").save(banner_file)

    parser = Args({"DEFAULT": {"screens": 4, "img_host_1": "imgbox"}})
    meta = Meta(category="BOOK", base_dir=str(tmp_path), uuid="generic-artwork")
    parser.parse([str(tmp_path), "--poster", str(cover_file), "--banner", str(banner_file)], meta)
    await prepare_artwork(meta)

    artwork = tmp_path / "tmp" / "generic-artwork" / "artwork"
    assert meta.artwork_path == str(artwork / "POSTER.png")
    assert meta.artwork_banner_path == str(artwork / "POSTER_BANNER.png")
    assert Image.open(meta.artwork_path).format == "PNG"
    assert Image.open(meta.artwork_banner_path).format == "PNG"


@pytest.mark.asyncio
async def test_generic_poster_url_is_normalized_and_retained(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (32, 48), "green").save(source)
    meta = Meta(base_dir=str(tmp_path), uuid="url-artwork", explicit_poster="https://images.example/poster.jpg")

    with patch("src.artwork._download_public_image", new=AsyncMock(return_value=source.read_bytes())):
        await prepare_artwork(meta)

    assert meta.artwork_url == "https://images.example/poster.jpg"
    assert meta.artwork_path == str(tmp_path / "tmp" / "url-artwork" / "artwork" / "POSTER.png")
    assert Image.open(meta.artwork_path).format == "PNG"


@pytest.mark.asyncio
async def test_local_artwork_discovery_normalizes_named_poster_and_banner(tmp_path: Path) -> None:
    media_file = tmp_path / "Release.mkv"
    media_file.touch()
    Image.new("RGB", (32, 48), "blue").save(tmp_path / "Release.Cover.jpg")
    Image.new("RGB", (96, 32), "red").save(tmp_path / "Release-Banner.webp")
    meta = Meta(base_dir=str(tmp_path), uuid="discovered-artwork", path=str(media_file), artwork_url="https://metadata.example/poster.jpg")

    await prepare_artwork(meta)

    artwork = tmp_path / "tmp" / "discovered-artwork" / "artwork"
    assert meta.artwork_path == str(artwork / "POSTER.png")
    assert meta.artwork_banner_path == str(artwork / "POSTER_BANNER.png")
    assert meta.artwork_url == ""


@pytest.mark.asyncio
async def test_category_artwork_path_is_normalized_without_a_named_sidecar(tmp_path: Path) -> None:
    extracted = tmp_path / "MUSIC_COVER.jpg"
    Image.new("RGB", (32, 48), "purple").save(extracted)
    meta = Meta(base_dir=str(tmp_path), uuid="extracted-artwork", artwork_path=str(extracted))

    await prepare_artwork(meta)

    assert meta.artwork_path == str(tmp_path / "tmp" / "extracted-artwork" / "artwork" / "POSTER.png")
    assert Image.open(meta.artwork_path).format == "PNG"


def test_imghost_cli_arg_takes_precedence_over_automatic_selection(tmp_path: Path) -> None:
    meta, _, _ = Args({"DEFAULT": {"screens": 4, "img_host_1": "imgbox"}}).parse([str(tmp_path), "-ih", "imgbb"], Meta())

    assert meta.imghost == "imgbb"
    assert meta.imghost_from_cli is True


def test_invalid_cover_is_not_accepted() -> None:
    from src.artwork import is_valid_cover_image

    assert not is_valid_cover_image(None)


def test_local_artwork_discovery_does_not_read_media_files(tmp_path: Path) -> None:
    """The scan touches every file beside the release, so non-images must be
    skipped by suffix. Reading them would pull whole media files - hundreds of
    gigabytes over a network share - only to find they are not cover art."""
    from src.artwork import _find_local_artwork_sources

    media_file = tmp_path / "Release.mkv"
    media_file.write_bytes(b"\x00" * 2048)
    (tmp_path / "Release.iso").write_bytes(b"\x00" * 2048)

    with patch.object(Path, "read_bytes", side_effect=AssertionError("must not read a non-image")):
        assert _find_local_artwork_sources(str(media_file)) == {}


def test_oversized_image_is_rejected_without_being_read(tmp_path: Path) -> None:
    from src.artwork import MAX_ARTWORK_BYTES, is_valid_cover_image

    oversized = tmp_path / "huge.png"
    oversized.write_bytes(b"\x00" * (MAX_ARTWORK_BYTES + 1))

    with patch.object(Path, "read_bytes", side_effect=AssertionError("must not read an oversized file")):
        assert not is_valid_cover_image(oversized)


def test_user_supplied_cover_without_extension_is_accepted(tmp_path: Path) -> None:
    """Paths the user provides explicitly are validated by content, not by name:
    a decodable image must not be rejected for lacking a known suffix."""
    from src.artwork import is_valid_cover_image

    extensionless = tmp_path / "cover_no_extension"
    Image.new("RGB", (32, 48), "teal").save(extensionless, format="PNG")

    assert is_valid_cover_image(extensionless)


def test_empty_image_file_is_rejected(tmp_path: Path) -> None:
    from src.artwork import is_valid_cover_image

    empty = tmp_path / "cover.png"
    empty.touch()

    assert not is_valid_cover_image(empty)


def test_valid_cover_within_size_limit_is_still_accepted(tmp_path: Path) -> None:
    from src.artwork import is_valid_cover_image

    cover_file = tmp_path / "cover.png"
    Image.new("RGB", (32, 48), "blue").save(cover_file)

    assert is_valid_cover_image(cover_file)


def test_local_artwork_discovery_skips_media_files(tmp_path: Path) -> None:
    """The scan must still find the cover while ignoring the media beside it."""
    from src.artwork import _find_local_artwork_sources

    media_file = tmp_path / "Release.mkv"
    media_file.write_bytes(b"\x00" * 4096)
    (tmp_path / "Release.iso").write_bytes(b"\x00" * 4096)
    cover_file = tmp_path / "Release.Cover.jpg"
    Image.new("RGB", (32, 48), "blue").save(cover_file)

    sources = _find_local_artwork_sources(str(media_file))

    assert sources.get("poster") == cover_file


@pytest.mark.asyncio
async def test_unit3d_attaches_only_a_decodable_book_cover(tmp_path: Path) -> None:
    cover_file = tmp_path / "cover.png"
    Image.new("RGB", (32, 48), "green").save(cover_file)
    meta = Meta(category="BOOK", base_dir=str(tmp_path), uuid="book-1", artwork_path=str(cover_file))
    tracker = UNIT3D({"DEFAULT": {}, "TRACKERS": {"TEST": {}}}, "TEST")

    files = await tracker.get_additional_files(meta)

    assert "torrent-cover" in files
    assert files["torrent-cover"][2] == "image/png"

    cover_file.write_bytes(b"not an image")
    files = await tracker.get_additional_files(meta)
    assert "torrent-cover" not in files
