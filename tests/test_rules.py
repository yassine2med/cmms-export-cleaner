import pytest

from cmmsclean import normalize_date, normalize_location, normalize_priority, normalize_status


@pytest.mark.parametrize("text,expected", [
    ("2026-03-04", "2026-03-04"),
    ("03/04/2026", "2026-03-04"),
    ("3/8/26", "2026-03-08"),
    ("5-Mar-2026", "2026-03-05"),
    ("March 6, 2026", "2026-03-06"),
    ("2026/03/07", "2026-03-07"),
    ("03/08/2026 14:22", "2026-03-08"),
    ("2026-03-08T09:30:00", "2026-03-08"),
    ("13/03/2026", "2026-03-13"),
])
def test_dates(text, expected):
    assert normalize_date(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "sometime in March", "02/30/2026", "99-99-9999"])
def test_bad_dates_return_none(text):
    assert normalize_date(text) is None


@pytest.mark.parametrize("text,expected", [
    ("new", "Open"), ("WIP", "In Progress"), ("  On   Hold ", "On Hold"),
    ("COMPLETED", "Closed"), ("Canceled", "Cancelled"), ("waiting on parts", "On Hold"),
])
def test_status(text, expected):
    assert normalize_status(text) == expected


def test_status_unknown():
    assert normalize_status("fixed-ish") is None


@pytest.mark.parametrize("text,expected", [
    ("P1", "Emergency"), ("urgent", "Emergency"), ("2", "High"),
    ("Routine", "Medium"), ("minor", "Low"), (" MED ", "Medium"),
])
def test_priority(text, expected):
    assert normalize_priority(text) == expected


def test_priority_unknown():
    assert normalize_priority("whenever") is None


@pytest.mark.parametrize("text,expected", [
    ("Bldg A Rm 101", "Building A, Room 101"),
    ("BLDG-A / 102", "Building A, Room 102"),
    ("building b room 210", "Building B, Room 210"),
    ("A-115", "Building A, Room 115"),
    ("Annex D rm 2", "Annex D, Room 2"),
    ("Bldg C", "Building C"),
    ("bldg.  b - 214", "Building B, Room 214"),
    ("Bldg B Rm 12b", "Building B, Room 12B"),
])
def test_locations(text, expected):
    assert normalize_location(text) == expected


def test_location_unknown():
    assert normalize_location("Lobby north") is None
