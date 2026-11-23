window.DESIGN = { kicker: "간판 내력서", list: "ledger", filterStyle: "chips", mapBase: "Base", darkFrom: 3, ramp: ["#ece6d9", "#d4ccbd", "#aaa294", "#7b746a", "#4e4943", "#24221f"], mapOwn: "#e6dcc6", mapOther: "#f1ebdd", mapLine: "#9c9384", mapPin: "#1b1a18", admLine: "#5a4a7a", ink: "#1b1a18", ink2: "#45403a" };
/* 의정부 간판사 — 시안 공통 동작 (외부 스크립트·AI 없음)
   화면 순서: 숫자 타일 → (동네 현황) → 검색 → 조건 → 목록(30곳씩 더 보기) → 상세(dialog)
   시안별 차이는 window.DESIGN 설정(목록 모양·색)과 CSS 뿐입니다. 선택한 시안을 web/ 로 옮깁니다. */
(() => {
  "use strict";
  const CFG = Object.assign({
    list: "cards",            // cards | ledger | gantt
    filterStyle: "chips",     // chips | select
    closed: "#6da7ec", active: "#0ca30c", cmpHi: "#2a78d6", cmpLo: "#b7d3f6",
    grid: "#eef0f3", ink: "#111418", ink2: "#4e5560",
    ramp: ["#e6f0fc", "#b7d3f6", "#86b6ef", "#5598e7", "#2a78d6", "#1c5cab"], // 동네 현황판(연한→진한)
    mapOwn: "#fff7e8", mapOther: "#f1f1ef", mapLine: "#c9c6bf", mapPin: "#1f4e8c",
  }, window.DESIGN || {});

  // ---------- 상수 (rules/*.yaml 과 이름이 같아야 함) ----------
  // 동네 = 법정동 (rules/region.yaml dongs, 지번주소·도로명 괄호와 같은 이름). 행정동은 지도에서만 겹쳐 봄
  const DONGS = ["의정부동", "호원동", "장암동", "신곡동", "용현동", "민락동", "낙양동", "자일동", "금오동", "가능동", "녹양동", "고산동", "산곡동"];
  const TYPES = ["카페", "한식", "치킨", "분식", "주점", "양식", "중식", "일식", "베이커리", "편의점"];
  const RISK = {
    주의: { cls: "risk-bad", icon: "▲", desc: "최근 10년 사이 가게가 자주 바뀐 자리" },
    보통: { cls: "risk-mid", icon: "●", desc: "몇 번 바뀌었지만 평균 수준" },
    양호: { cls: "risk-good", icon: "■", desc: "한 가게가 오래 운영된 편" },
  };
  const SORTS = { closed_desc: "자주 바뀐 순", avg_desc: "오래 버틴 순", vacant_long: "공실 오래된 순", recent: "최근 폐업 순" };
  // 지도 색 — 주의·보통·양호는 모양+색, 이 자리는 보라 핀, 경계선은 법정동 자주 실선 / 행정동 파랑 점선
  const RCOL = { 주의: "#e03131", 보통: "#f08c00", 양호: "#2f9e44" };
  const LINE = { bjd: "#d6336c", adm: "#1c7ed6" };
  const PINC = "#5f3dc4";
  const PAGE = 30;

  // ---------- 상태 ----------
  let DATA = null, shown = PAGE, TODAY = new Date(Date.now() + 9 * 3600e3).toISOString().slice(0, 10);
  // 공실 판단: 인허가 영업 중이 없고, 상가정보(소상공인)에도 가게가 없을 때만 '공실 추정'
  const isVac = (s) => !s.stats.current && !s.stats.occupied_other;
  const otherNow = (s) => (s.now && s.now.length ? `${s.now[0].name}${s.now[0].cat ? " (" + s.now[0].cat + ")" : ""}${s.now.length > 1 ? " 외 " + (s.now.length - 1) + "곳" : ""}` : "");
  const BLANK = { dong: "", type: "", risk: "", vacant: false, sort: "closed_desc", keyword: "" };
  const q = { ...BLANK };

  // ---------- 도우미 ----------
  const $ = (s, el = document) => el.querySelector(s);
  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "style") el.style.cssText = v; // CSP(style-src) 아래에서도 동작
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) {
      if (kid === null || kid === undefined || kid === false) continue;
      el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const norm = (s) => (s || "").replace(/\s+/g, "");
  const dur = (m) => { if (m == null) return "-"; const t = Math.round(m), y = Math.floor(t / 12), r = t % 12; return y ? (r ? `${y}년 ${r}개월` : `${y}년`) : `${r}개월`; };
  const ym = (d) => (d ? d.slice(0, 7).replace("-", ".") : "현재");
  // 화면 표시는 도로명주소 우선, 도로명이 없는 옛 폐업 기록은 지번주소로 대신 표시
  const shortAddr = (s) => (s.road || s.lotno).replace("경기도 의정부시 ", "").replace(/\s*\([^)]*\)$/, "") + (s.road ? "" : " (지번)");
  const badge = (r) => h("span", { class: `badge ${RISK[r].cls}` }, h("span", { "aria-hidden": "true" }, RISK[r].icon), ` ${r}`);
  const set = (patch) => { Object.assign(q, patch); shown = PAGE; draw(); };

  // ---------- 거르기·정렬 ----------
  function results() {
    let list = DATA.sites;
    if (q.keyword) { const k = norm(q.keyword); list = list.filter((s) => norm(s.road + s.lotno + s.key + s.history.map((x) => x.name).join("")).includes(k)); }
    if (q.dong) list = list.filter((s) => s.dong === q.dong);
    if (q.type) list = list.filter((s) => s.history.some((x) => x.type === q.type));
    if (q.risk) list = list.filter((s) => s.risk === q.risk);
    if (q.vacant) list = list.filter(isVac);
    const tAvg = (s) => { const hs = s.history.filter((x) => !q.type || x.type === q.type); return hs.reduce((a, x) => a + x.months, 0) / (hs.length || 1); };
    const lastClose = (s) => s.history.reduce((m, x) => (x.close && x.close > m ? x.close : m), "");
    const S = {
      closed_desc: (a, b) => b.stats.closed - a.stats.closed || (a.stats.avg_months ?? 999) - (b.stats.avg_months ?? 999),
      avg_desc: (a, b) => tAvg(b) - tAvg(a),
      vacant_long: (a, b) => ((a.stats.vacant_since || "9") < (b.stats.vacant_since || "9") ? -1 : 1),
      recent: (a, b) => (lastClose(b) > lastClose(a) ? 1 : -1),
    };
    return list.slice().sort(S[q.sort] || S.closed_desc);
  }

  // ---------- 숫자 타일 ----------
  function renderTiles() {
    const box = $("#tiles"); if (!box) return;
    const s = DATA.sites, yearAgo = String(Number(TODAY.slice(0, 4)) - 1) + TODAY.slice(4);
    const tiles = [
      ["점포 자리", s.length, "곳", { ...BLANK }],
      ["지금 영업 중", s.filter((x) => x.stats.current).length, "곳", { ...BLANK, sort: "avg_desc" }],
      ["공실 추정", s.filter(isVac).length, "곳", { ...BLANK, vacant: true, sort: "vacant_long" }],
      ["주의 자리", s.filter((x) => x.risk === "주의").length, "곳", { ...BLANK, risk: "주의" }],
      ["최근 1년 폐업", s.reduce((n, x) => n + x.history.filter((y) => y.close && y.close >= yearAgo).length, 0), "건", { ...BLANK, sort: "recent" }],
    ];
    box.replaceChildren(...tiles.map(([label, n, unit, patch], i) => h("button", { class: `tile t${i + 1}`, type: "button", onclick: () => { if ($("#qtext")) $("#qtext").value = ""; set(patch); } },
      h("span", { class: "tile-label" }, label), h("span", { class: "tile-num" }, n.toLocaleString(), h("small", {}, unit)))));
  }

  // ---------- 동네 현황판 (#dongs 가 있는 시안만) — 행정동별 정확한 숫자 ----------
  function renderDongs() {
    const box = $("#dongs"); if (!box) return;
    const rows = DONGS.map((d) => {
      const ss = DATA.sites.filter((s) => s.dong === d), closed = ss.flatMap((s) => s.history.filter((x) => x.close));
      return { d, n: ss.length, bad: ss.filter((s) => s.risk === "주의").length, avg: closed.length ? closed.reduce((a, x) => a + x.months, 0) / closed.length : null, vac: ss.filter(isVac).length };
    }).filter((r) => r.n);
    const rates = rows.map((r) => r.bad / r.n), lo = Math.min(...rates), hi = Math.max(...rates);
    const step = (v) => Math.min(CFG.ramp.length - 1, Math.floor(((v - lo) / ((hi - lo) || 1)) * CFG.ramp.length));
    box.replaceChildren(...rows.map((r) => {
      const k = step(r.bad / r.n), dark = k >= (CFG.darkFrom ?? 4), pct = ((r.bad / r.n) * 100).toFixed(1);
      const bar = CFG.dongAscii ? h("span", { class: "dong-bar", "aria-hidden": "true" }, "█".repeat(Math.round((r.bad / r.n) * 20)) + "░".repeat(20 - Math.round((r.bad / r.n) * 20))) : null;
      return h("button", { type: "button", class: "dong", "aria-pressed": String(q.dong === r.d), "aria-label": `${r.d}: 주의 자리 ${r.bad}곳, 전체 ${r.n}곳 중 ${pct}%`,
        style: CFG.dongAscii ? "" : `background:${CFG.ramp[k]};color:${dark ? "#fff" : CFG.ink}`, onclick: () => set({ dong: q.dong === r.d ? "" : r.d }) },
        h("span", { class: "dong-name" }, r.d),
        h("span", { class: "dong-rate" }, `${pct}%`), bar,
        h("span", { class: "dong-meta" }, `주의 ${r.bad}곳 / 전체 ${r.n}곳`),
        h("span", { class: "dong-meta" }, `폐업 평균 ${r.avg == null ? "-" : Math.round(r.avg) + "개월"}`), h("span", { class: "dong-meta" }, `공실 ${r.vac}곳`));
    }));
  }

  // ---------- 검색 (주소·번지·상호) ----------
  function renderSearch() {
    const box = $("#search"); if (!box) return;
    let t;
    const input = h("input", { id: "qtext", type: "search", placeholder: "주소·번지·상호를 입력하세요  예) 시민로 120, 민락동 800", "aria-label": "주소, 번지 또는 상호", autocomplete: "off",
      oninput: () => { clearTimeout(t); t = setTimeout(() => set({ keyword: input.value.trim() }), 200); } });
    const form = h("form", { class: "search-form", role: "search", onsubmit: (e) => { e.preventDefault(); set({ keyword: input.value.trim() }); const r = results(); if (r.length === 1) openDetail(r[0]); } },
      h("span", { class: "search-icon", "aria-hidden": "true" }, "⌕"), input, h("button", { class: "search-btn" }, "찾기"));
    box.replaceChildren(form);
  }

  // ---------- 조건 ----------
  function chipRow(title, values, cur, key) {
    return h("div", { class: "f-row" }, h("span", { class: "f-title" }, title),
      h("div", { class: "f-chips", role: "group", "aria-label": title },
        [["", "전체"], ...values.map((v) => [v, v])].map(([v, l]) => h("button", { type: "button", class: "f-chip", "aria-pressed": String(cur === v), onclick: () => set({ [key]: v }) }, l))));
  }
  function renderFilters() {
    const box = $("#filters"); if (!box) return;
    if (CFG.filterStyle === "select") {
      const sel = (label, values, key) => h("label", { class: "f-sel" }, h("span", {}, label),
        h("select", { onchange: (e) => set({ [key]: e.target.value }) }, h("option", { value: "" }, "전체"), values.map((v) => h("option", { value: v, selected: q[key] === v }, v))));
      box.replaceChildren(sel("동", DONGS, "dong"), sel("업종", TYPES, "type"), sel("주의도", Object.keys(RISK), "risk"),
        h("label", { class: "f-sel" }, h("span", {}, "정렬"), h("select", { onchange: (e) => set({ sort: e.target.value }) }, Object.entries(SORTS).map(([k, v]) => h("option", { value: k, selected: q.sort === k }, v)))),
        h("label", { class: "f-check" }, h("input", { type: "checkbox", checked: q.vacant, onchange: (e) => set({ vacant: e.target.checked }) }), "공실만"),
        h("button", { type: "button", class: "f-reset", onclick: () => { if ($("#qtext")) $("#qtext").value = ""; set({ ...BLANK }); } }, "조건 지우기"));
      return;
    }
    const blank = Object.keys(BLANK).every((k) => q[k] === BLANK[k]);
    box.replaceChildren(...[
      h("div", { class: "f-top" }, h("span", { class: "f-now" }, blank ? "조건 없음 · 전체 자리" : "적용 중: " + condText()),
        h("button", { type: "button", class: "f-reset-btn", disabled: blank, title: "동네·업종·주의도·정렬·검색어를 처음 상태로",
          onclick: () => { if ($("#qtext")) $("#qtext").value = ""; set({ ...BLANK }); } }, h("span", { "aria-hidden": "true" }, "↺ "), "조건 초기화")),
      CFG.hideDongChips ? null : chipRow("동네", DONGS, q.dong, "dong"),
      chipRow("업종", TYPES, q.type, "type"),
      chipRow("주의도", Object.keys(RISK), q.risk, "risk"),
      riskHelp(),
      h("div", { class: "f-row" }, h("span", { class: "f-title" }, "정렬"), h("div", { class: "f-chips" },
        Object.entries(SORTS).map(([k, v]) => h("button", { type: "button", class: "f-chip", "aria-pressed": String(q.sort === k), onclick: () => set({ sort: k }) }, v)),
        h("button", { type: "button", class: "f-chip", "aria-pressed": String(q.vacant), onclick: () => set({ vacant: !q.vacant }) }, "공실만")))].filter(Boolean));
  }

  const condText = () => [q.keyword && `“${q.keyword}”`, q.dong, q.type, q.risk && `주의도 ${q.risk}`, q.vacant && "공실만", SORTS[q.sort]].filter(Boolean).join(" · ");

  // 주의도 기준 — rules/risk.yaml 값을 sites.json 으로 받아 그대로 문장으로 (규칙을 바꾸면 설명도 함께 바뀜)
  function riskRules() {
    const R = (DATA && DATA.risk_rules) || { years: 10, recent_days: 730, 주의: { closed_at_least: 4, closed_2_and_avg_under: 18, recent_closed_at_least: 2 }, 보통: { closed_at_least: 2, avg_under: 24 } };
    const ry = Math.round(R.recent_days / 365);
    return {
      R, ry, lines: [
        ["주의", `최근 ${R.years}년 안에 폐업 ${R.주의.closed_at_least}번 이상 · 또는 폐업 2번 이상이면서 평균 영업기간 ${dur(R.주의.closed_2_and_avg_under)} 미만 · 또는 최근 ${ry}년 안에 폐업 ${R.주의.recent_closed_at_least}번 이상`],
        ["보통", `주의에는 해당하지 않지만 최근 ${R.years}년 안에 폐업 ${R.보통.closed_at_least}번 이상 · 또는 폐업 가게 평균 영업기간 ${dur(R.보통.avg_under)} 미만`],
        ["양호", `그 밖의 자리 — 최근 ${R.years}년 폐업이 거의 없거나, 문을 닫은 가게도 오래 운영됨`],
      ],
    };
  }
  function riskHelp() {
    const { lines } = riskRules();
    return h("div", { class: "risk-help", role: "note", "aria-label": "주의도 기준" },
      h("p", { class: "risk-help-title" }, "주의도는 이렇게 나눕니다 ", h("small", {}, "(인허가 개업·폐업 기록만으로 계산한 참고 지표)")),
      lines.map(([r, t]) => h("p", { class: "risk-help-line" }, badge(r), h("span", {}, t))));
  }
  function riskWhy(s) {
    const { R, ry } = riskRules();
    const cut = `${+TODAY.slice(0, 4) - R.years}${TODAY.slice(4, 7)}`;
    const closed = s.history.filter((x) => x.close && x.close.slice(0, 7) >= cut);
    const avg = closed.length ? closed.reduce((a, x) => a + x.months, 0) / closed.length : null;
    return `이 자리: 최근 ${R.years}년 폐업 ${closed.length}번 · 폐업 가게 평균 영업 ${avg == null ? "-" : dur(avg)} · 최근 ${ry}년 폐업 ${s.stats.recent_closed_2y}번`;
  }

  // ---------- 목록 ----------
  const strip = (s) => h("div", { class: "strip", "aria-hidden": "true" }, s.history.map((x) => h("span", { style: `flex:${Math.max(x.months, 2)};background:${x.close ? CFG.closed : CFG.active}` })));
  const open = (s) => ({ tabindex: "0", onclick: () => openDetail(s), onkeydown: (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), openDetail(s)) });
  const nowText = (s) => (s.stats.current ? `${s.stats.current} (${s.stats.current_type})` : s.stats.occupied_other ? `${otherNow(s)} · 상가정보` : `공실 추정 · ${ym(s.stats.vacant_since)}부터`);

  function itemCard(s) {
    const st = s.stats;
    return h("article", { class: "item", ...open(s) },
      h("div", { class: "item-head" }, h("h3", { class: "item-addr" }, shortAddr(s)), badge(s.risk)),
      h("p", { class: "item-meta" }, `${s.dong} · 가게 ${st.count}곳 거쳐 감 · 폐업 평균 ${dur(st.avg_months)}`),
      h("p", { class: "item-now" }, `지금: ${nowText(s)}`), strip(s));
  }
  function itemLedger(s, i) {
    const st = s.stats;
    return h("article", { class: "row", ...open(s) },
      h("span", { class: "row-no" }, String(i + 1).padStart(2, "0")),
      h("div", { class: "row-addr" }, h("h3", {}, shortAddr(s)), h("p", {}, `지번 ${s.lotno.replace("경기도 의정부시 ", "")}`)),
      h("div", { class: "row-num" }, h("b", {}, `${st.count}곳`), h("span", {}, "거쳐 간 가게")),
      h("div", { class: "row-num" }, h("b", {}, dur(st.avg_months)), h("span", {}, "폐업 가게 평균")),
      h("div", { class: "row-now" }, h("span", {}, "지금"), h("b", {}, st.current ? st.current : st.occupied_other ? s.now[0].name : "공실 추정")),
      h("div", { class: "row-risk" }, badge(s.risk)));
  }
  let G0 = 2009;
  function itemGantt(s) {
    const y1 = +TODAY.slice(0, 4) + 1, W = 100;
    const x = (d) => { const [Y, M] = d.split("-").map(Number); return ((Y + (M - 1) / 12 - G0) / (y1 - G0)) * W; };
    const bars = s.history.map((r) => h("span", { class: `g-bar ${r.close ? "" : "on"}`, title: `${r.name} (${r.type}) ${ym(r.open)}~${r.close ? ym(r.close) : "영업 중"}`,
      style: `left:${x(r.open)}%;width:${Math.max(x(r.close || TODAY) - x(r.open), 0.6)}%;background:${r.close ? CFG.closed : CFG.active}` }));
    return h("article", { class: "g-row", ...open(s) },
      h("div", { class: "g-addr" }, h("h3", {}, shortAddr(s)), h("p", {}, `${s.dong} · ${s.stats.count}곳 · `, badge(s.risk))),
      h("div", { class: "g-track" }, bars), h("div", { class: "g-now" }, s.stats.current ? s.stats.current_type : s.stats.occupied_other ? "다른 업종" : "공실"));
  }
  function ganttHead() {
    const y1 = +TODAY.slice(0, 4) + 1, ticks = [];
    for (let y = G0 + 1; y <= y1; y += 2) ticks.push(h("span", { style: `left:${((y - G0) / (y1 - G0)) * 100}%` }, String(y)));
    return h("div", { class: "g-head", "aria-hidden": "true" }, h("div", {}), h("div", { class: "g-axis" }, ticks), h("div", { class: "g-now-h" }, "지금"));
  }

  function renderList() {
    const all = results(), box = $("#list");
    const c = $("#count"); if (c) c.textContent = `${all.length.toLocaleString()}곳`;
    const cond = $("#cond"); if (cond) cond.textContent = condText();
    if (!all.length) { box.replaceChildren(h("p", { class: "empty" }, "조건에 맞는 자리가 없어요. 조건을 줄이거나 지워 보세요.")); return; }
    const page = all.slice(0, shown);
    const items = CFG.list === "ledger" ? page.map(itemLedger) : CFG.list === "gantt" ? [ganttHead(), ...page.map(itemGantt)] : page.map(itemCard);
    box.replaceChildren(...items);
    if (all.length > shown) box.append(h("button", { class: "more", type: "button", onclick: () => { shown += PAGE; renderList(); } }, `30곳 더 보기 (${Math.min(shown, all.length)}/${all.length})`));
  }

  // ---------- 상세 ----------
  const tip = () => $("#tip") || document.body.appendChild(h("div", { id: "tip", class: "tip", role: "tooltip" }));
  function showTip(e, html) { const t = tip(); t.innerHTML = html; t.style.opacity = 1; t.style.left = Math.min(e.clientX + 14, innerWidth - 270) + "px"; t.style.top = e.clientY + 14 + "px"; }
  const hideTip = () => { tip().style.opacity = 0; };
  function areaAvg(dong, type) {
    const a = DATA.area_stats.find((x) => x.dong === dong && x.type === type), c = DATA.area_stats.find((x) => x.dong === "전체" && x.type === type);
    return { dong: a?.avg_months ?? null, n: a?.n ?? 0, city: c?.avg_months ?? null, cn: c?.n ?? 0 };
  }
  function summary(s) {
    const st = s.stats;
    return `이 자리에는 ${s.history[0].open.slice(0, 4)}년부터 가게 ${st.count}곳이 거쳐 갔습니다. ` +
      (st.closed ? `문을 닫은 ${st.closed}곳의 평균 영업기간은 ${dur(st.avg_months)}입니다. ` : "") +
      (st.current ? `지금은 '${st.current}'(${st.current_type})이(가) 영업 중입니다.` : st.occupied_other ? `음식점 인허가는 ${ym(st.vacant_since)} 이후 없지만, 상가정보 기준 지금은 '${otherNow(s)}'이(가) 있습니다${s.now_match === "건물" ? "(같은 건물 기준)" : ""}.` : `${ym(st.vacant_since)} 이후 영업 기록이 없습니다(공실 추정).`);
  }
  const mo = (m) => (m == null ? "-" : `${Math.round(m)}개월` + (m >= 12 ? ` (${dur(Math.round(m))})` : ""));
  const diff = (a, b) => { if (a == null || b == null) return "-"; const d = Math.round(a - b); return d === 0 ? "같음" : d > 0 ? `${d}개월 길다` : `${-d}개월 짧다`; };

  // 키가 없을 때의 대체 그림: 같은 법정동 자리들이 모인 범위 + 행정동 경계(점선)
  function mapSVG(s) {
    const areas = DATA.areas || [];
    const pts = DATA.sites.filter((o) => o.dong === s.dong && o.lat).map((o) => [o.lng, o.lat]);
    if (s.lat) pts.push([s.lng, s.lat]);
    if (!pts.length) return `<p class="muted">좌표 기록이 없어 지도를 그릴 수 없습니다.</p>`;
    let [x0, x1, y0, y1] = [Math.min(...pts.map((p) => p[0])), Math.max(...pts.map((p) => p[0])), Math.min(...pts.map((p) => p[1])), Math.max(...pts.map((p) => p[1]))];
    const padX = Math.max((x1 - x0) * 0.2, 0.004), padY = Math.max((y1 - y0) * 0.2, 0.003); x0 -= padX; x1 += padX; y0 -= padY; y1 += padY;
    const k = Math.cos(((y0 + y1) / 2) * Math.PI / 180), W = 760, H = Math.max(260, Math.min(480, Math.round(W * (y1 - y0) / ((x1 - x0) * k))));
    const sc = Math.min((W / (x1 - x0)) * k, H / (y1 - y0)) / k, ox = (W - (x1 - x0) * sc * k) / 2, oy = (H - (y1 - y0) * sc) / 2;
    const P = (lng, lat) => [ox + (lng - x0) * sc * k, oy + (y1 - lat) * sc];
    const rings = (g) => (g.type === "MultiPolygon" ? g.coordinates.map((p) => p[0]) : [g.coordinates[0]]);
    const path = (g) => (g.type === "MultiPolygon" ? g.coordinates : [g.coordinates]).map((poly) => poly.map((r) => "M" + r.map((c) => P(c[0], c[1]).map((v) => v.toFixed(1)).join(",")).join("L") + "Z").join("")).join("");
    let g = "";
    for (const a of areas) g += `<path d="${path(a.geometry)}" fill="${CFG.mapOther}" stroke="${LINE.adm}" stroke-width="2" stroke-dasharray="7 5" fill-rule="evenodd"/>`;
    for (const a of areas) {
      const ps = rings(a.geometry).flat(), c = P(ps.reduce((t, p) => t + p[0], 0) / ps.length, ps.reduce((t, p) => t + p[1], 0) / ps.length);
      if (c[0] > 20 && c[0] < W - 20 && c[1] > 14 && c[1] < H - 8) g += `<text x="${c[0]}" y="${c[1]}" class="map-dong" text-anchor="middle">${a.name}</text>`;
    }
    const col = RCOL;
    const tag = { 주의: "path", 보통: "circle", 양호: "rect" };
    const mark = (r, x, y, rad) => r === "주의" ? `<path d="M${x} ${y - rad - 1}L${x + rad + 1} ${y + rad}L${x - rad - 1} ${y + rad}Z"` : r === "양호" ? `<rect x="${x - rad}" y="${y - rad}" width="${2 * rad}" height="${2 * rad}" rx="1"` : `<circle cx="${x}" cy="${y}" r="${rad}"`;
    for (const o of DATA.sites) {
      if (o.id === s.id || !o.lat || o.dong !== s.dong) continue;
      const [x, y] = P(o.lng, o.lat);
      g += `${mark(o.risk, x, y, 3.5)} fill="${col[o.risk]}" fill-opacity=".8" stroke="#fff" stroke-width="1"><title>${esc(shortAddr(o))} · ${o.risk}</title></${tag[o.risk]}>`;
    }
    if (s.lat) {
      const [x, y] = P(s.lng, s.lat);
      g += `<circle cx="${x}" cy="${y}" r="16" fill="${PINC}" fill-opacity=".2"/><circle cx="${x}" cy="${y}" r="8" fill="${PINC}" stroke="#fff" stroke-width="3"/><text x="${x + 12}" y="${y - 10}" class="map-pin">이 자리</text>`;
    }
    return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(s.dong)} 자리 위치 (점선은 행정동 경계)">${g}</svg>`;
  }

  // 브이월드 지도 (공공데이터포털: 국토교통부 WMTS 배경지도 · 행정구역도 · GIS건물통합정보 · 연속지적도). 인증키는 web/config.js
  let VMAP = null;
  const VPREF = { base: "Base", bnd: "both", bld: false, jijuk: false }; // 기본 = 일반지도. 선택은 다음 자리를 열어도 유지
  // 다각형 무게중심 (가장 큰 고리 기준) — 동 이름 놓을 자리
  function centroid(g) {
    const polys = g.type === "MultiPolygon" ? g.coordinates : [g.coordinates];
    let best = null, bestA = 0;
    for (const poly of polys) {
      const r = poly[0]; let a = 0, cx = 0, cy = 0;
      for (let i = 0, j = r.length - 1; i < r.length; j = i++) { const f = r[j][0] * r[i][1] - r[i][0] * r[j][1]; a += f; cx += (r[j][0] + r[i][0]) * f; cy += (r[j][1] + r[i][1]) * f; }
      if (Math.abs(a) > bestA) { bestA = Math.abs(a); best = [cy / (3 * a), cx / (3 * a)]; }
    }
    return best;
  }
  const riskIcon = (r) => {
    const L = window.L;
    const svg = r === "주의" ? `<svg width="20" height="18" viewBox="0 0 20 18"><path d="M10 1 L19 17 L1 17 Z" fill="${RCOL.주의}" stroke="#fff" stroke-width="1.6"/></svg>`
      : r === "보통" ? `<svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="5.6" fill="${RCOL.보통}" stroke="#fff" stroke-width="1.6"/></svg>`
      : `<svg width="10" height="10" viewBox="0 0 10 10"><rect x="1" y="1" width="8" height="8" fill="${RCOL.양호}" fill-opacity=".8" stroke="#fff" stroke-width="1"/></svg>`;
    const sz = r === "주의" ? [20, 18] : r === "보통" ? [14, 14] : [10, 10];
    return L.divIcon({ className: "v-mk", html: svg, iconSize: sz, iconAnchor: [sz[0] / 2, sz[1] / 2] });
  };
  const pinIcon = () => window.L.divIcon({ className: "v-pin2", iconSize: [34, 46], iconAnchor: [17, 46],
    html: `<span class="v-pin-label">이 자리</span><svg width="34" height="46" viewBox="0 0 34 46"><path d="M17 45 C17 45 2 27 2 16 A15 15 0 1 1 32 16 C32 27 17 45 17 45 Z" fill="${PINC}" stroke="#fff" stroke-width="3"/><circle cx="17" cy="16" r="6" fill="#fff"/></svg>` });
  const label = (latlng, text, kind) => window.L.marker(latlng, { interactive: false, keyboard: false,
    icon: window.L.divIcon({ className: `v-lbl ${kind}`, html: `<span>${esc(text)}</span>`, iconSize: [0, 0] }) });
  function vmap(s, dlg) {
    if (VMAP) { VMAP.remove(); VMAP = null; }
    const L = window.L, el = dlg.querySelector("#vmap"), KEY = encodeURIComponent(window.VWORLD_KEY), DOMAIN = location.origin;
    const m = L.map(el, { minZoom: 7, maxZoom: 19, scrollWheelZoom: false });
    m.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
    const area = (DATA.areas || []).filter(Boolean);
    const sameDong = DATA.sites.filter((o) => o.dong === s.dong && o.lat);
    if (s.lat) m.setView([s.lat, s.lng], 16);
    else if (sameDong.length) m.fitBounds(L.latLngBounds(sameDong.map((o) => [o.lat, o.lng])), { padding: [20, 20] });
    else m.setView([37.738, 127.047], 13);

    // 배경지도 (WMTS)
    const BASES = { Base: ["png", "일반지도"], Satellite: ["jpeg", "위성사진"] };
    if (!BASES[VPREF.base]) VPREF.base = "Base";
    const baseLayer = (k) => L.tileLayer(`https://api.vworld.kr/req/wmts/1.0.0/${KEY}/${k}/{z}/{y}/{x}.${BASES[k][0]}`, { maxZoom: 19, attribution: "배경지도 © 국토교통부 브이월드" });
    let base = baseLayer(VPREF.base).addTo(m);
    // 겹쳐 보기 (WMS) — 브이월드 2D 데이터·국가중점데이터
    const wms = (url, layer, extra = {}) => L.tileLayer.wms(url, Object.assign({ layers: layer, styles: layer, format: "image/png", transparent: true, version: "1.3.0", key: window.VWORLD_KEY, domain: DOMAIN, maxZoom: 19 }, extra));
    // 경계선 = 흰 테두리 위에 색 선 (어느 배경에서도 잘 보이게) + 동 이름
    const lines = (feats, color, weight, dash) => [
      L.geoJSON(feats, { style: { color: "#fff", weight: weight + 4, opacity: 0.85, fill: false }, interactive: false }),
      L.geoJSON(feats, { style: { color, weight, dashArray: dash, opacity: 1, fill: false }, interactive: false })];
    const fc = (arr) => ({ type: "FeatureCollection", features: arr.map((a) => ({ type: "Feature", properties: { name: a.name }, geometry: a.geometry })) });
    const bjdData = DATA.bjd || [];
    const bjdLabels = bjdData.length ? bjdData.map((a) => [centroid(a.geometry), a.name])
      : DONGS.map((d) => { const ps = DATA.sites.filter((o) => o.dong === d && o.lat); return ps.length ? [[ps.reduce((t, o) => t + o.lat, 0) / ps.length, ps.reduce((t, o) => t + o.lng, 0) / ps.length], d] : null; }).filter(Boolean);
    const LAYERS = {
      // 법정동: 브이월드 선 데이터(수집 때 받아 둠)가 있으면 색 선, 없으면 브이월드 경계 그림(WMS)
      bjd: L.layerGroup([...(bjdData.length ? lines(fc(bjdData), LINE.bjd, 3.5)
        : [wms("https://api.vworld.kr/req/wms", "lt_c_ademd", { attribution: "법정동 경계 © 국토교통부 행정구역도" })]),
        ...bjdLabels.filter((x) => x[0]).map(([c, n]) => label(c, n, "bjd"))]),
      adm: L.layerGroup([...lines(fc(area), LINE.adm, 2.5, "8 6"), ...area.map((a) => [centroid(a.geometry), a.name]).filter((x) => x[0]).map(([c, n]) => label(c, n, "adm"))]),
      bld: wms("https://api.vworld.kr/ned/wms/BldgisSpceService", "dt_d010", { styles: "", minZoom: 15, attribution: "건물 © 국토교통부 GIS건물통합정보" }),
      jijuk: wms("https://api.vworld.kr/req/wms", "lp_pa_cbnd_bubun", { minZoom: 16, attribution: "필지 © 국토교통부 연속지적도" }),
    };
    const applyBnd = () => {
      for (const k of ["bjd", "adm"]) m.removeLayer(LAYERS[k]);
      if (VPREF.bnd === "bjd" || VPREF.bnd === "both") LAYERS.bjd.addTo(m);
      if (VPREF.bnd === "adm" || VPREF.bnd === "both") LAYERS.adm.addTo(m);
    };
    const applyOverlay = (k) => (VPREF[k] ? LAYERS[k].addTo(m) : m.removeLayer(LAYERS[k]));
    applyBnd(); applyOverlay("bld"); applyOverlay("jijuk");

    // 자리 점 — 주의 ▲빨강(크게) · 보통 ●주황 · 양호 ■초록(작게). 주의가 위에 오도록 그리는 순서·높이 조정
    const marks = L.layerGroup().addTo(m);
    const zi = { 양호: 0, 보통: 200, 주의: 400 };
    for (const r of ["양호", "보통", "주의"]) for (const o of sameDong) {
      if (o.id === s.id || o.risk !== r) continue;
      L.marker([o.lat, o.lng], { icon: riskIcon(r), zIndexOffset: zi[r], keyboard: false })
        .bindTooltip(`${esc(shortAddr(o))} · ${RISK[o.risk].icon} ${o.risk} · 가게 ${o.stats.count}곳`).on("click", () => openDetail(o)).addTo(marks);
    }
    if (s.lat) L.marker([s.lat, s.lng], { icon: pinIcon(), zIndexOffset: 1000, keyboard: false, title: "이 자리" }).addTo(marks);

    // 선택 박스
    const bar = dlg.querySelector(".v-ctrl");
    bar.querySelector(".v-base").value = VPREF.base;
    bar.querySelector(".v-bnd").value = VPREF.bnd;
    bar.querySelector(".v-bld").checked = VPREF.bld;
    bar.querySelector(".v-jijuk").checked = VPREF.jijuk;
    bar.querySelector(".v-base").addEventListener("change", (e) => { VPREF.base = e.target.value; m.removeLayer(base); base = baseLayer(VPREF.base).addTo(m); base.bringToBack(); });
    bar.querySelector(".v-bnd").addEventListener("change", (e) => { VPREF.bnd = e.target.value; applyBnd(); });
    bar.querySelector(".v-bld").addEventListener("change", (e) => { VPREF.bld = e.target.checked; applyOverlay("bld"); if (VPREF.bld && m.getZoom() < 15) m.setZoom(16); });
    bar.querySelector(".v-jijuk").addEventListener("change", (e) => { VPREF.jijuk = e.target.checked; applyOverlay("jijuk"); if (VPREF.jijuk && m.getZoom() < 16) m.setZoom(17); });
    const fit = dlg.querySelector(".v-fit"), here = dlg.querySelector(".v-here");
    if (fit && sameDong.length) fit.addEventListener("click", () => m.fitBounds(L.latLngBounds(sameDong.map((o) => [o.lat, o.lng])), { padding: [20, 20] }));
    if (here) here.addEventListener("click", () => s.lat && m.setView([s.lat, s.lng], 17));
    setTimeout(() => m.invalidateSize(), 60);
    VMAP = m;
    dlg.addEventListener("close", () => { if (VMAP === m) { m.remove(); VMAP = null; } }, { once: true });
  }

  function openDetail(s) {
    const dlg = $("#detail"), st = s.stats;
    const mainType = st.current_type || s.history[s.history.length - 1].type;
    const own = s.history.filter((x) => x.type === mainType && x.close), av = areaAvg(s.dong, mainType);
    const ownAvg = own.length ? own.reduce((a, x) => a + x.months, 0) / own.length : null;
    const q2 = encodeURIComponent((s.road || s.lotno).replace(/\s*\([^)]*\)$/, "").replace(/,.*$/, ""));
    const sameDong = DATA.sites.filter((o) => o.dong === s.dong), badN = sameDong.filter((o) => o.risk === "주의").length;
    const useV = !!(window.VWORLD_KEY && window.L); // 브이월드 키와 Leaflet 이 있으면 실제 배경지도
    const ext = `<a class="v-ext naver" href="https://map.naver.com/p/search/${q2}" target="_blank" rel="noopener">네이버지도 ↗</a><a class="v-ext kakao" href="https://map.kakao.com/?q=${q2}" target="_blank" rel="noopener">카카오맵 ↗</a>`;
    dlg.innerHTML = `
      <div class="d-head"><div><p class="d-kicker">${CFG.kicker || "자리 이력서"}</p><h2 id="d-title">${esc(shortAddr(s))}</h2>
        <p class="muted">지번 ${esc(s.lotno.replace("경기도 의정부시 ", ""))}${s.unit ? "" : " · 건물 단위로 묶음"}</p></div>
        <button class="d-close" type="button" aria-label="닫기">✕</button></div>
      <div class="d-risk"></div>
      <p class="d-sum">${esc(summary(s))}</p>
      <div class="d-tiles">
        <div><span>거쳐 간 가게</span><b>${st.count}곳</b><small>폐업 ${st.closed}곳 · 영업 중 ${st.count - st.closed}곳</small></div>
        <div><span>폐업 가게 평균 영업기간</span><b>${st.avg_months == null ? "-" : Math.round(st.avg_months) + "개월"}</b><small>${st.avg_months == null ? "폐업 기록 없음" : (st.avg_months >= 12 ? dur(st.avg_months) + " · " : "") + "폐업 " + st.closed + "곳 기준"}</small></div>
        <div><span>최근 2년 폐업</span><b>${st.recent_closed_2y}곳</b><small>${st.current ? "지금: " + esc(st.current) : st.occupied_other ? "지금: " + esc(otherNow(s)) : "지금: 공실 추정 (" + ym(st.vacant_since) + "부터)"}</small></div>
      </div>
      <h3>위치</h3>
      ${useV ? `<div class="v-ctrl" role="group" aria-label="지도 보기 선택">
        <label>배경 <select class="v-base"><option value="Base">일반지도</option><option value="Satellite">위성사진</option></select></label>
        <label>경계선 <select class="v-bnd"><option value="both">법정동 + 행정동</option><option value="bjd">법정동</option><option value="adm">행정동</option><option value="none">없음</option></select></label>
        <label><input type="checkbox" class="v-bld"> 건물</label>
        <label><input type="checkbox" class="v-jijuk"> 필지</label>
        <span class="v-btns"><button type="button" class="v-fit">동네 전체</button><button type="button" class="v-here">이 자리로</button>${ext}</span></div>` : `<div class="v-ctrl"><span class="v-btns">${ext}</span></div>`}
      <div class="d-map">${useV ? '<div id="vmap" class="vmap" role="region" aria-label="브이월드 배경지도"></div>' : mapSVG(s)}</div>
      <p class="map-legend"><span class="lg-pin" aria-hidden="true"></span><b>이 자리</b> &nbsp; <span class="lg-bad" aria-hidden="true"></span>주의 &nbsp; <span class="lg-mid" aria-hidden="true"></span>보통 &nbsp; <span class="lg-good" aria-hidden="true"></span>양호 — 같은 법정동(${esc(s.dong)})의 다른 자리 (주의 ${badN}곳 / ${sameDong.length}곳)</p>
      <p class="map-legend"><span class="ln bjd" aria-hidden="true"></span>법정동 경계·이름(자주색 실선) &nbsp; <span class="ln adm" aria-hidden="true"></span>행정동 경계·이름(파란 점선)${useV ? " &nbsp; · 건물·필지는 가까이 확대하면 보임" : ""}</p>
      ${s.lat ? "" : `<p class="muted">이 자리는 좌표 기록이 없어 점을 찍지 못했습니다.</p>`}

      <h3>업종 변천사 <small class="muted">${s.history.length}곳 · 오래된 순</small></h3>
      <div class="table-wrap"><table class="d-table"><thead><tr><th>순번</th><th>상호</th><th>업종</th><th>개업</th><th>폐업</th><th class="num">영업기간</th></tr></thead><tbody>
        ${s.history.map((x, i) => `<tr${x.close ? "" : ' class="on"'}><td>${i + 1}</td><td>${esc(x.name)}</td><td>${x.type}</td><td>${x.open.replaceAll("-", ".")}</td><td>${x.close ? x.close.replaceAll("-", ".") : "영업 중"}</td><td class="num">${x.months}개월</td></tr>`).join("")}
      </tbody></table></div>
      <h3>${mainType} 평균 영업기간 비교 <small class="muted">폐업한 가게 기준</small></h3>
      <div class="table-wrap"><table class="d-table"><thead><tr><th>구분</th><th class="num">평균 영업기간</th><th class="num">표본</th><th>이 자리와 비교</th></tr></thead><tbody>
        <tr class="on"><td>이 자리</td><td class="num">${mo(ownAvg)}</td><td class="num">${own.length}곳</td><td>-</td></tr>
        <tr><td>${esc(s.dong)} 평균</td><td class="num">${mo(av.dong)}</td><td class="num">${av.n}곳</td><td>${ownAvg == null ? "-" : "이 자리가 " + diff(ownAvg, av.dong)}</td></tr>
        <tr><td>의정부시 평균</td><td class="num">${mo(av.city)}</td><td class="num">${av.cn}곳</td><td>${ownAvg == null ? "-" : "이 자리가 " + diff(ownAvg, av.city)}</td></tr>
      </tbody></table></div>
      <p class="d-note">영업기간은 인허가일부터 폐업일(영업 중이면 기준일 ${TODAY.replaceAll("-", ".")})까지의 개월 수입니다. 주의도는 인허가 기록만으로 계산한 참고 지표로 매출·임대료·유동인구는 반영되지 않습니다. 지도: 배경·법정동 경계·건물·필지는 국토교통부 브이월드, 행정동 경계는 통계청 SGIS(가공 vuski/admdongkor, CC BY 4.0).</p>`;
    dlg.querySelector(".d-risk").append(badge(s.risk), h("span", { class: "muted" }, ` ${RISK[s.risk].desc}`),
      h("p", { class: "risk-why" }, riskWhy(s)),
      h("details", { class: "risk-rules" }, h("summary", {}, "주의도 기준 보기"), riskRules().lines.map(([r, t]) => h("p", { class: "risk-help-line" }, badge(r), h("span", {}, t)))));
    dlg.querySelector(".d-close").addEventListener("click", () => dlg.close());
    if (!dlg.open) dlg.showModal ? dlg.showModal() : dlg.setAttribute("open", "");
    dlg.scrollTop = 0;
    if (useV) vmap(s, dlg);
  }

  // ---------- 전체 ----------
  function draw() { renderDongs(); renderFilters(); renderList(); }
  async function load() {
    if (window.EMBEDDED_DATA) return window.EMBEDDED_DATA;
    return (await fetch("data/sites.json", { cache: "no-cache" })).json();
  }
  load().then((d) => {
    DATA = d; TODAY = d.meta.generated || TODAY;
    G0 = Math.max(2000, Math.min(...d.sites.map((s) => +s.history[0].open.slice(0, 4))));
    const u = $("#updated"); if (u) u.textContent = d.meta.source.startsWith("샘플") ? "샘플(가상) 데이터 · 시안 확인용" : `업데이트 ${d.updated_at.slice(0, 16).replace("T", " ")}`;
    const f = $("#source-note"); if (f) f.textContent = `자료: ${d.meta.source} · 점포 자리 ${d.meta.site_count.toLocaleString()}곳 · 인허가 기록 ${d.meta.record_count.toLocaleString()}건 · ${d.meta.note} 행정동 경계: 통계청 SGIS(공공누리 제1유형), 가공 vuski/admdongkor(CC BY 4.0).`;
    renderTiles(); renderSearch(); draw();
  }).catch(() => { $("#list").replaceChildren(h("p", { class: "empty" }, "자료를 불러오지 못했어요. 잠시 뒤 다시 열어 주세요.")); });
})();
