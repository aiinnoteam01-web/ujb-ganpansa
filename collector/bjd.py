"""법정동 경계(선·이름)를 브이월드에서 받아 지도에 그릴 수 있게 저장합니다.

- 화면 지도의 법정동 경계를 '그림(WMS)'이 아닌 '선 데이터'로 그려야 색·굵기·동 이름을 정할 수 있음
- 수집할 때 한 번 받아 data/bjd.json 에 저장 → 실패하면 이전 파일을 그대로 씀 (화면은 그림 경계로 대체)
- 인증키: 환경변수 VWORLD_KEY (GitHub Secrets). 브이월드 키는 서비스 URL(도메인)과 함께 써야 함

순서대로 시도합니다.
 1) 브이월드 2D데이터 API  LT_C_ADEMD_INFO (속성 조건: 의정부 41150)
 2) 브이월드 WFS  lt_c_ademd (의정부 범위 BBOX)
"""
from __future__ import annotations

import math
import os

import requests

DOMAIN = "https://aiinnoteam01-web.github.io"
SIGUNGU = "41150"  # 의정부시
BBOX = (126.98, 37.68, 127.14, 37.79)  # 경도·위도 범위 (넉넉히)
UA = {"User-Agent": "ujb-ganpansa-collector/1.0"}


def _key() -> str:
    k = os.environ.get("VWORLD_KEY", "").strip()
    if not k:
        raise RuntimeError("VWORLD_KEY 없음 (법정동 경계는 그림 경계로 대체)")
    return k


def _lonlat(c):
    """좌표 순서가 (위도, 경도)로 오면 뒤집음 — 의정부는 경도 ≈127, 위도 ≈37."""
    x, y = float(c[0]), float(c[1])
    return [y, x] if x < 90 < y else [x, y]


def _rdp(pts, eps):
    """선 단순화 (Ramer–Douglas–Peucker)."""
    if len(pts) < 4:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy) or 1e-12
    far, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / norm
        if d > far:
            far, idx = d, i
    if far <= eps:
        return [pts[0], pts[-1]]
    return _rdp(pts[: idx + 1], eps)[:-1] + _rdp(pts[idx:], eps)


def _clean(geom: dict) -> dict:
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    out = []
    for poly in polys:
        rings = []
        for ring in poly:
            r = [[round(v, 5) for v in _lonlat(c)] for c in ring]
            if len(r) > 8:  # 닫힌 고리는 반으로 나눠 단순화 (시작=끝 점이라 한 번에 하면 무너짐)
                mid = len(r) // 2
                simple = _rdp(r[: mid + 1], 0.00004)[:-1] + _rdp(r[mid:], 0.00004)
                r = simple if len(simple) >= 4 else r
            if len(r) >= 4:
                rings.append(r)
        if rings:
            out.append(rings)
    return {"type": "MultiPolygon", "coordinates": out}


def _from_data_api(key: str) -> list[dict]:
    feats, page = [], 1
    while page <= 5:
        r = requests.get("https://api.vworld.kr/req/data", headers=UA, timeout=60, params={
            "service": "data", "request": "GetFeature", "data": "LT_C_ADEMD_INFO", "key": key, "domain": DOMAIN,
            "attrFilter": f"emdCd:like:{SIGUNGU}", "geometry": "true", "attribute": "true", "crs": "EPSG:4326",
            "format": "json", "size": 100, "page": page})
        r.raise_for_status()
        res = r.json().get("response", {})
        if res.get("status") != "OK":
            raise RuntimeError(f"2D데이터 API: {res.get('status')} {res.get('error', {}).get('text', '')}")
        got = res["result"]["featureCollection"]["features"]
        feats += got
        if page >= int(res.get("page", {}).get("total", 1)):
            break
        page += 1
    return feats


def _from_wfs(key: str) -> list[dict]:
    x0, y0, x1, y1 = BBOX
    last = None
    for bbox in (f"{y0},{x0},{y1},{x1},EPSG:4326", f"{x0},{y0},{x1},{y1},EPSG:4326"):  # 축 순서가 버전마다 달라 둘 다 시도
        r = requests.get("https://api.vworld.kr/req/wfs", headers=UA, timeout=60, params={
            "SERVICE": "WFS", "REQUEST": "GetFeature", "VERSION": "1.1.0", "TYPENAME": "lt_c_ademd",
            "BBOX": bbox, "SRSNAME": "EPSG:4326", "OUTPUT": "application/json", "MAXFEATURES": 500,
            "KEY": key, "DOMAIN": DOMAIN})
        r.raise_for_status()
        try:
            feats = r.json().get("features", [])
        except ValueError as e:
            last = RuntimeError(f"WFS 응답이 JSON 아님: {r.text[:120]}")
            continue
        if feats:
            return feats
    raise last or RuntimeError("WFS: 경계 0건")


def fetch(dongs: list[str]) -> list[dict]:
    """[{name, geometry(MultiPolygon, 경도·위도)}] — 의정부 법정동만."""
    key = _key()
    errors = []
    for how in (_from_data_api, _from_wfs):
        try:
            feats = how(key)
        except Exception as e:  # 다음 방법으로
            errors.append(f"{how.__name__}: {str(e)[:110]}")
            continue
        out = {}
        for f in feats:
            p = {k.lower(): v for k, v in (f.get("properties") or {}).items()}
            code = str(p.get("emd_cd") or p.get("emdcd") or "")
            name = p.get("emd_kor_nm") or p.get("emdkornm") or p.get("full_nm", "").split(" ")[-1]
            if code and not code.startswith(SIGUNGU):
                continue
            if name in dongs and f.get("geometry"):
                out[name] = {"name": name, "geometry": _clean(f["geometry"])}
        if out:
            return [out[d] for d in dongs if d in out]
        errors.append(f"{how.__name__}: 의정부 법정동 0곳")
    raise RuntimeError(" / ".join(errors))
