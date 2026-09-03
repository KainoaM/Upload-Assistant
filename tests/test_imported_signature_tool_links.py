# ruff: noqa: S101
from src.bbcode import strip_uploader_signatures


def test_removes_bare_tracker_tool_link() -> None:
    signature = "[center][url=https://onlyencodes.cc/wikis/17]OnlyEncodes Upload Assistant[/url][/center]"

    assert strip_uploader_signatures(signature) == ""


def test_still_removes_attributed_code_host_tool_link() -> None:
    signature = "[right][url=https://github.com/wastaken7/Upload-Assistant][size=4]Shared with Upload-Assistant v3.9 (fork)[/size][/url][/right]"

    assert strip_uploader_signatures(signature) == ""


def test_keeps_tracker_link_without_tool_name() -> None:
    content = "[center][url=https://onlyencodes.cc/torrents/123]Source torrent[/url][/center]"

    assert strip_uploader_signatures(content) == content


def test_keeps_prose_mentioning_upload_assistant() -> None:
    content = "The upload assistant screenshots were taken from the remux."

    assert strip_uploader_signatures(content) == content


def test_keeps_release_note() -> None:
    content = "Release notes:\n- Corrected chapter timestamps.\n- Retained the original Dolby Vision metadata."

    assert strip_uploader_signatures(content) == content
