# ruff: noqa: S101

from src.trackers.common import rows_matching_release

OURS = "El.Conde.2023.1080p.NF.WEB-DL.DUAL.DDP5.1.Atmos.H.264-FLUX.mkv"
OUR_SIZE = 7_177_154_133


def _row(files=None, size=0, name="whatever"):
    attributes = {"size": size, "name": name}
    if files is not None:
        attributes["files"] = [{"name": f} for f in files]
    return {"attributes": attributes}


def test_exact_inner_filename_is_the_match():
    row = _row(files=[OURS], name="El Conde 2023 1080p NF WEB-DL Dual-Audio DD+ 5.1 Atmos H.264-FLUX")

    assert rows_matching_release([row], OURS, OUR_SIZE, "ULCX") == [row]


def test_blutopia_noise_is_discarded():
    # Real response: Blutopia ignores file_name and answered this query with unrelated releases.
    rows = [
        _row(files=["Saturday.Night.Live.S35E01.720p.PCOK.WEB-DL.DDP5.1.H.264-IndianaJones.mkv"]),
        _row(files=["AUTORUN.INF", "Files/go.exe"]),
        _row(files=["Saturday.Night.Live.S36E02.720p.PCOK.WEB-DL.DDP5.1.H.264-IndianaJones.mkv"]),
    ]

    assert rows_matching_release(rows, OURS, OUR_SIZE, "BLU") == []


def test_case_differences_still_match():
    row = _row(files=[OURS.upper()])

    assert rows_matching_release([row], OURS, OUR_SIZE, "LST") == [row]


def test_the_matching_row_is_picked_out_of_several():
    wanted = _row(files=[OURS])
    rows = [_row(files=["Something.Else.2019.mkv"]), wanted, _row(files=["Another.2020.mkv"])]

    assert rows_matching_release(rows, OURS, OUR_SIZE, "OE") == [wanted]


def test_a_response_without_files_falls_back_to_size():
    row = _row(size=OUR_SIZE)

    assert rows_matching_release([row], OURS, OUR_SIZE, "LST") == [row]


def test_size_fallback_rejects_a_different_release():
    # The Masterchef row was a whole different size; the fallback catches that much.
    assert rows_matching_release([_row(size=21_000_000_000)], OURS, OUR_SIZE, "BLU") == []


def test_unusable_rows_do_not_raise():
    rows = [_row(size=None), _row(size="not-a-number"), {"attributes": {}}, {}]

    assert rows_matching_release(rows, OURS, OUR_SIZE, "LST") == []
