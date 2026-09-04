import pytest

from src.meta import Meta
from src.trackers.UNIT3D.luminarr import Luminarr


def make_luminarr_meta(**kwargs) -> Meta:
    default_kwargs = {
        "category": "MOVIE",
        "title": "Test Movie",
        "tmdb_id": 12345,
        "tmdb": 12345,
        "type": "ENCODE",
        "resolution": "1080p",
        "video_height": 1080,
        "video_codec": "H.264",
        "container": "mkv",
        "source": "BluRay",
        "is_disc": "",
        "language": "en",
        "original_language": "en",
        "language_checked": True,
        "audio_languages": ["English"],
        "unattended": True,
        "valid_mi_settings": True,
        "image_list": ["http://img1.png", "http://img2.png", "http://img3.png"],
        "keywords": [],
        "genres": [],
        "anime": False,
        "hdr": "",
        "filelist": ["Test.Movie.1080p.BluRay.x264.mkv"],
        "mediainfo": {
            "media": {
                "track": [
                    {"@type": "Video", "Format": "AVC", "Format_Profile": "High@L4.1"},
                    {"@type": "Audio", "Format": "AAC", "Channels": "2", "Language": "en"},
                ]
            }
        },
    }
    default_kwargs.update(kwargs)
    meta = Meta()
    for key, value in default_kwargs.items():
        setattr(meta, key, value)
    return meta


def make_luminarr() -> Luminarr:
    config = {
        "TRACKERS": {
            "LUMINARR": {
                "api_key": "fake_key",
                "announce_url": "https://luminarr.me/announce/123",
            }
        }
    }
    return Luminarr(config)


@pytest.mark.asyncio
async def test_below_1080p_encode_requires_x264():
    tracker = make_luminarr()

    hevc = make_luminarr_meta(type="ENCODE", resolution="720p", video_height=720, video_codec="HEVC")
    assert await tracker.get_additional_checks(hevc) is False

    x264 = make_luminarr_meta(type="ENCODE", resolution="720p", video_height=720, video_codec="H.264")
    assert await tracker.get_additional_checks(x264) is True


@pytest.mark.asyncio
async def test_1080p_sdr_live_action_encode_requires_x264():
    tracker = make_luminarr()
    meta = make_luminarr_meta(video_codec="HEVC")
    assert await tracker.get_additional_checks(meta) is False


@pytest.mark.asyncio
async def test_1080p_sdr_animation_encode_allows_hevc_from_anime_flag():
    tracker = make_luminarr()
    meta = make_luminarr_meta(video_codec="HEVC", video_height=800, anime=True)
    assert await tracker.get_additional_checks(meta) is True


@pytest.mark.asyncio
async def test_1080p_sdr_animation_encode_allows_hevc_from_genre():
    tracker = make_luminarr()
    meta = make_luminarr_meta(video_codec="HEVC", genres=["Drama", "Animation"])
    assert await tracker.get_additional_checks(meta) is True


@pytest.mark.asyncio
async def test_1080p_hdr_encode_allows_hevc():
    tracker = make_luminarr()
    meta = make_luminarr_meta(video_codec="HEVC", hdr="HDR")
    assert await tracker.get_additional_checks(meta) is True


@pytest.mark.asyncio
async def test_1080p_dv_encode_allows_hevc():
    tracker = make_luminarr()
    meta = make_luminarr_meta(video_codec="HEVC", hdr="DV")
    assert await tracker.get_additional_checks(meta) is True


@pytest.mark.asyncio
async def test_1080p_hdr_x264_is_not_rejected():
    """We enforce 6.5.4.1 and 6.5.4.2, not 6.5.4.3.

    6.5.4.3 is only recorded in our notes as "requires x265 at 1080p HDR", which we used to
    justify NOT dropping x265 there. Turning that paraphrase into a rejection would block on
    unverified wording, and 1080p HDR x264 encodes barely exist - so nothing is enforced here.
    """
    tracker = make_luminarr()
    meta = make_luminarr_meta(video_codec="H.264", hdr="HDR")
    assert await tracker.get_additional_checks(meta) is True


@pytest.mark.asyncio
async def test_1080p_hevc_webdl_is_out_of_scope():
    tracker = make_luminarr()
    meta = make_luminarr_meta(type="WEBDL", source="WEB", video_codec="HEVC")
    assert await tracker.get_additional_checks(meta) is True


@pytest.mark.asyncio
async def test_avc_high_10_profile_rejected_for_live_action():
    tracker = make_luminarr()
    meta = make_luminarr_meta(
        mediainfo={
            "media": {
                "track": [
                    {"@type": "Video", "Format": "AVC", "Format_Profile": "High 10@L4.1"},
                    {"@type": "Audio", "Format": "AAC", "Channels": "2", "Language": "en"},
                ]
            }
        }
    )
    assert await tracker.get_additional_checks(meta) is False


@pytest.mark.asyncio
async def test_avc_high_10_profile_allowed_for_anime():
    tracker = make_luminarr()
    meta = make_luminarr_meta(
        anime=True,
        mediainfo={
            "media": {
                "track": [
                    {"@type": "Video", "Format": "AVC", "Format_Profile": "High 10@L4.1"},
                    {"@type": "Audio", "Format": "AAC", "Channels": "2", "Language": "en"},
                ]
            }
        },
    )
    assert await tracker.get_additional_checks(meta) is True


@pytest.mark.asyncio
async def test_hevc_main_10_profile_is_not_an_avc_high_10_profile():
    tracker = make_luminarr()
    meta = make_luminarr_meta(
        video_codec="HEVC",
        hdr="HDR",
        mediainfo={
            "media": {
                "track": [
                    {"@type": "Video", "Format": "HEVC", "Format_Profile": "Main 10@L4@Main"},
                    {"@type": "Audio", "Format": "AAC", "Channels": "2", "Language": "en"},
                ]
            }
        },
    )
    assert await tracker.get_additional_checks(meta) is True
