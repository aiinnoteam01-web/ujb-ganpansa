"""소상공인시장진흥공단_상가(상권)정보 API — '지금 그 자리에 무엇이 있나'를 보완합니다.

왜 필요한가
- 인허가 자료는 음식점·카페·제과점처럼 허가·신고 업종만 있어, 옷가게·휴대폰 매장·학원처럼
  다른 업종이 들어온 자리를 '공실 추정'으로 잘못 보일 수 있습니다.
- 상가정보는 지금 영업 중인 상가를 업종 구분 없이 담고, 층·호 정보도 있어 자리 구분을 돕습니다.
- 개업·폐업 이력은 없으므로 '간판 내력'은 인허가 자료로, '지금 입점'은 상가정보로 보여 줍니다.

호출: https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong
      divId=signguCd, key=41150(의정부시), numOfRows=1000, pageNo, type=json
처음 연결 때 inspect 워크플로에서 응답 필드명을 확인하세요.
"""
from __future__ import annotations

URL = "https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
SIGNGU_CD = "41150"  # 의정부시
PAGE_SIZE = 1000

FIELDS = {
    "name":  ["bizesNm"],
    "cat":   ["indsSclsNm", "indsMclsNm", "indsLclsNm"],
    "lotno": ["lnoAdr"],
    "road":  ["rdnmAdr"],
    "floor": ["flrNo"],
    "ho":    ["hoNo"],
    "lat":   ["lat"],
    "lng":   ["lon"],
}


def _pick(rec: dict, names: list[str]):
    for n in names:
        v = rec.get(n)
        if v not in (None, "", " "):
            return str(v).strip()
    return None


def params(page: int) -> dict:
    return {"divId": "signguCd", "key": SIGNGU_CD, "numOfRows": PAGE_SIZE, "pageNo": page, "type": "json"}


def normalize(rec: dict) -> dict:
    floor, ho = _pick(rec, FIELDS["floor"]), _pick(rec, FIELDS["ho"])
    detail = " ".join(x for x in [f"{floor}층" if floor and floor.lstrip("-").isdigit() else (floor or ""),
                                  f"{ho}호" if ho and ho.isdigit() else ""] if x)
    detail = detail.replace("-", "지하") if detail.startswith("-") else detail
    lat, lng = _pick(rec, FIELDS["lat"]), _pick(rec, FIELDS["lng"])
    return {
        "name": _pick(rec, FIELDS["name"]) or "(상호 미상)",
        "cat": _pick(rec, FIELDS["cat"]) or "",
        "lotno": _pick(rec, FIELDS["lotno"]) or "",
        # 층·호를 도로명 뒤에 붙여 인허가 자료와 같은 방식으로 자리 키를 만듦
        "road": f"{_pick(rec, FIELDS['road']) or ''}, {detail}" if detail else (_pick(rec, FIELDS["road"]) or ""),
        "lat": round(float(lat), 6) if lat else None,
        "lng": round(float(lng), 6) if lng else None,
    }
