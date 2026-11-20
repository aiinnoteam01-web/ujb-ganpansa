"""시안 A·B·C 를 미리보기용 단일 파일과 '시안 캔버스' 한 장으로 묶습니다.

  dist/design-a.html, design-b.html, design-c.html  : 샘플 데이터까지 들어간 단독 파일
  dist/canvas.html                                    : 세 시안을 탭으로 비교하는 캔버스 (claude.ai 아티팩트용)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "designs"
OUT = ROOT / "dist"
OUT.mkdir(exist_ok=True)

base_css = (D / "base.css").read_text(encoding="utf-8")
core_js = (D / "core.js").read_text(encoding="utf-8")
data = json.loads((ROOT / "designs" / "sample" / "sites.json").read_text(encoding="utf-8"))
data_js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def inline(html: str, with_data: bool) -> str:
    html = html.replace('<link rel="stylesheet" href="base.css">', f"<style>{base_css}</style>")
    pre = f"<script>window.EMBEDDED_DATA={data_js};</script>\n" if with_data else ""
    return html.replace('<script src="core.js"></script>', pre + f"<script>{core_js}</script>")


designs = {}
for k in "abcde":
    src = (D / f"{k}.html").read_text(encoding="utf-8")
    (OUT / f"design-{k}.html").write_text(inline(src, True), encoding="utf-8")
    designs[k] = inline(src, False)

INFO = {
    "a": ("A", "자리 이력서 (수정안)", False, "서류·장부 느낌에 C의 '동네별 주의 자리 비율'을 더했습니다. 상세는 그래프 대신 정확한 숫자 표 + 브이월드 위치 지도.",
          ["법정동 13곳 주의 비율: 주의 n곳 / 전체 n곳 · % · 폐업 평균 · 공실", "상세: 업종 변천사·평균 비교를 개월 수 표로", "상세 지도: 브이월드 배경 + 경계선(법정동/행정동/둘 다) 선택 + 건물·필지 켜기"]),
    "b": ("B", "연표 목록형", False, "목록 한 줄이 곧 그 자리의 연표. 막대가 잘게 끊긴 자리 = 자주 바뀐 자리.",
          ["2009~현재 연표를 한 화면에서 비교", "데이터를 좋아하는 사용자에게 강함", "작은 화면에서는 연표가 좁아짐"]),
    "c": ("C", "동네 현황판", False, "동네별 '주의 자리 비율'을 먼저 보고 동네를 눌러 자리로 내려가는 공공 현황판.",
          ["13개 법정동 색 타일(진할수록 주의 많음)", "큰 글자·큰 단추, 정책 담당자 보고용", "첫 화면이 다소 무거움"]),
    "d": ("D", "서예·수묵화풍 (2차)", True, "한지 결, 먹 번짐 산수와 난초, 세로쓰기 붓글씨 제목, 붓획 구분선, 낙관 도장. 지도도 먹색으로.",
          ["동네 비율을 먹 번짐 칸(옅음→짙음)으로", "주의도는 붉은 낙관, 구분선은 붓획", "지도 배경은 백색지도 + 먹색 처리"]),
    "e": ("E", "90년대 PC통신풍", False, "파란 화면·고정폭 한글·이중선 창·번호 메뉴. 그 시절 통신 화면 분위기로 같은 기능을.",
          ["동네 비율을 글자 막대(█ 한 칸 = 5%)로", "선택 항목은 반전색, 아래 상태줄", "화제성은 높지만 오래 읽기엔 눈이 피로할 수 있음"]),
}

cards = "".join(
    f"""<button class="card" data-k="{k}" type="button" aria-pressed="{'true' if rec else 'false'}">
  <span class="tag">시안 {a}</span>{'<span class="rec">확정</span>' if rec else ''}<h2>{name}</h2><p>{desc}</p><ul>{''.join(f'<li>{x}</li>' for x in pts)}</ul></button>"""
    for k, (a, name, rec, desc, pts) in INFO.items()
)

canvas = f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>의정부 간판사 — 시안 캔버스</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;800&amp;family=Nanum+Brush+Script&amp;display=swap">
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "Noto Sans KR", system-ui, sans-serif; background: #f3f1ee; color: #1d1b19; word-break: keep-all; }}
header {{ max-width: 1280px; margin: 0 auto; padding: 28px 24px 8px; }}
h1 {{ margin: 0; font-size: 26px; letter-spacing: -.5px; }}
.sub {{ margin: 6px 0 0; color: #5d5852; font-size: 14.5px; }}
.flow {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; font-size: 13px; color: #5d5852; }}
.flow span {{ background: #fff; border: 1px solid #e3ddd5; border-radius: 99px; padding: 3px 10px; }}
.cards {{ max-width: 1280px; margin: 0 auto; padding: 16px 24px; display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; }}
.card {{ display: flex; flex-direction: column; justify-content: flex-start; align-items: flex-start; text-align: left; font: inherit; color: inherit; background: #fff; border: 0; border-radius: 16px; padding: 18px 20px; cursor: pointer; box-shadow: inset 0 0 0 1px #e3ddd5; }}
.card[aria-pressed="true"] {{ box-shadow: inset 0 0 0 3px #1d1b19; }}
.card h2 {{ margin: 6px 0 4px; font-size: 19px; }}
.card p {{ margin: 0; color: #5d5852; font-size: 14px; }}
.card ul {{ margin: 10px 0 0; padding-left: 18px; font-size: 13.5px; color: #3c3833; }}
.rec {{ margin-left: 6px; font-size: 12px; font-weight: 800; background: #b8322a; color: #fff; border-radius: 6px; padding: 2px 8px; }}
.names {{ max-width: 1280px; margin: 0 auto; padding: 4px 24px 14px; }}
.names h2 {{ font-size: 18px; margin: 0 0 8px; }}
.nmgrid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 10px; }}
.nm {{ background: #f6f1e5; border-radius: 12px; padding: 12px 16px; box-shadow: inset 0 0 0 1px #e3ddd5; }}
.nm-t {{ font-family: "Nanum Brush Script", serif; font-size: 40px; line-height: 1; overflow-wrap: anywhere; }}
.nm em {{ font-style: normal; font-size: 12px; font-weight: 800; background: #b12e26; color: #fff; border-radius: 5px; padding: 1px 7px; margin-left: 8px; vertical-align: 8px; }}
.nm p {{ margin: 6px 0 0; font-size: 13px; color: #4b463f; }}
.why {{ max-width: 1280px; margin: 0 auto; padding: 0 24px 6px; }}
.why div {{ background: #fff; border-radius: 14px; padding: 14px 18px; box-shadow: inset 0 0 0 1px #e3ddd5; font-size: 14px; color: #3c3833; }}
.why b {{ color: #1d1b19; }}
.why ol {{ margin: 6px 0 0; padding-left: 20px; }}
.tag {{ font-size: 12px; font-weight: 800; background: #1d1b19; color: #fff; border-radius: 6px; padding: 2px 8px; }}
.bar {{ max-width: 1280px; margin: 0 auto; padding: 0 24px 10px; display: flex; gap: 8px; align-items: center; font-size: 14px; }}
.bar button {{ font: inherit; border: 1px solid #d8d1c7; background: #fff; border-radius: 8px; padding: 6px 12px; cursor: pointer; }}
.bar button[aria-pressed="true"] {{ background: #1d1b19; color: #fff; border-color: #1d1b19; }}
.bar .note {{ margin-left: auto; color: #6f6962; font-size: 13px; }}
.stage {{ max-width: 1280px; margin: 0 auto 40px; padding: 0 24px; }}
.frame {{ margin: 0 auto; background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,.08), inset 0 0 0 1px #e3ddd5; transition: width .2s; }}
iframe {{ display: block; width: 100%; height: 900px; border: 0; }}
@media (max-width: 900px) {{ .cards {{ grid-template-columns: 1fr; }} }}
</style></head>
<body>
<header>
  <h1>의정부 간판사 — 시안 캔버스</h1>
  <p class="sub">※ 이 캔버스에서는 외부 지도 그림을 불러올 수 없어 상세 지도가 대체 그림(점선 = 행정동 경계)으로 보입니다. 실제 사이트에서는 브이월드 지도와 선택 박스가 나옵니다.<br>점포 자리 이력 조회 사이트 시안 5가지입니다. 카드를 눌러 아래에서 실제로 눌러 보며 비교하세요. 데이터는 화면 확인용 <b>가상 샘플</b>(의정부시 13개 법정동, 자리 {data['meta']['site_count']}곳)입니다.</p>
  <div class="flow"><span>① 숫자 타일</span><span>② 주소·번지·상호 검색</span><span>③ 조건</span><span>④ 목록 30곳씩</span><span>⑤ 상세: 업종 변천사·평균 비교</span></div>
</header>
<section class="cards">{cards}</section>
<section class="names"><h2>이름 후보 (붓글씨 미리보기)</h2><div class="nmgrid"><div class="nm"><span class="nm-t">터무늬</span><p>'터무니'(터를 잡은 자취)에서 따온 이름. 그 자리에 남은 가게들의 무늬(내력)를 본다는 뜻. 수묵화풍 D와 가장 잘 어울립니다.</p></div><div class="nm"><span class="nm-t">자리내력</span><p>가장 쉽게 뜻이 전달되는 이름. '이 자리의 내력'. 정보형 A·장부형 화면과 잘 맞습니다.</p></div><div class="nm"><span class="nm-t">간판사</span><em>확정</em><p>간판이 바뀌어 온 역사. 짧고 기억하기 쉬우며 붓글씨와 잘 어울립니다.</p></div><div class="nm"><span class="nm-t">터살핌</span><p>계약하기 전에 '터를 살핀다'는 행동을 이름에 담았습니다. 창업 상담·민원 안내 문구로 쓰기 좋습니다.</p></div><div class="nm"><span class="nm-t">그 자리</span><p>'그 자리 그 가게'처럼 말로 부르기 쉬운 이름. 친근한 느낌이 필요할 때.</p></div><div class="nm"><span class="nm-t">자리모아</span><p>청년모아·지원모아와 같은 '모아' 시리즈 이름. 시리즈 통일감이 장점입니다.</p></div></div></section>
<section class="why"><div><b>확정: 이름 「간판사」 + 시안 D 서예·수묵화풍</b>
<ol><li>한지 결·먹 번짐·붓글씨 제목·낙관으로 다른 공공 사이트와 확실히 구별되는 인상을 줍니다.</li>
<li>구성(숫자 → 동네별 주의 비율 → 검색·조건 → 자리 장부 → 간판 내력서)과 숫자 표·지도는 A 수정안과 같아 정보는 그대로입니다.</li>
<li>지도는 백색 배경을 먹색으로 처리해 화면 분위기와 맞췄습니다.</li></ol></div></section>
<div class="bar"><span>보기</span><button type="button" data-w="100%" aria-pressed="true">데스크톱</button><button type="button" data-w="400px" aria-pressed="false">모바일</button>
  <span class="note">빠른 조건 단추를 누르거나 주소·상호를 검색하고, 목록의 자리를 눌러 이력을 열어 보세요.</span></div>
<div class="stage"><div class="frame" id="frame"><iframe id="view" title="시안 미리보기"></iframe></div></div>
<script type="application/json" id="sample">{data_js}</script>
<script>
const DESIGNS = {json.dumps(designs, ensure_ascii=False).replace("</", "<\\/")};
const view = document.getElementById("view");
function show(k) {{
  document.querySelectorAll(".card").forEach(c => c.setAttribute("aria-pressed", String(c.dataset.k === k)));
  // 샌드박스 안에서도 동작하도록 각 시안에 샘플 데이터를 직접 넣음
  const json = document.getElementById("sample").textContent;
  const marker = DESIGNS[k].lastIndexOf("<script>");
  view.srcdoc = DESIGNS[k].slice(0, marker) + "<script>window.EMBEDDED_DATA=" + json + ";<\\/script>" + DESIGNS[k].slice(marker);
}}
document.querySelectorAll(".card").forEach(c => c.addEventListener("click", () => {{ show(c.dataset.k); document.getElementById("frame").scrollIntoView({{ behavior: "smooth", block: "start" }}); }}));
document.querySelectorAll(".bar button").forEach(b => b.addEventListener("click", () => {{
  document.querySelectorAll(".bar button").forEach(x => x.setAttribute("aria-pressed", String(x === b)));
  document.getElementById("frame").style.width = b.dataset.w;
}}));
show("d");
</script>
</body></html>"""
(OUT / "canvas.html").write_text(canvas, encoding="utf-8")
for f in sorted(OUT.iterdir()):
    print(f.name, f.stat().st_size)
