# ruff: noqa: S101

from src.trackers.common import release_titles_agree


def test_reordered_title_disagrees():
    assert not release_titles_agree(
        "Gretel.and.Hansel.2020.1080p.AMZN.WEB-DL.DDP5.1.H.264-NTG.mkv",
        "Hansel and Gretel 2020 1080p AMZN WEB-DL DD+ 5.1 H.264-NTG",
    )


def test_same_title_agrees():
    assert release_titles_agree(
        "Gretel.and.Hansel.2020.1080p.AMZN.WEB-DL.DDP5.1.H.264-NTG.mkv",
        "Gretel and Hansel 2020 1080p AMZN WEB-DL DD+ 5.1 H.264-NTG",
    )


def test_original_title_after_aka_agrees():
    assert release_titles_agree(
        "Geomeun.sajedeul.2015.720p.BluRay.DD+5.1.x264-playHD.mkv",
        "The Priests AKA Geomeun sajedeul 2015 720p BluRay DD+ 5.1 x264-playHD",
    )


def test_english_title_before_aka_agrees():
    assert release_titles_agree(
        "Grave Torture (2024) (1080p NF WEB-DL H264 SDR DDP 5.1 Indonesian - HONE).mkv",
        "Grave Torture AKA Siksa Kubur 2024 1080p NF WEB-DL DD+ 5.1 H.264-HONE",
    )


def test_empty_tracker_name_disagrees():
    assert not release_titles_agree("Gretel.and.Hansel.2020.1080p.mkv", "")


def test_a_title_that_is_a_year_still_agrees():
    # Splitting on the first four-digit year ate these titles entirely, so two identical names
    # compared as DISAGREE. guessit reads 1917/2012 as the title and the second number as the year.
    from src.trackers.common import release_titles_agree

    assert release_titles_agree(
        "1917.2019.1080p.BluRay.x264-GRP.mkv", "1917 2019 1080p BluRay x264-GRP"
    )
    assert release_titles_agree(
        "2012.2009.1080p.BluRay.x264-GRP.mkv", "2012 2009 1080p BluRay x264-GRP"
    )
    assert release_titles_agree(
        "Blade.Runner.2049.2017.2160p.UHD.BluRay.x265-GRP.mkv",
        "Blade Runner 2049 2017 2160p UHD BluRay x265-GRP",
    )
    # and a year-titled film must still not match a different one
    assert not release_titles_agree(
        "1917.2019.1080p.BluRay.x264-GRP.mkv", "2012 2009 1080p BluRay x264-GRP"
    )
