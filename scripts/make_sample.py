"""
make_sample.py — 시안 확인용 '가상' 데이터 생성기.
실제 인허가 API와 같은 항목 구조로 의정부시 점포 이력을 만들어 build.py 로 변환합니다.
상호명·번지는 모두 가상입니다. 실제 데이터는 collector/collect.py 가 대체합니다.
"""
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collector"))
import json  # noqa: E402
from history import build  # noqa: E402
from normalize import type_of  # noqa: E402

random.seed(20261119)

# 행정동별: (대표 법정동 후보, 주요 도로명, 가중치) — 시안용 가상 값
DONGS = {
    "의정부1동": (["의정부동"], ["시민로", "행복로", "태평로"], 1.4),
    "의정부2동": (["의정부동"], ["청사로", "시민로", "평화로"], 0.8),
    "호원1동":   (["호원동"], ["평화로", "호암로"], 0.7),
    "호원2동":   (["호원동"], ["회룡로", "호국로"], 0.6),
    "장암동":    (["장암동"], ["동일로", "장암로"], 0.4),
    "신곡1동":   (["신곡동"], ["신곡로", "추동로"], 0.8),
    "신곡2동":   (["신곡동"], ["용민로", "신곡로"], 0.6),
    "송산1동":   (["용현동"], ["용민로", "오목로"], 0.7),
    "송산2동":   (["민락동"], ["민락로", "용민로"], 0.9),
    "송산3동":   (["민락동", "낙양동"], ["오목로", "낙양로"], 0.7),
    "자금동":    (["금오동", "자일동"], ["금신로", "천보로"], 0.8),
    "가능동":    (["가능동"], ["가능로", "평화로"], 0.7),
    "흥선동":    (["가능동", "의정부동"], ["흥선로", "가능로"], 0.6),
    "녹양동":    (["녹양동"], ["녹양로", "평화로"], 0.5),
    "고산동":    (["고산동", "산곡동"], ["고산로", "산곡로"], 0.4),
}
import admdong  # noqa: E402  (행정동 경계 안에 가상 점을 고르게 놓기 위해서만 사용)

_FEAT = {f["properties"]["name"]: f for f in admdong._GEO["features"]}


def _polys(g):
    return g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]


def _inside(x, y, ring):
    c, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi, xj, yj = ring[i][0], ring[i][1], ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            c = not c
        j = i
    return c


def point_in(adm):
    polys = _polys(_FEAT[adm]["geometry"])
    ring = [p for poly in polys for p in poly[0]]
    x0, x1 = min(p[0] for p in ring), max(p[0] for p in ring)
    y0, y1 = min(p[1] for p in ring), max(p[1] for p in ring)
    while True:
        x, y = random.uniform(x0, x1), random.uniform(y0, y1)
        if any(_inside(x, y, poly[0]) for poly in polys):
            return round(y, 6), round(x, 6)


# 업종: (업종구분, 업태명, 평균 생존 개월, 이름 재료)
TYPES = [
    ("휴게음식점", "커피숍", 28, ["커피", "카페", "로스터스", "다방", "브루"]),
    ("일반음식점", "통닭(치킨)", 36, ["치킨", "통닭", "후라이드"]),
    ("일반음식점", "한식", 52, ["식당", "밥상", "국밥", "한우", "보쌈"]),
    ("일반음식점", "분식", 30, ["분식", "김밥", "떡볶이"]),
    ("일반음식점", "중국식", 48, ["반점", "각", "짬뽕"]),
    ("일반음식점", "일식", 38, ["스시", "돈카츠", "라멘", "횟집"]),
    ("일반음식점", "경양식", 32, ["파스타", "비스트로", "버거"]),
    ("일반음식점", "호프/통닭", 34, ["호프", "포차", "술집", "이자카야"]),
    ("제과점", "제과점영업", 44, ["베이커리", "제과", "빵집"]),
    ("휴게음식점", "편의점", 60, ["편의점"]),
]
WEIGHTS = [26, 12, 18, 9, 6, 6, 6, 9, 5, 3]
PREFIX = ["달빛", "온기", "하루", "새봄", "골목", "바삭", "정성", "소담", "푸른", "한결",
          "든든", "모퉁이", "작은", "행복", "참", "오늘", "다온", "늘봄", "해든", "미소",
          "도담", "솔", "라온", "별", "이음", "고운", "누리", "다솜", "마루", "서로"]

TODAY = date(2026, 11, 19)
START = date(2009, 1, 1)


def rand_months(mean):
    # 지수분포 + 최소 3개월
    return max(6, int(random.expovariate(1 / mean)))


def make_name(words):
    w = random.choice(words)
    return f"{random.choice(PREFIX)}{w}" if random.random() < 0.8 else f"{w} {random.choice(PREFIX)}점"


records = []
site_no = 0
for adm, (bjds, roads, weight) in DONGS.items():
    n_sites = int(30 * weight)
    for _ in range(n_sites):
        site_no += 1
        road = random.choice(roads)
        bldg = random.randint(10, 320)
        lot = f"{random.randint(100, 899)}-{random.randint(1, 30)}"
        floor = random.choice(["1층", "1층", "1층", "2층", "지하1층"])
        ho = f"{random.randint(1, 3)}0{random.randint(1, 5)}호"
        dong = random.choice(bjds)
        lat, lng = point_in(adm)
        if random.random() < 0.04:  # 좌표 없는 옛 기록 흉내 → 행정동 '추정' 확인용
            lat = lng = None
        # 이 자리의 '체질': 어떤 자리는 유독 회전이 빠름
        churn = random.choices([0.7, 1.1, 1.7, 2.6], [0.15, 0.30, 0.33, 0.22])[0]
        t = START + timedelta(days=random.randint(0, 3600))
        first_type = random.choices(TYPES, WEIGHTS)[0]
        while t < TODAY:
            ty = first_type if random.random() < 0.35 else random.choices(TYPES, WEIGHTS)[0]
            months = int(rand_months(ty[2]) * churn) or 3
            close = t + timedelta(days=int(months * 30.4))
            rec = {
                "source": "sample",
                "name": make_name(ty[3]),
                "uptae": ty[1],
                "type": type_of(ty[1], ty[0]),
                "open": t.isoformat(),
                "close": close.isoformat() if close < TODAY else None,
                "lotno": f"경기도 의정부시 {dong} {lot}",
                "road": f"경기도 의정부시 {road} {bldg}, {floor} {ho} ({dong})",
                "lat": lat,
                "lng": lng,
            }
            records.append(rec)
            if close >= TODAY:
                break
            # 공실 기간 0~10개월 (가끔 그대로 공실)
            if random.random() < 0.12 and close > date(2024, 6, 1):
                break
            t = close + timedelta(days=random.randint(10, 300))

# 상가정보(소상공인) 샘플: 일부 자리에 다른 업종 가게가 들어와 있다고 가정
_cats = [("모아휴대폰", "휴대폰 판매"), ("한빛학원", "입시학원"), ("고운옷집", "여성 의류"), ("새봄약국", "약국"), ("반짝네일", "네일숍")]
stores = [{"name": _cats[i % 5][0], "cat": _cats[i % 5][1], "lotno": r["lotno"], "road": r["road"]}
          for i, r in enumerate(random.sample(records, 60))]
data = build(records, today=TODAY, source_label="샘플(가상) 데이터 — 시안 확인용", stores=stores)
data = {"updated_at": "2026-11-19T09:10+09:00", **data}
(ROOT / "designs" / "sample" / "sites.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(data["meta"])
