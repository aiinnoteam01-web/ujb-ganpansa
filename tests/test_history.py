import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collector"))

import history as h  # noqa: E402

TODAY = date(2026, 11, 19)


def rec(name, o, c, t="카페", lot="경기도 의정부시 의정부동 1-1", road="경기도 의정부시 시민로 1, 1층 (의정부동)"):
    return {"name": name, "type": t, "open": o, "close": c, "lotno": lot, "road": road, "lat": None, "lng": None}


def test_months():
    assert h.months_between("2020-01-15", "2021-01-14") == 11
    assert h.months_between("2020-01-15", "2021-01-15") == 12


def test_same_site_grouped_and_current():
    d = h.build([rec("A", "2015-01-01", "2016-01-01"), rec("B", "2016-03-01", None)], today=TODAY)
    assert d["meta"]["site_count"] == 1
    s = d["sites"][0]
    assert s["stats"]["count"] == 2 and s["stats"]["current"] == "B" and s["stats"]["avg_months"] == 12


def test_vacant():
    d = h.build([rec("A", "2015-01-01", "2016-01-01")], today=TODAY)
    assert d["sites"][0]["stats"]["vacant_since"] == "2016-01-01"


def test_risk_bad_when_four_closures():
    rs = [rec(f"X{i}", f"{2017 + i * 2}-01-01", f"{2018 + i * 2}-06-01") for i in range(4)]
    assert h.build(rs, today=TODAY)["sites"][0]["risk"] == "자주 바뀜"


def test_risk_good_long_runner():
    d = h.build([rec("오래", "2012-01-01", None)], today=TODAY)
    assert d["sites"][0]["risk"] == "오래 유지"


def test_bad_dates_dropped():
    d = h.build([rec("오류", "2020-01-01", "2019-01-01"), rec("옛날", "1995-01-01", "1998-06-01")], today=TODAY)
    assert d["meta"]["site_count"] == 0


def test_store_fills_vacancy_same_unit():
    d = h.build([rec("A", "2015-01-01", "2016-01-01")], today=TODAY,
                stores=[{"name": "새옷가게", "cat": "의류", "lotno": "경기도 의정부시 의정부동 1-1", "road": "경기도 의정부시 시민로 1, 1층"}])
    s = d["sites"][0]
    assert s["now"][0]["name"] == "새옷가게" and s["now_match"] == "자리" and s["stats"]["occupied_other"]


def test_store_other_floor_not_matched():
    d = h.build([rec("A", "2015-01-01", "2016-01-01")], today=TODAY,
                stores=[{"name": "2층학원", "cat": "학원", "lotno": "경기도 의정부시 의정부동 1-1", "road": "경기도 의정부시 시민로 1, 2층"}])
    assert d["sites"][0]["now"] == [] and not d["sites"][0]["stats"]["occupied_other"]


def test_department_floor_excluded():
    recs = [rec(f"팝업{i}", "2020-01-01", None) for i in range(3)]
    d = h.build(recs, today=TODAY)
    assert d["sites"] == [] and d["meta"]["multi_excluded"] == 1


def test_old_store_still_open_kept():
    d = h.build([rec("40년 노포", "1985-03-01", None)], today=TODAY)
    assert d["sites"][0]["stats"]["current"] == "40년 노포"
