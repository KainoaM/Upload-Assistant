# ruff: noqa: S101
import pytest

from src.bbcode import BBCODE


@pytest.mark.parametrize(
    "signature",
    [
        "[center]OnlyEncodes Uploader - Powered by L4G's Upload Assistant[/center]",
        "[code][/code][center][b][i][url=https://codeberg.org/CvT/Uploadrr]Powered by Uploadrr[/url][/i][/b][/center]",
        "[center]Uploaded with [color=red]❤[/color] using GG-BOT Upload Assistant[/center]",
        "[center]Powered by GG-BOT Upload Assistant[/center]",
        "[center][b]Uploaded with [color=#58a6ff]UNIT3D[/color] Auto Uploader[/b][/center]",
    ],
)
def test_clean_unit3d_description_removes_imported_uploader_signatures(signature: str) -> None:
    description = f"Release notes\n{signature}\nTechnical details"

    cleaned, _ = BBCODE().clean_unit3d_description(description, "https://example.test")

    assert signature not in cleaned
    assert "Release notes" in cleaned
    assert "Technical details" in cleaned


def test_clean_unit3d_description_preserves_non_tool_upload_attribution() -> None:
    signature = "[center]This release was uploaded with care by the group[/center]"

    cleaned, _ = BBCODE().clean_unit3d_description(signature, "https://example.test")

    assert cleaned == signature


def test_clean_unit3d_description_removes_only_dead_host_comparisons() -> None:
    dead = "[comparison=Source, Encode]https://ptpimg.me/one.png, https://ptpimg.me/two.png[/comparison]"
    live = "[comparison=Source, Encode]https://img.onlyimage.org/one.png, https://img.onlyimage.org/two.png[/comparison]"

    cleaned, _ = BBCODE().clean_unit3d_description(f"Release notes\n{dead}\n{live}", "https://example.test")

    assert dead not in cleaned
    assert live in cleaned


def test_clean_unit3d_description_removes_line_wrapped_align_center_signature() -> None:
    description = """Release notes
[align=center]
[url=https://github.com/wastaken7/Upload-Assistant]
[size=4]
Shared with Upload-Assistant v3.3 (fork)
[/size]
[/url]
[/align]"""

    cleaned, _ = BBCODE().clean_unit3d_description(description, "https://example.test")

    assert cleaned == "Release notes"


def test_clean_unit3d_description_preserves_non_version_suffix() -> None:
    description = "[right][url=https://github.com/wastaken7/Upload-Assistant]Shared with Upload Assistant release[/url][/right]"

    cleaned, _ = BBCODE().clean_unit3d_description(description, "https://example.test")

    assert cleaned == description
