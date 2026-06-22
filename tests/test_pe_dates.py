from modules.pe_monitor.views import _parse_iso_date


def test_parse_iso_date_canonicalises():
    assert _parse_iso_date("2024-01-01") == "2024-01-01"
    assert _parse_iso_date("20240101") == "2024-01-01"    # basic format
    assert _parse_iso_date("2024-W01-1") == "2024-01-01"  # ISO week date


def test_parse_iso_date_rejects_bad_input():
    for bad in (None, "", "not-a-date", "2024-13-01"):
        assert _parse_iso_date(bad) is None
