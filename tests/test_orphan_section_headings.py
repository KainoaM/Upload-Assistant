from src.bbcode import collapse_empty_wrappers, strip_orphan_section_headings, strip_uploader_signatures


def test_removes_adjacent_orphan_encode_and_source_headings() -> None:
    desc = (
        "[/spoiler]\n"
        "[center][color=#ff7700][b]Encode[/b][/color][/center]"
        "[center][color=#ff7700][b]Source[/b][/color][/center]"
    )

    cleaned = strip_orphan_section_headings(desc)

    # Assert the behaviour, not the shape: earlier this pinned the empty [center][/center]
    # shells an older implementation left for collapse_empty_wrappers to clear.
    assert "Encode" not in cleaned
    assert "Source" not in cleaned
    assert cleaned.startswith("[/spoiler]")
    assert "[center]" not in cleaned


def test_removes_only_orphan_screenshots_heading_from_info_block() -> None:
    desc = (
        "[center]\n"
        "[size=18][b][color=#9a9a9a]INFO[/color][/b][/size]\n"
        "[size=12]File Name: Krampus.2015.1080p.MA.WEB-DL.DDP5.1.H.264-cinepth.mkv\n"
        "Total Bitrate: 8.3 Mb/s[/size]\n"
        "[color=#9a9a9a][b]SCREENSHOTS:[/b][/color]\n"
        "[/center]"
    )

    cleaned = strip_orphan_section_headings(desc)

    assert "SCREENSHOTS:" not in cleaned
    assert "INFO" in cleaned
    assert "File Name: Krampus.2015.1080p.MA.WEB-DL.DDP5.1.H.264-cinepth.mkv" in cleaned
    assert "Total Bitrate: 8.3 Mb/s" in cleaned


def test_group_banner_and_orphan_heading_rules_compose() -> None:
    desc = """[code]
[center]

[size=18][b][color=#9a9a9a]INFO[/color][/b][/size]

[size=12]File Name: Krampus.2015.1080p.MA.WEB-DL.DDP5.1.H.264-cinepth.mkv
Total Bitrate: 8.3 Mb/s[/size]

[color=#9a9a9a][b]SCREENSHOTS:[/b][/color]
[/center]



[center][b][size=20]A CINEPTH RELEASE
DO NOT RETAG OR UPLOAD TO PUBLIC TRACKERS[/size][/b][/center]

[/code]"""

    cleaned = strip_uploader_signatures(desc)
    cleaned = strip_orphan_section_headings(cleaned)
    cleaned = collapse_empty_wrappers(cleaned)

    assert "A CINEPTH RELEASE" not in cleaned
    assert "DO NOT RETAG OR UPLOAD TO PUBLIC TRACKERS" not in cleaned
    assert "SCREENSHOTS" not in cleaned
    assert "INFO" in cleaned
    assert "Total Bitrate" in cleaned


def test_keeps_screenshots_heading_with_comparison_block() -> None:
    desc = "[center][b]Screenshots[/b][/center]\n[comparison=Source, Encode]one,two[/comparison]"

    assert strip_orphan_section_headings(desc) == desc


def test_keeps_heading_followed_by_real_prose() -> None:
    desc = "[center][b]Screens[/b][/center]\nThese frames show the restored color grade."

    assert strip_orphan_section_headings(desc) == desc


def test_leaves_plain_text_source_label_inside_code_untouched() -> None:
    desc = "[code]Source....:  Midsommar.2019.MULTi.COMPLETE.BLURAY-SAVEiT[/code]"

    assert strip_orphan_section_headings(desc) == desc


def test_empty_description_does_not_crash() -> None:
    assert strip_orphan_section_headings("") == ""


def test_keeps_heading_that_still_has_images_under_it() -> None:
    """The image check is the definition of orphaned, not a safety net - keep it tested.

    clean_unit3d_description happens to strip every [img] just before calling this, so without a
    test this branch would look dead and get deleted, and the function would then be wrong for
    any other caller.
    """
    desc = "[center][b]Screenshots[/b][/center]\n[img]https://example.invalid/a.png[/img]"

    assert strip_orphan_section_headings(desc) == desc
