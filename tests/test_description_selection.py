# ruff: noqa: S101

import asyncio

from src.meta import Meta
from src.tracker_descriptions import description_quality
from src.trackermeta import update_meta_with_unit3d_data


def test_description_quality_prefers_substantive_release_notes():
    release_notes = " ".join(["This Italian production includes detailed restoration and release notes."] * 100)
    short_signature = "[center]Screenshots\nCreated with Upload Assistant\n[img]https://x/1[/img][/center]"
    shorter_signature = "Screenshots Created with Upload Assistant https://x!"

    assert len(release_notes) > 7000
    assert len(short_signature) == 81
    assert len(shorter_signature) == 52
    assert description_quality(release_notes, 0) > description_quality(short_signature, 1)
    assert description_quality(release_notes, 0) > description_quality(shorter_signature, 0)


def test_screenshots_only_description_scores_near_zero():
    description = "[center][b]Screenshots[/b]\n[img]https://example.com/one.jpg[/img][/center]"

    assert description_quality(description, 1) == 1


def test_more_screenshots_breaks_a_prose_less_tie():
    description = "[center]Screenshots[/center]"

    assert description_quality(description, 4) > description_quality(description, 1)


def test_better_description_survives_a_later_worse_candidate():
    async def run():
        meta = Meta({"tracker_description_mode": "text", "tracker_search_term": "Release.2026.1080p"})
        good = (1, 2, 3, 0, "Detailed release notes explain the source and restoration process.", "MOVIE", None, [], "Release.2026.1080p.mkv")
        bad = (1, 2, 3, 0, "[b]Screenshots[/b] Created with Upload Assistant", "MOVIE", None, [], "Release.2026.1080p.mkv")

        await update_meta_with_unit3d_data(meta, good, "LST")
        fingerprint = meta.description_fingerprint
        await update_meta_with_unit3d_data(meta, bad, "ULCX")

        assert meta.description == good[4]
        assert meta.description_fingerprint == fingerprint
        assert [candidate["selected"] for candidate in meta.description_candidates] == [True, False]
        assert meta.description_provenance["source"] == "LST"

    asyncio.run(run())


def test_explicit_id_beats_a_higher_quality_search_hit():
    async def run():
        meta = Meta(
            {
                "tracker_description_mode": "text",
                "tracker_search_term": "Release.2026.1080p",
                "tracker_ids": {"ULCX": "123"},
            }
        )
        search_hit = (1, 2, 3, 0, "Extensive and genuinely useful release notes about the source, encode, and restoration.", "MOVIE", None, [], "Release.2026.1080p.mkv")
        explicit_hit = (1, 2, 3, 0, "Brief notes.", "MOVIE", None, [], "Different.Release.mkv")

        await update_meta_with_unit3d_data(meta, search_hit, "LST")
        await update_meta_with_unit3d_data(meta, explicit_hit, "ULCX")

        assert meta.description == explicit_hit[4]
        assert meta.description_provenance["source"] == "ULCX"
        assert meta.description_candidates[-1]["selected"] is True

    asyncio.run(run())
