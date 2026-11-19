import csv

import pytest

from cmmsclean.cleaner import clean_rows, map_headers, read_records
from cmmsclean.cli import main

MAPPING = {"WO #": "id", "Location": "location", "Status": "status", "Priority": "priority",
           "Date Opened": "created", "Date Closed": "closed", "Description": "description"}


def rec(**kw):
    base = {"WO #": "WO-1", "Location": "Bldg A Rm 1", "Status": "new", "Priority": "P2",
            "Date Opened": "03/04/2026", "Date Closed": "", "Description": "x"}
    base.update(kw)
    return base


def test_header_aliases():
    mapping = map_headers(["Work Order #", " DATE  OPENED ", "Desc", "Unrelated"])
    assert mapping == {"Work Order #": "id", " DATE  OPENED ": "created", "Desc": "description"}


def test_missing_required_header():
    with pytest.raises(ValueError, match="id"):
        map_headers(["Location", "Date Opened"])


def test_clean_row_values():
    result = clean_rows([rec()], MAPPING)
    row = result.rows[0]
    assert row["location"] == "Building A, Room 1"
    assert row["status"] == "Open" and row["priority"] == "High" and row["created"] == "2026-03-04"
    assert result.changed["status"] == 1


def test_duplicate_ids_dropped_case_insensitive():
    result = clean_rows([rec(), rec(**{"WO #": "wo-1"})], MAPPING)
    assert len(result.rows) == 1 and result.duplicates == 1


def test_missing_id_rejected():
    result = clean_rows([rec(**{"WO #": ""})], MAPPING)
    assert not result.rows and result.rejects[0]["reason"] == "missing id"


def test_bad_created_date_rejected():
    result = clean_rows([rec(**{"Date Opened": "soon"}), rec(**{"WO #": "WO-2", "Date Opened": ""})], MAPPING)
    assert [r["reason"] for r in result.rejects] == ["unreadable created date", "missing created date"]


def test_unknown_value_kept_and_counted():
    result = clean_rows([rec(Status="fixed-ish")], MAPPING)
    assert result.rows[0]["status"] == "fixed-ish"
    assert result.unresolved["status"] == 1


def test_whitespace_collapsed():
    result = clean_rows([rec(Description="  a   b  ")], MAPPING)
    assert result.rows[0]["description"] == "a b"


def test_empty_optional_fields_not_counted():
    result = clean_rows([rec()], MAPPING)
    assert result.unresolved["closed"] == 0 and result.changed["closed"] == 0


def test_cli_end_to_end(tmp_path, capsys):
    src = tmp_path / "in.csv"
    src.write_text("WO #,Date Opened,Status\nWO-1,03/04/2026,done\n,03/05/2026,open\n")
    out, rej = tmp_path / "out.csv", tmp_path / "rej.csv"
    assert main([str(src), "-o", str(out), "--rejects", str(rej)]) == 0
    rows = list(csv.DictReader(out.open()))
    assert rows[0]["status"] == "Closed" and rows[0]["created"] == "2026-03-04"
    assert rej.exists()
    assert "rejected 1" in capsys.readouterr().out


def test_cli_missing_file(tmp_path, capsys):
    assert main([str(tmp_path / "none.csv")]) == 1
    assert "error" in capsys.readouterr().err


def test_read_records_handles_bom(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_bytes(b"\xef\xbb\xbfWO #,Date Opened\nWO-1,2026-03-04\n")
    headers, records = read_records(path)
    assert headers[0] == "WO #" and len(records) == 1
