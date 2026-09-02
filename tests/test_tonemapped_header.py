# ruff: noqa: S101

from types import SimpleNamespace

import src.get_desc as get_desc
from src.get_desc import DescriptionBuilder

HEADER = "[center][code] Screenshots have been tonemapped for reference [/code][/center]"
TEXT = f"Notes\n{HEADER}\nMore"


def _builder():
    return DescriptionBuilder("TEST", {"DEFAULT": {}, "TRACKERS": {"TEST": {}}})


def _meta(*, imported=True, mode="text", images=None):
    return SimpleNamespace(
        description_provenance={"source": "TEST"} if imported else None,
        tracker_description_mode=mode,
        image_list=images or [],
        base_dir="base",
        uuid="release",
        hdr="HDR",
        tag="",
    )


def _patch_image_state(monkeypatch, captures=()):
    monkeypatch.setattr(get_desc, "resolve_description_mode", lambda mode: SimpleNamespace(imports_images=mode == "text_and_images"))
    monkeypatch.setattr(get_desc, "manifest_files", lambda _base_dir, _uuid, _group: list(captures))


def test_imported_text_without_images_loses_the_header(monkeypatch):
    _patch_image_state(monkeypatch)

    result = _builder()._strip_tonemapped_header(TEXT, _meta(), replacing=False)

    assert HEADER not in result
    assert "Notes" in result and "More" in result


def test_imported_hosted_images_keep_one_header(monkeypatch):
    _patch_image_state(monkeypatch)
    meta = _meta(mode="text_and_images", images=[{"img_url": "https://example.test/screen.png"}])

    result = _builder()._strip_tonemapped_header(TEXT, meta, replacing=False)

    assert result.count(HEADER) == 1


def test_local_captures_remove_the_imported_header(monkeypatch):
    _patch_image_state(monkeypatch, captures=["screen.png"])
    meta = _meta(mode="text_and_images", images=[{"img_url": "https://example.test/screen.png"}])

    result = _builder()._strip_tonemapped_header(TEXT, meta, replacing=False)

    assert HEADER not in result


def test_replacing_removes_the_imported_header(monkeypatch):
    _patch_image_state(monkeypatch)

    result = _builder()._strip_tonemapped_header(TEXT, _meta(mode="text_and_images"), replacing=True)

    assert HEADER not in result


def test_user_supplied_description_keeps_the_header(monkeypatch):
    _patch_image_state(monkeypatch)

    result = _builder()._strip_tonemapped_header(TEXT, _meta(imported=False), replacing=False)

    assert result.count(HEADER) == 1


def test_duplicate_imported_headers_collapse_to_one(monkeypatch):
    _patch_image_state(monkeypatch)
    meta = _meta(mode="text_and_images", images=[{"img_url": "http://example.test/screen.png"}])
    text = f"Notes\n{HEADER}\n{HEADER}\nMore"

    result = _builder()._strip_tonemapped_header(text, meta, replacing=False)

    assert result.count(HEADER) == 1
