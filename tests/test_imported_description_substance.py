# ruff: noqa: S101

from src.get_desc import _has_substance


def test_screenshots_heading_has_no_substance():
    body = (
        "[spoiler=Release Notes][center] ---------------------- "
        "[size=22]Screenshots[/size] ---------------------- [/center][/spoiler]"
    )

    assert not _has_substance(body)


def test_dashes_and_whitespace_have_no_substance():
    assert not _has_substance("  -----\n\t----------  ")


def test_real_release_note_has_substance():
    body = "[quote][center][color=#12ee26]Web Source ~ Amazon PRIME ~ Lionsgate+[/color][/center][/quote]"

    assert _has_substance(body)


def test_screenshots_with_real_prose_has_substance():
    assert _has_substance("Screenshots were captured from the source encode.")
