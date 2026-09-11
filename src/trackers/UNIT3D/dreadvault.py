# Upload Assistant © 2025 Audionut & wastaken7 — Licensed under UAPL v1.0
import re
from typing import Any, cast

import cli_ui

from src.console import logger
from src.languages import languages_manager
from src.meta import Meta
from src.trackers.common import Common
from src.trackers.UNIT3D import UNIT3D

Config = dict[str, Any]

# https://dreadvault.org/wikis/10 (Horror Eligibility): specific horror tropes.
# Broad subjects, styles and regions still need "horror"; violence alone does not qualify.
HORROR_TERMS = frozenset({
    "creature feature",
    "demon possession",
    "demonic",
    "eldritch",
    "ghost stories",
    "ghost story",
    "giallo",
    "haunted house",
    "haunted place",
    "horror",
    "killer doll",
    "killer object",
    "lovecraftian",
    "lycanthrope",
    "lycanthropy",
    "monster",
    "occult",
    "slasher",
    "spirit possession",
    "undead",
    "vampire",
    "werewolf",
    "werewolves",
    "witchcraft",
    "zombie",
})

NON_INFORMATIVE_BOOK_TERMS = frozenset({
    "books",
    "ebook",
    "fiction",
    "general",
    "juvenile fiction",
    "literary",
    "literature",
    "non-fiction",
    "subject",
    "nonfiction",
    "young adult fiction",
})


class DreadVault(UNIT3D):
    """
    DreadVault (DV) is a Private Torrent Tracker for HORROR MOVIES / TV / EBOOKS
    """

    tracker = "DREADVAULT"
    display_name = "DreadVault"
    allows_bloated_audio = True
    base_url = "https://dreadvault.org"
    banned_groups = (
        "AOC",
        "AOS",
        "BONE",
        "EVO",
        "FGT",
        "LAMA",
        "NeoNoir",
        "PSA",
        "RARBG",
        "VXT",
        "YIFY",
        "YTS",
    )
    id_url = f"{base_url}/api/torrents/"
    upload_url = f"{base_url}/api/torrents/upload"
    requests_url = f"{base_url}/api/requests/filter"
    search_url = f"{base_url}/api/torrents/filter"
    torrent_url = f"{base_url}/torrents/"
    supported_categories = ("TV", "MOVIE", "BOOK")
    book_required_fields = ("title", "author", "book_language")
    tracker_urls = ("https://dreadvault.org",)
    # site rules allow coexisting releases; only a literal duplicate (same files
    # and size) is a dupe
    exact_match_only = True

    def __init__(self, config: Config) -> None:
        super().__init__(config, tracker_name="DREADVAULT")
        self.config: Config = config
        self.common = Common(config)

    async def get_category_id(self, meta: Meta, category: str = "", reverse: bool = False, mapping_only: bool = False) -> dict[str, str]:
        category_id = await super().get_category_id(meta, mapping_only=True)
        category_id["BOOK"] = "3"
        if mapping_only:
            return category_id
        if reverse:
            return {v: k for k, v in category_id.items()}
        return {"category_id": category_id.get(category or meta.category, "0")}

    async def get_type_id(self, meta: Meta, type: str = "", reverse: bool = False, mapping_only: bool = False) -> dict[str, str]:
        type_id = await super().get_type_id(meta, mapping_only=True)
        type_id.update({"PDF": "7", "EPUB": "8", "CBR": "9"})
        if mapping_only:
            return type_id
        if reverse:
            return {v: k for k, v in type_id.items()}
        resolved_type = type or (self._book_format(meta) if meta.category == "BOOK" else meta.type)
        return {"type_id": type_id.get(resolved_type or "", "0")}

    @staticmethod
    def _terms(value: Any) -> list[str]:
        if isinstance(value, list):
            return [term.strip() for term in cast(list[str], value) if term.strip()]
        return [term.strip() for term in str(value or "").split(",") if term.strip()]

    @staticmethod
    def _book_format(meta: Meta) -> str:
        return (meta.type or meta.container or "").strip().upper().lstrip(".")

    def _book_name(self, meta: Meta) -> str:
        author = str(meta.author or meta.book_author or "").strip()
        title = str(meta.title or "").strip()
        year = str(meta.year or "").strip()
        edition = str(meta.manual_edition or meta.edition or "").strip()
        format_name = self._book_format(meta)
        source = str(meta.manual_source or meta.source or "").strip().upper()
        scan_type = "OCR" if meta.ocr else "SCAN" if source == "SCAN" else ""
        isbn = re.sub(r"[^0-9Xx]", "", str(meta.isbn or ""))
        name = " ".join(part for part in (author, "-" if author and title else "", title, edition, year, format_name, scan_type, isbn) if part)
        tag = str(meta.tag or "").strip().lstrip("-").strip()
        return f"{name}-{tag}" if tag else name

    async def get_name(self, meta: Meta) -> dict[str, str]:
        if meta.category == "BOOK":
            return {"name": self._book_name(meta)}

        dreadvault_name: str = meta.name
        resolution: str = meta.resolution
        video_codec: str = meta.video_codec
        video_encode: str = meta.video_encode
        name_type: str = meta.type or ""
        source: str = meta.source or ""
        alt_title = meta.aka if not meta.no_aka else ""

        year = str(meta.year) if meta.year is not None else ""
        if meta.category == "TV":
            year = str(meta.year) if (meta.year is not None and meta.search_year != "") else ""
        manual_year_value = str(meta.manual_year)
        if manual_year_value and int(manual_year_value) > 0:
            year = manual_year_value
        if meta.no_year:
            year = ""

        if name_type == "DVDRIP":
            source = "DVDRip"
            encode_token = video_encode.strip()
            dreadvault_name = dreadvault_name.replace(f"{meta.source} ", "", 1)
            dreadvault_name = dreadvault_name.replace(f" {encode_token}", "", 1)
            dreadvault_name = dreadvault_name.replace(f"{source}", f"{resolution} {source}", 1)
            dreadvault_name = dreadvault_name.replace((meta.audio), f"{meta.audio} {encode_token}", 1)

        elif meta.is_disc == "DVD":
            region_and_source = " ".join(part for part in (meta.region, source) if part)
            disc_details = " ".join(part for part in (resolution, meta.region, source) if part)
            if region_and_source:
                dreadvault_name = dreadvault_name.replace(region_and_source, disc_details, 1)
            dreadvault_name = dreadvault_name.replace((meta.audio), f"{video_codec} {meta.audio}", 1)

        elif name_type == "REMUX" and source in ("PAL DVD", "NTSC DVD", "DVD"):
            dreadvault_name = dreadvault_name.replace(meta.source or "", f"{resolution} {meta.source}", 1)
            dreadvault_name = dreadvault_name.replace((meta.audio), f"{video_codec} {meta.audio}", 1)

        if alt_title and year:
            dreadvault_name = dreadvault_name.replace(f"{year} {alt_title}", f"{alt_title} {year}", 1)

        # The marker goes immediately before the resolution, so it has to run AFTER the branches
        # above: the DVDRip and DVD-disc templates carry no resolution of their own, and those
        # branches are what insert it. Running first silently dropped the marker on both.
        if not meta.language_checked:
            await languages_manager.process_desc_language(meta, tracker=self.tracker)
        audio_languages: list[str] = [] if not meta.audio_languages else meta.audio_languages
        if audio_languages and not await languages_manager.has_english_language(audio_languages):
            foreign_lang = audio_languages[0].upper()
            dvd_remux = name_type == "REMUX" and source in ("PAL DVD", "NTSC DVD", "DVD")
            if dvd_remux and year:
                dreadvault_name = dreadvault_name.replace(year, f"{year} {foreign_lang}", 1)
            elif meta.is_disc != "BDMV":
                # get_name drops the resolution token when it is OTHER; the next slot anchors the marker:
                # the service on a web release, the source everywhere else.
                for anchor in (meta.resolution, str(meta.service), source):
                    if anchor and anchor in dreadvault_name:
                        dreadvault_name = dreadvault_name.replace(anchor, f"{foreign_lang} {anchor}", 1)
                        break

        return {"name": dreadvault_name}

    async def get_additional_checks(self, meta: Meta) -> bool:
        if meta.category == "BOOK":
            if meta.audiobook:
                logger.info(f"{self.tracker}: [bold red]Audiobooks are not supported; DreadVault has no audiobook category. Skipping upload; select a tracker that supports audiobooks.[/bold red]")
                return False
            format_name = self._book_format(meta)
            if format_name not in ("PDF", "EPUB", "CBR"):
                logger.info(f"{self.tracker}: [bold red]Unsupported eBook format: {format_name or 'unspecified'}. Only PDF, EPUB and CBR are supported. Skipping upload.[/bold red]")
                return False

        combined_genres = self._terms(meta.combined_genres)
        keywords = self._terms(meta.keywords)

        # substring per term: the horror signal is often a compound keyword
        searchable = {term.lower() for term in [*combined_genres, *keywords]}
        if meta.category == "BOOK":
            searchable -= NON_INFORMATIVE_BOOK_TERMS
        if not searchable and meta.category == "BOOK":
            reason = "no genre metadata is available (genres and keywords are empty)"
            if combined_genres or keywords:
                reason = "the only genre evidence is non-specific; the horror gate could not be evaluated"
            mam_hint = ""
            if meta.book_skip_mam or self.config.get("DEFAULT", {}).get("book_skip_mam", False):
                mam_hint = " book_skip_mam is enabled; disable it to try MAM genre lookup if you have a MAM account."
            logger.warning(
                f"{self.tracker}: [yellow]BOOK: {reason}; "
                f"continuing on uploader responsibility. Verify that this book qualifies as horror.{mam_hint}[/yellow]"
            )
        elif not any(horror_term in term for term in searchable for horror_term in HORROR_TERMS):
            if not searchable:
                logger.info(f"{self.tracker}: [bold red]Horror gate could not be evaluated because no genre metadata is available.[/bold red]")
            else:
                remedy = " Verify this book's horror eligibility and re-run attended to confirm." if meta.category == "BOOK" else ""
                logger.info(f"{self.tracker}: [bold red]Only horror content is allowed at {self.tracker}.{remedy}[/bold red]")
            if meta.unattended or not cli_ui.ask_yes_no("Do you want to upload anyway?", default=False):
                return False

        genres = ", ".join([*keywords, *combined_genres])
        # only terms that never appear as TMDB keywords on legitimate horror
        adult_keywords = ["xxx", "porn", "adult", "hentai", "softcore"]
        if meta.adult_media or any(re.search(rf"(^|,\s*){re.escape(keyword)}(\s*,|$)", genres, re.IGNORECASE) for keyword in adult_keywords):
            remedy = " Verify this book's adult classification and re-run attended if incorrect." if meta.category == "BOOK" else ""
            logger.info(f"{self.tracker}: [bold red]Porn/xxx is not allowed at {self.tracker}.{remedy}[/bold red]")
            if meta.unattended or not cli_ui.ask_yes_no("Do you want to upload anyway?", default=False):
                return False

        return True
