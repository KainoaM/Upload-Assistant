from src.bbcode import strip_uploader_signatures


def test_removes_aligned_group_release_banner() -> None:
    desc = "[center][b][size=20]A CINEPTH RELEASE\nDO NOT RETAG OR UPLOAD TO PUBLIC TRACKERS[/size][/b][/center]"

    assert strip_uploader_signatures(desc) == ""


def test_removes_bare_distribution_instruction() -> None:
    desc = "DO NOT RETAG OR UPLOAD TO PUBLIC TRACKERS"

    assert strip_uploader_signatures(desc) == ""


def test_recognizes_distribution_instruction_variants() -> None:
    instructions = (
        "do not retag",
        "do not re-tag",
        "do not upload",
        "do not re-upload",
        "do not reupload",
        "do not share",
        "do not distribute",
        "do not trade",
        "not for public",
        "not for trade",
        "not to be uploaded",
        "not to be shared",
        "no retagging",
        "DO - NOT   RE - TAG",
    )

    for instruction in instructions:
        assert strip_uploader_signatures(instruction) == ""


def test_keeps_technical_notes_in_code_block() -> None:
    desc = "[code]Source....:  Midsommar.2019.MULTi.COMPLETE.BLURAY-SAVEiT (ITA) (Video)[/code]"

    assert strip_uploader_signatures(desc) == desc


def test_keeps_encoder_notes_prose() -> None:
    desc = (
        "[quote]Source..........: Blu-ray Remux AVC DTS-HD MA 5.1 - KRaLiMaRKo (Thanks)\n"
        "Encoder.........: DeamoN\n"
        "Encoder's note: used fillmargins.[/quote]"
    )

    assert strip_uploader_signatures(desc) == desc


def test_keeps_long_paragraph_with_distribution_instruction() -> None:
    visible = (
        "These archival notes explain the source selection, restoration choices, encoding settings, and quality checks "
        "in enough detail to help viewers understand the presentation. Please do not upload partial samples while the "
        "comparison is being reviewed, because incomplete files could lead to misleading conclusions about the encode."
    )
    desc = f"[quote]{visible}[/quote]"

    assert len(visible) > 200
    assert strip_uploader_signatures(desc) == desc
