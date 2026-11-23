"""공통 형식 레코드 → '점포 자리'별 이력(data/sites.json).

sites.json
  meta        지역·건수·기준일
  area_stats  동 × 업종 평균 영업기간 (폐업 가게 기준, 표본 3건 이상)
  by_year     연도별 개업·폐업 수
  sites[]     자리 하나 = {id, key, road, lotno, dong(법정동), unit, lat, lng, history[], stats{}, risk, now[]}
              now = 소상공인 상가정보 기준 지금 그 자리(또는 같은 건물)에 있는 가게들
  areas       행정동 경계(지도 겹쳐 보기 전용). 동네 조건·통계·자리 묶기는 모두 법정동 기준.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

from admdong import _GEO
from normalize import site_key

RULES = Path(__file__).resolve().parent.parent / "rules"
RISK = yaml.safe_load((RULES / "risk.yaml").read_text(encoding="utf-8"))
REGION = yaml.safe_load((RULES / "region.yaml").read_text(encoding="utf-8"))


def _d(s: str) -> date:
    return date.fromisoformat(s)


def months_between(a: str, b: str) -> int:
    x, y = _d(a), _d(b)
    return max(0, (y.year - x.year) * 12 + (y.month - x.month) - (1 if y.day < x.day else 0))


MULTI_AT = 3


def max_concurrent(hist: list[dict], t: str) -> int:
    ev = sorted([(h["open"], 1) for h in hist] + [(h["close"] or t, -1) for h in hist], key=lambda e: (e[0], e[1]))
    cur = peak = 0
    for _, v in ev:
        cur += v
        peak = max(peak, cur)
    return peak


def risk_level(hist: list[dict], today: date) -> str:
    cut = date(today.year - RISK["years"], today.month, 1).isoformat()
    closed = [h for h in hist if h["close"] and h["close"] >= cut]
    n = len(closed)
    avg = statistics.mean(h["months"] for h in closed) if closed else None
    recent = sum(1 for h in closed if (today - _d(h["close"])).days <= RISK["recent_days"])
    bad, mid = RISK["주의"], RISK["보통"]
    if n >= bad["closed_at_least"] or (n >= 2 and avg is not None and avg < bad["closed_2_and_avg_under"]) \
            or recent >= bad["recent_closed_at_least"]:
        return "주의"
    if n >= mid["closed_at_least"] or (avg is not None and avg < mid["avg_under"]):
        return "보통"
    return "양호"


def attach_stores(sites: list[dict], stores: list[dict]) -> None:
    """상가정보(지금 영업 중)를 자리 키로 붙입니다.
    - 층·호까지 같은 자리 → match "자리"
    - 층·호가 없는 자리는 같은 건물(동+번지) → match "건물"
    인허가상 공실 추정인데 상가정보에 가게가 있으면 '다른 업종 입점'으로 표시합니다."""
    by_unit, by_bldg = defaultdict(list), defaultdict(list)
    for r in stores:
        key, dong, unit = site_key(r.get("lotno"), r.get("road"))
        if not key:
            continue
        item = {"name": r["name"], "cat": r.get("cat", "")}
        by_bldg[" ".join(key.split(" ")[:2])].append(item)
        if unit:
            by_unit[key].append(item)
    for s in sites:
        bldg = " ".join(s["key"].split(" ")[:2])
        found, how = (by_unit.get(s["key"]), "자리") if s["unit"] else (None, None)
        if not found and not s["unit"]:
            found, how = by_bldg.get(bldg), "건물"
        s["now"] = (found or [])[:5]
        s["now_match"] = how if found else None
        s["stats"]["occupied_other"] = bool(found) and not s["stats"]["current"]


def build(records: list[dict], today: date | None = None, source_label: str = "", stores: list[dict] | None = None,
          bjd: list[dict] | None = None) -> dict:
    today = today or date.today()
    t = today.isoformat()
    groups: dict[str, list[dict]] = defaultdict(list)
    place: dict[str, dict] = {}
    for r in records:
        if not r.get("open"):
            continue
        # 2000년 이전에 문 닫은 기록만 뺌 (그 전에 열어 지금까지 영업 중인 오래된 가게는 남김)
        if (r.get("close") or "9999")[:4] < str(REGION["min_open_year"]):
            continue
        if r.get("close") and r["close"] < r["open"]:
            continue  # 날짜 오류
        key, dong, unit = site_key(r.get("lotno"), r.get("road"))
        if not key:
            continue
        groups[key].append({
            "name": r["name"], "type": r["type"], "open": r["open"], "close": r.get("close"),
            "months": months_between(r["open"], r.get("close") or t),
        })
        p = place.get(key)
        if p is None or (r.get("road") and not p["road"]) or (r.get("lat") and not p["lat"]):
            place[key] = {"road": r.get("road") or "", "lotno": r.get("lotno") or "", "dong": dong,
                          "unit": unit, "lat": r.get("lat"), "lng": r.get("lng")}

    sites, multi = [], []
    for key in sorted(groups):
        hist = sorted(groups[key], key=lambda h: h["open"])
        # 같은 '자리'에 동시에 3곳 이상 영업한 적이 있으면 백화점·마트·휴게소처럼 여러 가게가 함께 있는 곳
        # → 한 자리의 간판 교체로 볼 수 없어 자리 비교(주의도·순위)에서 뺌
        addr = f"{place[key]['road']} {place[key]['lotno']}"
        if max_concurrent(hist, t) >= MULTI_AT or any(w in addr for w in REGION.get("multi_words", [])):
            multi.append(key)
            continue
        i = len(sites)
        closed = [h for h in hist if h["close"]]
        current = next((h for h in reversed(hist) if not h["close"]), None)
        sites.append({
            "id": f"S{i + 1:05d}", "key": key, **place[key],
            "history": hist,
            "stats": {
                "count": len(hist),
                "closed": len(closed),
                "avg_months": round(statistics.mean(h["months"] for h in closed), 1) if closed else None,
                "recent_closed_2y": sum(1 for h in closed if (today - _d(h["close"])).days <= RISK["recent_days"]),
                "current": current["name"] if current else None,
                "current_type": current["type"] if current else None,
                "vacant_since": None if current else max(h["close"] for h in closed),
            },
            "risk": risk_level(hist, today),
        })

    attach_stores(sites, stores or [])

    agg, opens, closes = defaultdict(list), defaultdict(int), defaultdict(int)
    for s in sites:
        for h in s["history"]:
            opens[h["open"][:4]] += 1
            if h["close"]:
                closes[h["close"][:4]] += 1
                agg[(s["dong"], h["type"])].append(h["months"])
                agg[("전체", h["type"])].append(h["months"])
    area = [{"dong": d, "type": ty, "avg_months": round(statistics.mean(v), 1), "n": len(v)}
            for (d, ty), v in sorted(agg.items()) if len(v) >= 3]

    return {
        "meta": {
            "region": REGION["name"], "source": source_label, "generated": t,
            "site_count": len(sites), "record_count": sum(len(s["history"]) for s in sites),
            "store_count": len(stores or []),
            "multi_excluded": len(multi),
            "note": "동네는 법정동 기준입니다. 같은 건물에서 층·호가 기록되지 않은 경우 건물 단위로 묶었습니다. "
                    f"백화점·마트·휴게소처럼 한 층에 여러 가게가 함께 있는 곳 {len(multi)}곳은 자리 비교에서 뺐습니다.",
        },
        "area_stats": area,
        # 지도에서 행정동 경계를 겹쳐 보기 위한 자료 (출처: 통계청 SGIS, 가공 vuski/admdongkor, CC BY 4.0)
        "bjd": bjd or [],
        "risk_rules": RISK,
        "areas": [{"name": f["properties"]["name"], "geometry": f["geometry"]} for f in _GEO["features"]],
        "by_year": {"open": dict(sorted(opens.items())), "close": dict(sorted(closes.items()))},
        "sites": sites,
    }
