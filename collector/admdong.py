"""지도 겹쳐 보기용 의정부시 행정동 경계 (자료 판정에는 쓰지 않음).

경계: rules/admdong_uijeongbu.geojson (통계청 SGIS 행정동 경계, 가공 vuski/admdongkor ver20261001, CC BY 4.0)
행정동이 바뀌면(분동·통합) admdongkor 새 버전에서 의정부시만 다시 뽑아 파일만 바꿉니다.
법정동 경계는 지도에서 브이월드 '행정구역도(lt_c_ademd)' WMS 로 바로 그립니다.
"""
from __future__ import annotations

import json
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / "rules" / "admdong_uijeongbu.geojson"
_GEO = json.loads(PATH.read_text(encoding="utf-8"))
NAMES = [f["properties"]["name"] for f in _GEO["features"]]
