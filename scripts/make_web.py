"""선택한 시안(designs/<글자>.html)을 실제 사이트 파일(web/index.html·app.css·app.js)로 옮깁니다.

사용법:  python scripts/make_web.py d
- 시안의 <style> → web/app.css (base.css 와 합침)
- 시안의 window.DESIGN 설정 + designs/core.js → web/app.js
- HTML 에는 보안 정책(CSP)과 Leaflet·config.js 연결을 넣음 (인라인 스크립트 없음)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D, W = ROOT / "designs", ROOT / "web"
k = (sys.argv[1] if len(sys.argv) > 1 else "d").lower()
src = (D / f"{k}.html").read_text(encoding="utf-8")

css = re.search(r"<style>\n(.*?)</style>", src, re.S).group(1)
(W / "app.css").write_text(f"/* 의정부 간판사 · 시안 {k.upper()} */\n" + (D / "base.css").read_text(encoding="utf-8") + "\n" + css, encoding="utf-8")
cfg = re.search(r"<script>(window\.DESIGN = .*?)</script>", src).group(1)
(W / "app.js").write_text(cfg + "\n" + (D / "core.js").read_text(encoding="utf-8"), encoding="utf-8")

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
       "img-src 'self' data: https://api.vworld.kr https://xdworld.vworld.kr; connect-src 'self'; base-uri 'self'; form-action 'self'")
html = re.sub(r'<link rel="stylesheet" href="base.css">\n<style>.*?</style>',
              '<link rel="stylesheet" href="lib/leaflet.css">\n<link rel="stylesheet" href="app.css">\n'
              '<script src="lib/leaflet.js" defer></script>\n<script src="config.js" defer></script>\n<script src="app.js" defer></script>', src, flags=re.S)
html = re.sub(r'<script>window\.DESIGN.*?</script>\n<script src="core.js"></script>\n', "", html)
html = html.replace('<meta name="viewport" content="width=device-width, initial-scale=1">',
                    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
                    f'<meta http-equiv="Content-Security-Policy" content="{CSP}">\n'
                    '<meta name="description" content="의정부시 점포 자리마다 어떤 가게가 몇 번 열고 닫았는지, 간판이 바뀌어 온 내력을 인허가 기록으로 보여 줍니다.">')
html = re.sub(r"<title>.*?</title>", "<title>의정부 간판사</title>", html)
(W / "index.html").write_text(html, encoding="utf-8")
print(f"web/ ← 시안 {k.upper()}")
