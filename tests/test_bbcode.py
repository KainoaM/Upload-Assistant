# ruff: noqa: S101
import pytest

from src.bbcode import BBCODE, strip_foreign_tracker_links, strip_uploader_signatures


UPLOADER_SIGNATURES = [
    "[right][url=https://github.com/autobrr/upbrr][size=4]Uploaded by upbrr[/size][/url][/right]",
    "[right][url=https://github.com/Audionut/Upload-Assistant][size=4]Created by Upload Assistant v3.4.5[/size][/url][/right]",
    "[right][url=https://github.com/wastaken7/Upload-Assistant][size=4]Shared with Upload-Assistant v3.9 (fork)[/size][/url][/right]",
    "[right][size=4]Uploaded with DarkPeers AutoUploader v1.2.3[/size][/right]",
    "[right][size=4][color=#4DA6FF]Uploaded with Maghuro Upload Suite[/color][/size][/right]",
    "[center][url=https://github.com/edge20200/Only-Uploader]Powered by Only-Uploader[/url][/center]",
    "[center][small]Uploaded with [url=https://github.com/AQTKU/ak-automated-uploader]AK Automated Uploader[/url][/small][/center]",
    "[center][url=https://github.com/edge20200/Only-Uploader]Brought to you by Audionut's Upload Assistant[/url][/center]",
    "[center][color=#12ee26][size=18]⚡ Uploaded using EASY UPLOADNR ⚡[/size][/color][/center]",
    "[center]OnlyEncodes Uploader - Powered by L4G's Upload Assistant[/center]",
    "[center]Uploaded with [color=red]❤[/color] using GG-BOT Upload Assistant[/center]",
    "[center][b]Uploaded with [color=#58a6ff]UNIT3D[/color] Auto Uploader[/b][/center]",
    "[code][/code][center][b][i][url=https://codeberg.org/CvT/Uploadrr]Powered by Uploadrr[/url][/i][/b][/center]",
    "[size=1]Created and uploaded using Calliope; Developed and quality tested with love and poor life decisions by Jeditwo and GalacticVoid.[/size]",
    "[size=15]Shared with [url=https://github.com/jesterr0/NfoForge]NfoForge v1.1.12[/url][/size]",
    "Uploaded using GUS-x265 V1.12.31b",
    # PR #311 kept this one because its regex was anchored to a version number. It is still a
    # right-aligned link to the fork's repo saying "Shared with Upload Assistant": a signature.
    "[right][url=https://github.com/wastaken7/Upload-Assistant]Shared with Upload Assistant release[/url][/right]",
    """[align=center]
[url=https://github.com/wastaken7/Upload-Assistant]
[size=4]
Shared with Upload-Assistant v3.3 (fork)
[/size]
[/url]
[/align]""",
    "[center][url=https://github.com/z-ink/uploadrr][img=200]https://i.ibb.co/2NVWb0c/uploadrr.webp[/img][/url][/center]",
    "[center][url=https://github.com/edge20200/Only-Uploader][/url][/center]",
]


@pytest.mark.parametrize("signature", UPLOADER_SIGNATURES)
def test_clean_unit3d_description_removes_imported_uploader_signatures(signature: str) -> None:
    description = f"Release notes\n{signature}\nTechnical details"

    cleaned, images = BBCODE().clean_unit3d_description(description, "https://example.test")

    assert signature not in cleaned
    assert "Release notes" in cleaned
    assert "Technical details" in cleaned
    assert images == []


@pytest.mark.parametrize(
    "content",
    [
        "[center]This release was uploaded with care by the group[/center]",
        "▣ Thanks to the uploaders for the source. Greetings to everyone! Enjoy!",
        "[center][color=#E97412][size=24]A GRiMM TV Release PRESENTS[/size][/color][/center]",
        "[comparison=Source, Encode]https://img.onlyimage.org/one.png, https://img.onlyimage.org/two.png[/comparison]",
    ],
)
def test_clean_unit3d_description_preserves_non_signatures(content: str) -> None:
    cleaned, _ = BBCODE().clean_unit3d_description(content, "https://example.test")

    assert cleaned == content


def test_strip_uploader_signatures_removes_each_candidate_on_one_line() -> None:
    only_uploader_link = "[center][url=https://github.com/edge20200/Only-Uploader][/url][/center]"
    only_uploader_text = "[center]Powered By Only-Uploader[/center]"
    internal_release = "[center][color=#12ee26]~ A GRiMM TV INTERNAL RELEASE ~ [/color][/center]"

    assert strip_uploader_signatures(only_uploader_link + only_uploader_text + internal_release) == ""


@pytest.mark.parametrize(
    "internal_content",
    [
        "[center][color=#12ee26]~ A GRiMM TV INTERNAL RELEASE ~ [/color][/center]",
        "This is an internal release which was first released exclusively on Aither.",
    ],
)
def test_strip_uploader_signatures_removes_internal_release_lines(internal_content: str) -> None:
    assert strip_uploader_signatures(f"Release notes\n{internal_content}\nTechnical details") == "Release notes\n\nTechnical details"


@pytest.mark.parametrize(
    "content",
    [
        "The internal audio track is the original theatrical mix.",
        "Internal subtitles include signs and songs.",
        "The internal encoding settings were tuned for grain retention.",
    ],
)
def test_strip_uploader_signatures_preserves_other_internal_lines(content: str) -> None:
    assert strip_uploader_signatures(content) == content


def test_strip_foreign_tracker_links_drops_tracker_advertisement_line() -> None:
    description = "Release notes\nFind our uploads [url=https://aither.cc/torrents?name=Kitsune]🐾 here 🐾[/url]\nTechnical details"

    assert strip_foreign_tracker_links(description) == "Release notes\nTechnical details"


def test_strip_foreign_tracker_links_keeps_substantial_surrounding_prose() -> None:
    description = "The release team posted a detailed encode note at [url=https://sub.lst.gg/torrents/1]its tracker page[/url] for reference."

    assert strip_foreign_tracker_links(description) == "The release team posted a detailed encode note at its tracker page for reference."


def test_strip_foreign_tracker_links_removes_bare_tracker_url() -> None:
    assert strip_foreign_tracker_links("Uploads: https://blutopia.cc/torrents/123") == ""


def test_strip_foreign_tracker_links_preserves_image_host() -> None:
    screenshot = "[url=https://pixhost.cc/show/1/example][img]https://t1.pixhost.to/thumbs/example.jpg[/img][/url]"

    assert strip_foreign_tracker_links(screenshot) == screenshot


def test_strip_foreign_tracker_links_preserves_closing_tags_on_advertisement_line() -> None:
    description = "Find our uploads [url=https://aither.cc/torrents?name=Kitsune]🐾 here 🐾[/url][/center][/h3]"

    assert strip_foreign_tracker_links(description) == "[/center][/h3]"


@pytest.mark.parametrize(
    "screenshot",
    [
        "[url=https://pixhost.to/show/5385/764940459_min1.png][img]https://file.aither.cc/u/RMQnijMLxVEP938v.png[/img][/url]",
        "[url=https://ibb.co/BH1DtFfP][img=350]https://file.aither.cc/u/Tbs2rSdNBiMG9Fx0.png[/img][/url]",
    ],
)
def test_strip_foreign_tracker_links_preserves_tracker_cdn_image_payload(screenshot: str) -> None:
    assert strip_foreign_tracker_links(screenshot) == screenshot


def test_strip_foreign_tracker_links_unwraps_source_credit() -> None:
    description = "Source: [url=https://darkpeers.org/torrents/4793]Gaten Ragnarok 2013 1080p BluRay AVC DTS-HD MA 5.1-Liber8[/url]"

    assert strip_foreign_tracker_links(description) == "Source: Gaten Ragnarok 2013 1080p BluRay AVC DTS-HD MA 5.1-Liber8"


def test_clean_unit3d_description_removes_only_dead_host_comparisons() -> None:
    dead = "[comparison=Source, Encode]https://ptpimg.me/one.png, https://ptpimg.me/two.png[/comparison]"
    live = "[comparison=Source, Encode]https://img.onlyimage.org/one.png, https://img.onlyimage.org/two.png[/comparison]"

    cleaned, _ = BBCODE().clean_unit3d_description(f"Release notes\n{dead}\n{live}", "https://example.test")

    assert dead not in cleaned
    assert live in cleaned


def test_clean_unit3d_description_extracts_sized_url_wrapped_images_without_orphaned_tags() -> None:
    image_tags = [
        f"[url=https://image.hallowd.net/images/{index}.png][img{attribute}]https://image.hallowd.net/images/{index}.png[/img][/url]"
        for index, attribute in enumerate(["=350", " width=350"] * 6)
    ]
    description = "[comparison=Source, Encode]" + "\n".join(image_tags) + "[/comparison]"

    cleaned, images = BBCODE().clean_unit3d_description(description, "https://example.test")

    assert len(images) == 12
    assert cleaned.lower().count("[/img]") == cleaned.lower().count("[img")
