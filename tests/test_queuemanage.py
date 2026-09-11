from pathlib import Path
from unittest.mock import Mock

import pytest

from src.args import Args
from src.book_prep import BOOK_EXTENSIONS
from src.meta import Meta
from src.queuemanage import QueueManager


@pytest.mark.asyncio
@pytest.mark.parametrize("category", ["BOOK", "MOVIE", "TV"])
@pytest.mark.parametrize("path_mode", ["folder", "glob"])
@pytest.mark.parametrize("category_source", ["meta", "cli"])
async def test_queue_filters_extensions_for_category(tmp_path: Path, monkeypatch, category, path_mode, category_source) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (tmp_path / "tmp").mkdir()
    video_extensions = {".mkv", ".mp4", ".ts"}
    for extension in BOOK_EXTENSIONS | video_extensions | {".jpg"}:
        (books / f"Title{extension.upper()}").touch()
    book_folder = books / "Book folder"
    book_folder.mkdir()
    (book_folder / "Novel.epub").touch()
    monkeypatch.setattr("src.queuemanage.cli_ui.ask_string", lambda _: "")
    path = str(books if path_mode == "folder" else books / "Title*")
    if category_source == "cli":
        meta, _, _ = Args({"DEFAULT": {"screens": 1}}).parse([path, "--category", category.lower(), "--queue", "books"], Meta())
        assert meta.category == ""
    else:
        meta = Meta(category=category, queue="books")

    queue, _ = await QueueManager.handle_queue(path, meta, [path], str(tmp_path))

    expected_extensions = BOOK_EXTENSIONS if category == "BOOK" else video_extensions
    expected = {str(books / f"Title{extension.upper()}") for extension in expected_extensions}
    if category == "BOOK" and path_mode == "folder":
        expected.add(str(book_folder))
    assert set(queue) == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("category", ["BOOK", "MOVIE"])
@pytest.mark.parametrize("path_mode", ["folder", "glob"])
async def test_empty_filtered_queue_explains_before_prompting_or_saving(tmp_path: Path, monkeypatch, caplog, category, path_mode) -> None:
    books = tmp_path / "books"
    books.mkdir()
    (books / "cover.jpg").touch()
    prompt = Mock()
    monkeypatch.setattr("src.queuemanage.cli_ui.ask_string", prompt)
    path = str(books if path_mode == "folder" else books / "*.jpg")

    with pytest.raises(SystemExit) as error:
        await QueueManager.handle_queue(path, Meta(category=category, queue="books"), [path], str(tmp_path))

    assert error.value.code == 1
    assert "Queue is empty after filtering" in caplog.text
    assert "check the category and use supported files" in caplog.text
    assert (".epub" if category == "BOOK" else ".mkv") in caplog.text
    prompt.assert_not_called()
    assert not (tmp_path / "tmp" / "books_queue.log").exists()
