import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collector"))

import admdong as a  # noqa: E402


def test_overlay_has_15_dongs():
    assert len(a.NAMES) == 15 and "송산2동" in a.NAMES


def test_overlay_is_wgs84_polygons():
    f = a._GEO["features"][0]
    ring = f["geometry"]["coordinates"][0][0] if f["geometry"]["type"] == "MultiPolygon" else f["geometry"]["coordinates"][0]
    lng, lat = ring[0]
    assert 126.9 < lng < 127.2 and 37.6 < lat < 37.85
