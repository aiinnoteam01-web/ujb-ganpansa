# 의정부 간판사 — 점포 자리 간판 내력 조회

주소를 넣으면 그 자리에서 어떤 가게가 몇 번 열고 닫았는지(간판이 몇 번 바뀌었는지), 평균 얼마나 버텼는지 보여 주는 사이트입니다. 화면은 시안 D 서예·수묵화풍입니다.
청년모아·지원모아와 **같은 방법론**(GitHub Actions 수집 → data 브랜치 JSON → GitHub Pages)으로 만듭니다.

## 폴더 구성

| 경로 | 하는 일 |
|---|---|
| `collector/collect.py` | 인허가 API 3곳(일반음식점·휴게음식점·제과점) + 상가정보 수집, 출처별 실패 시 이전 자료 유지 |
| `collector/semas.py` | 소상공인 상가(상권)정보: 지금 그 자리에 있는 가게(업종 무관)로 공실 추정을 보정 |
| `collector/normalize.py` | 원본 한 건 → 공통 형식 (날짜·업종·주소 키·좌표 변환) |
| `collector/history.py` | 같은 '점포 자리'로 묶어 이력·평균·주의도 계산 → `data/sites.json` |
| `rules/types.yaml` | 업태명 → 화면 업종 (화면 `TYPES` 와 띄어쓰기까지 같아야 함) |
| `rules/risk.yaml` | 주의도 기준 (폐업 횟수·평균 영업기간) |
| `rules/region.yaml` | 의정부 지번주소 필터, 동네(법정동 13개) 목록 |
| `rules/admdong_uijeongbu.geojson` | 의정부시 행정동 경계 (통계청 SGIS, 가공 vuski/admdongkor ver20261001, CC BY 4.0) |
| `collector/admdong.py` | 지도 겹쳐 보기용 행정동 경계 불러오기 (자료 판정에는 안 씀) |
| `tests/` | 규칙 테스트 (수집 전에 Actions 가 먼저 돌림) |
| `web/` | 사이트 (index.html · app.css · app.js, 외부 스크립트 없음, CSP 적용) |
| `designs/` | 시안 원본 (A·B·C·D·E). 화면 동작은 `core.js` 하나를 같이 씀. **현재 `web/` 은 D 서예·수묵화풍** |
| `scripts/make_web.py` | 시안을 사이트로 옮김: `python scripts/make_web.py d` |
| `scripts/make_sample.py` | 시안 확인용 가상 데이터 → `designs/sample/sites.json` (실제 자료는 data 브랜치) |
| `.github/workflows/` | collect(매일 09:10) → deploy → check(09:40), inspect(처음 연결 때 버튼으로 실행) |

## 동네 기준: 법정동 (행정동은 지도에서만)

- 동네 버튼·동네별 주의 비율·동네 평균은 **법정동**(13개) 기준입니다. 지번주소와 도로명주소 괄호에 나오는 동 이름과 같아 별도 변환·추정이 없습니다.
- 행정동은 **지도에서만** 경계선으로 겹쳐 봅니다(선택 박스: 법정동 / 행정동 / 둘 다 / 없음).
- 같은 자리를 묶는 기준은 지번(법정동+번지)+층·호입니다.

## 진행 순서 (차근차근)

### 0. 준비물
- GitHub 계정 `aiinnoteam01-web` (청년모아·지원모아와 같은 계정)
- 공공데이터포털 인증키(Decoding) — 지원모아의 `DATA_GO_KR_KEY` 와 같은 키
- 브이월드 인증키 — 서비스 URL 에 `https://aiinnoteam01-web.github.io` 등록
- 이 저장소 압축 파일(ujb-ganpansa.zip)

### 1. 공공데이터포털 활용신청 (10분)
data.go.kr 에서 아래 4개를 찾아 [활용신청] (자동승인)
- 행정안전부_식품_일반음식점 조회서비스 (필수 · 간판 내력)
- 행정안전부_식품_휴게음식점 조회서비스 (필수 · 카페·분식 등)
- 행정안전부_식품_제과점영업 조회서비스 (필수 · 빵집)
- 소상공인시장진흥공단_상가(상권)정보 (권장 · 지금 입점 가게, 층·호) — 실패해도 사이트는 정상 동작

마이페이지 → 데이터활용 → Open API → 활용신청 현황 → 각 API [상세보기] 의 **요청주소**를 메모합니다.
(지도 레이어는 브이월드 키 하나로 쓰므로 공공데이터포털에서 따로 할 일은 없습니다.)

### 2. 저장소 만들기 (5분)
github.com → 오른쪽 위 [+] → New repository
- Repository name: `ujb-ganpansa`
- **Public** (무료 GitHub Pages 조건)
- README·.gitignore·license 추가는 **모두 체크하지 않음** → [Create repository]

### 3. 파일 올리기 (10분)
1. 압축을 풉니다. 안에 `.github`, `collector`, `designs`, `rules`, `scripts`, `tests`, `web`, `README.md` 등이 보여야 합니다.
2. 새 저장소 화면의 **uploading an existing file** 을 누르고, 압축 푼 폴더 안의 **내용물 전체**를 끌어다 놓습니다.
3. 아래 Commit changes 를 누릅니다.
4. **확인:** 저장소에 `.github/workflows` 폴더가 있어야 합니다. 맥에서는 점(.)으로 시작하는 폴더가 숨겨져 안 올라갈 수 있습니다 → Finder 에서 `Cmd+Shift+.` 로 숨김 파일을 보이게 한 뒤 다시 올리거나, GitHub Desktop 으로 올리세요.

### 4. 비밀값(Secrets) 넣기 (3분)
Settings → Secrets and variables → Actions → [New repository secret] 을 두 번:
- `DATA_GO_KR_KEY` = 공공데이터포털 인증키(Decoding)
- `VWORLD_KEY` = 브이월드 인증키

### 5. 권한과 Pages 켜기 (2분)
- Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save
- Settings → Pages → Build and deployment → Source: **GitHub Actions**

### 6. 호출 주소와 필드명 맞추기 (처음 1번, 10분)
1. Actions 탭 → 왼쪽 **inspect** → [Run workflow] → 끝나면 눌러서 로그를 엽니다.
2. `=== 일반음식점 …` 아래에
   - `!! 실패` 가 보이면: 1단계에서 메모한 **요청주소**로 `collector/collect.py` 의 `SOURCES` 주소를 고칩니다
     (파일을 열고 연필 아이콘으로 편집 → Commit changes). 고친 뒤 inspect 를 다시 실행합니다.
   - `전체 N건, 첫 건` 과 JSON 이 보이면 성공입니다. JSON 의 항목 이름(예: `BPLC_NM`, `LOTNO_ADDR`, `CLSBIZ_YMD`, `CRD_INFO_X`)이
     `collector/normalize.py` 의 `FIELDS` 후보에 있는지 봅니다. 없으면 그 이름을 후보 목록 맨 앞에 추가합니다.
3. 세 곳 모두 성공할 때까지 반복합니다.

### 7. 첫 수집과 배포 (10분)
1. Actions → **collect** → [Run workflow]. 규칙 테스트 → 수집 → `data` 브랜치 저장 → **deploy 자동 실행** 순서로 진행됩니다.
2. Actions → deploy 가 초록색이 되면 사이트 주소가 열립니다: `https://aiinnoteam01-web.github.io/ujb-ganpansa/`
3. collect 가 빨간색이면 로그의 `!! 실패` 또는 `status` 부분을 확인합니다(키는 `***` 로 가려져 나옵니다).

### 8. 화면 점검 (20분)
- 아는 가게 몇 곳을 검색해 개업·폐업 날짜와 지도 위 위치가 맞는지 확인합니다.
- 상세 화면의 지도에서 배경·경계선(법정동/행정동)·건물·필지 선택이 동작하는지 봅니다.
  회색으로만 나오면 F12 → Network 에서 `api.vworld.kr` 응답(키·도메인 오류)을 확인합니다.
- 업종이 '기타'로 많이 빠지면 `rules/types.yaml` 에 낱말을 더합니다.

### 9. 이후 운영
- 매일 09:10 자동 수집 → 자동 배포, 09:40 check 가 수집 결과를 점검합니다.
- 한 출처가 실패해도 이전 자료를 그대로 보여 주고 `status.json` 에 기록합니다.
- 화면을 다른 시안으로 바꾸려면 `python scripts/make_web.py a` 처럼 실행해 `web/` 을 다시 만듭니다.

## 상세 화면의 지도 (모두 공공데이터)

| 지도에서 쓰는 곳 | 공공데이터포털 API | 호출 |
|---|---|---|
| 배경지도(일반·위성·백색) | 국토교통부_WMTS/TMS API | `https://api.vworld.kr/req/wmts/1.0.0/{키}/{Base|Satellite|white}/{z}/{y}/{x}` |
| 법정동 경계선 | 국토교통부_행정구역도(WMS/WFS) | `https://api.vworld.kr/req/wms` layers=`lt_c_ademd` |
| 건물 윤곽 | 국토교통부_GIS건물통합정보(WMS/WFS) | `https://api.vworld.kr/ned/wms/BldgisSpceService` layers=`dt_d010` |
| 필지 경계 | 국토교통부_연속지적도 | `https://api.vworld.kr/req/wms` layers=`lp_pa_cbnd_bubun` |
| 행정동 경계선 | 통계청 SGIS 행정동 경계(가공 vuski/admdongkor, CC BY 4.0) | 저장소 파일 `rules/admdong_uijeongbu.geojson` |

- 지도 위 선택 박스: **배경**(일반/위성/백색), **경계선**(법정동+행정동/법정동/행정동/없음), **건물**, **필지**. 고른 값은 다른 자리를 열어도 유지됩니다.
- 지도 라이브러리는 Leaflet(저장소 `web/lib/`, BSD-2) 이고, 브이월드 인증키 하나로 위 레이어를 모두 씁니다.
- **키 넣는 법:** GitHub Settings → Secrets and variables → Actions → `VWORLD_KEY`. deploy 가 배포할 때만 `web/config.js` 에 써 넣습니다.
- 브이월드 키의 **서비스 URL** 에 `https://aiinnoteam01-web.github.io` 등록 필요. WMS 요청에는 `domain=` 으로 사이트 주소를 함께 보냅니다.
- 키가 없으면 대체 그림(같은 법정동 자리 + 행정동 점선 경계)으로 보입니다.
- CSP `img-src` 에 `https://api.vworld.kr`, `https://xdworld.vworld.kr` 추가해 두었습니다.
- 첫 배포 뒤 어떤 레이어가 안 보이면 F12 → Network 에서 해당 `api.vworld.kr` 응답을 확인하세요(키·도메인·레이어명 오류가 응답에 나옵니다). 건물(GIS건물통합정보) WMS 는 좌표계 EPSG:3857 요청을 지원하는지 확인이 필요합니다.

## 다음 점검 거리
- 같은 번지에 상가 건물이 큰 경우(층·호 미기재) 자리 구분 정확도
- 업종 '기타' 비율이 높으면 `types.yaml` 낱말 보강
- **좌표 변환(EPSG:5174 → 위경도)이 맞는지 표본 확인** — 지도 위 점 위치가 실제 가게 위치와 맞는지 몇 곳 확인
