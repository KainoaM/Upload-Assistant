# Upload Assistant © 2025 Audionut & wastaken7 — Licensed under UAPL v1.0
from typing import Any

import cli_ui

from src.console import logger
from src.meta import Meta
from src.trackers.common import Common
from src.trackers.UNIT3D import UNIT3D


class Luminarr(UNIT3D):
    """
    Luminarr is a Private Torrent Tracker for MOVIES / TV
    """

    tracker = "LUMINARR"
    display_name = "Luminarr"
    allows_bloated_audio = True
    base_url = "https://luminarr.me"
    banned_groups: tuple[str, ...] = ()
    id_url = f"{base_url}/api/torrents/"
    upload_url = f"{base_url}/api/torrents/upload"
    requests_url = f"{base_url}/api/requests/filter"
    search_url = f"{base_url}/api/torrents/filter"
    torrent_url = f"{base_url}/torrents/"
    supported_categories = ("TV", "MOVIE")
    tracker_urls = ("https://luminarr.me",)

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config, tracker_name="LUMINARR")
        self.config = config
        self.common = Common(config)

    async def get_additional_data(self, meta: Meta) -> dict[str, Any]:
        return {
            "mod_queue_opt_in": await self.get_flag(meta, "modq"),
        }

    async def get_additional_checks(self, meta: Meta) -> bool:
        keywords = [k.lower() for k in (meta.keywords or [])]
        genres = [g.lower() for g in (meta.genres if isinstance(meta.genres, list) else [])]

        if meta.is_disc not in ["BDMV", "DVD"] and not await self.common.check_language_requirements(
            meta, self.tracker, languages_to_check=["english"], check_audio=True, check_subtitle=True, original_language=True
        ):
            return False

        if meta.is_disc not in ["BDMV", "DVD"] and meta.resolution not in ["8640p", "4320p", "2160p", "1440p", "1080p", "1080i", "720p"]:
            if not meta.unattended or (meta.unattended and meta.unattended_confirm):
                logger.info(f"{self.tracker}: [bold red]only allows SD releases when the content does not have a higher resolution release.[/bold red]")
                if cli_ui.ask_yes_no("Do you want to upload anyway?", default=False):
                    pass
                else:
                    return False
            else:
                return False

        if not meta.is_disc and meta.container != "mkv":
            logger.info(f"{self.tracker}: [bold red]only allows MKV containers for non-disc uploads.[/bold red]")
            return False

        if meta.type == "ENCODE":
            is_animation = meta.anime or "animation" in keywords or "animation" in genres
            video_codec = (meta.video_codec or "").upper()
            is_x264 = video_codec in ("AVC", "H.264", "H264", "X264")
            resolution = (meta.resolution or "").lower()
            # Named buckets only. meta.video_height is the LETTERBOXED picture height - a 2.40:1
            # 1080p encode measures 800 and a 1080p WEB-DL 816 - so testing it would call most
            # scope films sub-1080p and reject their codec. Listed positively, so an unknown
            # resolution rejects nothing.
            is_below_1080p = resolution in ("720p", "576p", "576i", "480p", "480i")
            # meta.hdr is a token string: "" for SDR, otherwise "HDR", "DV HDR" and friends.
            is_hdr = bool(meta.hdr)

            if is_below_1080p and not is_x264:
                logger.info(f"{self.tracker}: [bold red]Rule 6.5.4.1: Encodes below 1080p must use x264.[/bold red]")
                return False

            if resolution == "1080p" and not is_animation and not is_hdr and not is_x264:
                logger.info(f"{self.tracker}: [bold red]Rule 6.5.4.2: 1080p SDR live-action encodes must use x264.[/bold red]")
                return False

            media_tracks = (meta.mediainfo or {}).get("media", {}).get("track", [])
            video_tracks = [track for track in media_tracks if track.get("@type") == "Video"] if isinstance(media_tracks, list) else []
            video_profile = str(video_tracks[0].get("Format_Profile", "")).upper() if video_tracks else ""
            forbidden_avc_profiles = ("HIGH 10", "HIGH 4:2:2", "HIGH 4:4:4", "HI10P", "HI422P", "HI444P")
            if is_x264 and not is_animation and any(profile in video_profile for profile in forbidden_avc_profiles):
                logger.info(f"{self.tracker}: [bold red]Rule 6.2.4.2.1.1: AVC High 10/4:2:2/4:4:4 profiles are not allowed for live-action encodes.[/bold red]")
                return False

        if not meta.valid_mi_settings:
            logger.info(f"{self.tracker}: [bold red]No encoding settings in mediainfo, skipping {self.tracker} upload.[/bold red]")
            return False

        return self.common.check_and_confirm_adult_media_upload(meta, self.tracker)
