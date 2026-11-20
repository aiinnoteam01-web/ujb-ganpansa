import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collector"))

import normalize as n  # noqa: E402


def test_date_compact():
    assert n.to_date("20190305") == "2019-03-05"


def test_date_dotted():
    assert n.to_date("2019.03.05") == "2019-03-05"


def test_date_bad():
    assert n.to_date("2019-13-40") is None and n.to_date("") is None


def test_type_cafe():
    assert n.type_of("커피숍", "휴게음식점") == "카페"


def test_type_chicken_hof_is_chicken_first():
    # '통닭(치킨)' 은 치킨. 화면 업종 이름은 rules/types.yaml 과 같아야 함
    assert n.type_of("통닭(치킨)", "일반음식점") == "치킨"


def test_type_bakery_fallback():
    assert n.type_of(None, "제과점") == "베이커리"


def test_site_key_with_unit():
    key, dong, unit = n.site_key("경기도 의정부시 의정부동 168-5", "경기도 의정부시 시민로 100, 1층 101호 (의정부동)")
    assert key == "의정부동 168-5 1층101호" and dong == "의정부동" and unit


def test_site_key_building_only():
    key, dong, unit = n.site_key("경기도 의정부시 민락동 800-3", "")
    assert key == "민락동 800-3" and not unit


def test_site_key_basement():
    key, _, _ = n.site_key("경기도 의정부시 호원동 12-1", "경기도 의정부시 평화로 1, 지하1층 (호원동)")
    assert key == "호원동 12-1 지하1층"


def test_type_hof_is_pub():
    assert n.type_of("호프/통닭", "일반음식점") == "주점"
    assert n.type_of("라이브카페", "일반음식점") == "주점"


def test_error_text_hides_key():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collector"))
    import collect
    msg = collect.safe(Exception("GET /info?serviceKey=abc%2Bdef&pageNo=1 failed"))
    assert "abc" not in msg and "serviceKey=***" in msg
