"""The tracker whose description is worth having must win, not the one with a closer filename.

Regression for 2026-09-03: on Dexter S01 both LST and OnlyEncodes matched, OE's release name was
marginally closer to our folder name, and the old flat "+10 for having a description" let that
decide - so we took OE's 1,099-char description (which cleans down to a bare "Personal Release"
banner) over LST's 18,831-char one. description_quality() rates them 1,610 against 257,474.
"""

from src.get_tracker_data import TrackerDataManager
from src.meta import Meta

LST_DESCRIPTION = "[center][spoiler=S01E02]\n[b]General[/b]\n[b]Format:[/b] Matroska\n" + ("[b]Bit rate:[/b] 6058 kb/s per episode mediainfo\n" * 40) + "[/spoiler][/center]"
OE_DESCRIPTION = "[center][size=6][b]Personal Release[/b][/size][/center]"


def _candidate(tracker: str, description: str, images: int, name_score: int) -> Meta:
    meta = Meta()
    meta.tmdb_id = 1405
    meta.description = description
    meta.tracker_description_raw = {tracker: description}
    meta.image_list = [{"img_url": f"https://example.invalid/{i}.png"} for i in range(images)]
    meta.description_provenance = {"source": tracker, "score": name_score}
    return meta


def test_substance_beats_a_closer_filename() -> None:
    original = Meta()
    # OE is given every cosmetic advantage the old scorer rewarded: a better name score and
    # the same screenshot count. Only the description differs.
    lst = _candidate("LST", LST_DESCRIPTION, images=10, name_score=62)
    oe = _candidate("ONLYENCODES", OE_DESCRIPTION, images=10, name_score=100)

    lst_score = TrackerDataManager._candidate_score(original, lst)
    oe_score = TrackerDataManager._candidate_score(original, oe)

    assert lst_score > oe_score, f"thin description won: LST {lst_score} vs OE {oe_score}"
    # Ranked on substance, not summed away by the likeness terms.
    assert lst_score[1] > oe_score[1]
    assert oe_score[2] > lst_score[2], "the fixture must keep OE ahead on likeness"


def test_no_description_loses_to_any_description() -> None:
    original = Meta()
    empty = _candidate("ULCX", "", images=10, name_score=100)
    lst = _candidate("LST", LST_DESCRIPTION, images=0, name_score=1)
    assert TrackerDataManager._candidate_score(original, lst) > TrackerDataManager._candidate_score(original, empty)
