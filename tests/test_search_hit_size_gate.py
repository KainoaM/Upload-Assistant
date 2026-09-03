# ruff: noqa: S101

from src.trackers.common import size_matched_rows

DEMONS_SIZE = 90_000_000_000


def _row(size, name="whatever"):
    return {"attributes": {"size": size, "name": name}}


def test_unrelated_hit_is_discarded_on_size():
    # The real 2026-09-03 failure: Blutopia answered a 90 GB remux query with a TV season,
    # and UA published the file under that show's title on three trackers.
    rows = [_row(21_000_000_000, "Celebrity Masterchef 2006 S01")]

    assert size_matched_rows(rows, DEMONS_SIZE, "BLU") == []


def test_exact_size_match_is_kept():
    rows = [_row(DEMONS_SIZE, "Demons 1985 2160p UHD BluRay REMUX")]

    assert size_matched_rows(rows, DEMONS_SIZE, "LST") == rows


def test_small_difference_is_within_tolerance():
    rows = [_row(int(DEMONS_SIZE * 1.01))]

    assert size_matched_rows(rows, DEMONS_SIZE, "LST") == rows


def test_difference_beyond_tolerance_is_discarded():
    rows = [_row(int(DEMONS_SIZE * 1.05))]

    assert size_matched_rows(rows, DEMONS_SIZE, "LST") == []


def test_the_matching_row_is_picked_out_of_several():
    wanted = _row(DEMONS_SIZE, "Demons 1985")
    rows = [_row(1_000_000_000, "something else"), wanted, _row(5_000_000_000, "another")]

    assert size_matched_rows(rows, DEMONS_SIZE, "OE") == [wanted]


def test_unknown_source_size_leaves_rows_untouched():
    # Nothing to compare against, so the name-score gate in trackermeta stays the only check.
    rows = [_row(123), _row(456)]

    assert size_matched_rows(rows, 0, "LST") == rows


def test_unusable_sizes_do_not_raise():
    rows = [_row(None), _row("not-a-number"), {"attributes": {}}, {}]

    assert size_matched_rows(rows, DEMONS_SIZE, "LST") == []
