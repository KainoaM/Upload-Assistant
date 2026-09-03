# ruff: noqa: S101

import asyncio

from src.meta import Meta
from src.trackermeta import update_meta_with_unit3d_data


def test_unrelated_search_hit_is_rejected_without_adopting_metadata():
    async def run():
        meta = Meta(
            {
                "category": "MOVIE",
                "description": "original description",
                "image_list": [{"raw_url": "https://example.com/original.jpg"}],
                "tracker_description_mode": "text_and_images",
                "tracker_search_term": "Demons.1985.UHD.BluRay.2160p.DTS-HD.MA.5.1.DV.HEVC.REMUX-FraMeSToR.mkv",
            }
        )
        result = (
            123,
            456,
            789,
            10,
            "wrong description",
            "TV",
            None,
            [{"raw_url": "https://example.com/wrong.jpg"}],
            "Celebrity Masterchef 2006 S01 2160p UHD BluRay REMUX DV HDR HEVC MULTI DTS-HD MA 5.1-FraMeSToR",
        )

        assert not await update_meta_with_unit3d_data(meta, result, "BLUTOPIA")
        assert meta.tmdb_id is None
        assert meta.imdb_id is None
        assert meta.tvdb_id is None
        assert meta.mal_id == 0
        assert meta.description == "original description"
        assert meta.category == "MOVIE"
        assert meta.image_list == [{"raw_url": "https://example.com/original.jpg"}]
        assert getattr(meta, "blutopia_filename", "") == ""
        assert meta.description_candidates[0]["selected"] is False

    asyncio.run(run())


def test_renamed_genuine_search_hit_is_accepted():
    async def run():
        meta = Meta(
            {
                "tracker_description_mode": "text",
                "tracker_search_term": "Blink.Twice.2024.1080p.AMZN.WEB-DL.DDP5.1.Atmos.H.264-FLUX.mkv",
            }
        )
        result = (123, 456, 0, 0, "tracker description", "MOVIE", None, [], "Blink Twice 2024 1080p AMZN WEB-DL DD+ 5.1 Atmos H.264-FLUX")

        assert await update_meta_with_unit3d_data(meta, result, "BLUTOPIA")
        assert meta.description == "tracker description"

    asyncio.run(run())


def test_explicit_id_hit_is_accepted_despite_poor_name_score():
    async def run():
        meta = Meta(
            {
                "tracker_description_mode": "text",
                "tracker_ids": {"BLUTOPIA": "123"},
                "tracker_search_term": "Demons.1985.2160p.mkv",
            }
        )
        result = (123, 456, 0, 0, "explicit description", "TV", None, [], "Completely Unrelated Release")

        assert await update_meta_with_unit3d_data(meta, result, "BLUTOPIA")
        assert meta.description == "explicit description"
        assert meta.category == "TV"

    asyncio.run(run())


def test_search_hit_never_changes_category_when_accepted():
    async def run():
        meta = Meta(
            {
                "category": "MOVIE",
                "tracker_description_mode": "text",
                "tracker_search_term": "Blink.Twice.2024.1080p.mkv",
            }
        )
        result = (123, 456, 0, 0, "tracker description", "TV", None, [], "Blink Twice 2024 1080p")

        assert await update_meta_with_unit3d_data(meta, result, "BLUTOPIA")
        assert meta.category == "MOVIE"

    asyncio.run(run())


def test_search_hit_with_empty_returned_name_is_rejected():
    async def run():
        meta = Meta(
            {
                "description": "original description",
                "tracker_description_mode": "text",
                "tracker_search_term": "Blink.Twice.2024.1080p.mkv",
            }
        )
        result = (123, 456, 0, 0, "tracker description", "MOVIE", None, [], "")

        assert not await update_meta_with_unit3d_data(meta, result, "BLUTOPIA")
        assert meta.tmdb_id is None
        assert meta.description == "original description"
        assert meta.description_candidates[0]["release_name"] == ""
        assert meta.description_candidates[0]["selected"] is False

    asyncio.run(run())
