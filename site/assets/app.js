/* 라이징쇼츠 화면 스크립트: data/*.json 을 읽어 각 화면을 그린다 */
(() => {
'use strict';
const $ = (s, el = document) => el.querySelector(s);
const params = new URLSearchParams(location.search);
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

/* ---------- 숫자·글자 표시 ---------- */
function trim1(n) { const s = n.toFixed(1); return s.endsWith('.0') ? s.slice(0, -2) : s; }
function kn(n) {
  if (n == null || isNaN(n)) return '-';
  const a = Math.abs(n);
  if (a >= 1e8) return trim1(n / 1e8) + '억';
  if (a >= 1e5) return Math.round(n / 1e4).toLocaleString('ko-KR') + '만';
  if (a >= 1e4) return trim1(n / 1e4) + '만';
  if (a >= 1e3) return trim1(n / 1e3) + '천';
  return String(Math.round(n));
}
function ratioText(r) {
  if (r == null) return null;
  if (r >= 10) return Math.round(r).toLocaleString('ko-KR') + '배';
  return trim1(r) + '배';
}
function ago(h) {
  if (h == null) return '';
  if (h < 1) return '방금';
  if (h < 24) return Math.floor(h) + '시간 전';
  return Math.floor(h / 24) + '일 전';
}
function dur(s) { if (!s && s !== 0) return ''; return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0'); }
function title(t) {
  const c = String(t || '').replace(/#[^\s#]+/g, ' ').replace(/\s+/g, ' ').trim();
  return c || String(t || '');
}
function kst(iso) {
  const d = new Date(iso);
  if (isNaN(d)) return '';
  const f = new Intl.DateTimeFormat('ko-KR', { timeZone: 'Asia/Seoul', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: false });
  return f.format(d);
}
const kstHour = (epochHours) => (Math.floor(epochHours + 9) % 24 + 24) % 24;

/* ---------- 썸네일 ---------- */
function thumb(id, alt) {
  const vert = `https://i.ytimg.com/vi/${encodeURIComponent(id)}/oar2.jpg`;
  const hq = `https://i.ytimg.com/vi/${encodeURIComponent(id)}/hqdefault.jpg`;
  return `<img src="${vert}" data-fb="${hq}" alt="${esc(alt || '')}" loading="lazy" decoding="async">`;
}
document.addEventListener('error', (e) => {
  const img = e.target;
  if (img.tagName === 'IMG' && img.dataset.fb && img.src !== img.dataset.fb) { img.src = img.dataset.fb; img.dataset.fb = ''; }
}, true);

/* ---------- 작은 추이 그래프 ---------- */
function sparkPoints(series, w, h, hours) {
  if (!series || series.length < 2) return null;
  const last = series[series.length - 1][0];
  let s = series.filter((p) => p[0] >= last - hours);
  if (s.length < 2) s = series.slice(-2);
  const x0 = s[0][0], x1 = s[s.length - 1][0] || x0 + 1;
  const ys = s.map((p) => p[1]);
  const lo = Math.min(...ys), hi = Math.max(...ys);
  const span = hi - lo || 1, tspan = x1 - x0 || 1;
  return s.map((p) => [((p[0] - x0) / tspan) * w, h - 3 - ((p[1] - lo) / span) * (h - 6)]);
}
function spark(series) {
  const pts = sparkPoints(series, 160, 36, 12);
  if (!pts) return '';
  const line = pts.map((p) => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
  return `<svg class="spark" viewBox="0 0 160 36" preserveAspectRatio="none" role="img" aria-label="최근 12시간 조회수 추이"><polygon points="0,36 ${line} 160,36" fill="#E8EEFC"/><polyline points="${line}" fill="none" stroke="#1E4FD8" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>`;
}

/* ---------- 데이터 ---------- */
const cache = {};
function get(path) {
  if (!cache[path]) cache[path] = fetch('/data/' + path, { cache: 'no-cache' }).then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
  return cache[path];
}
const META_FALLBACK = { categories: [] };
const meta = () => get('meta.json').catch(() => META_FALLBACK);

function region() {
  const r = params.get('r');
  if (r === 'kr' || r === 'us') { try { localStorage.setItem('rs-region', r); } catch (e) {} return r; }
  try { const s = localStorage.getItem('rs-region'); if (s === 'kr' || s === 'us') return s; } catch (e) {}
  return 'kr';
}
const RNAME = { kr: '국내', us: '해외' };
function link(page, q) {
  const u = new URLSearchParams(q);
  const s = u.toString();
  return '/' + page + (s ? '?' + s : '');
}

/* ---------- 공통 조각 ---------- */
function card(v, rank) {
  const ratio = ratioText(v.ratio);
  return `<a class="card" href="${link('video', { id: v.id })}">
    <div class="tile">${thumb(v.id, '')}${rank ? `<span class="rank">${rank}</span>` : ''}${v.dur ? `<span class="dur">${dur(v.dur)}</span>` : ''}</div>
    <div class="cb">
      <p class="ct">${esc(title(v.t))}</p>
      <p class="cm">${esc(v.cn)}${v.age_h != null ? ' · ' + ago(v.age_h) : ''}</p>
      ${spark(v.series)}
      <div class="badges"><span class="b-blue">▲ ${kn(v.vph)}/시간</span>${ratio ? `<span class="b-orange">구독자 ${ratio}</span>` : ''}</div>
    </div></a>`;
}
function skeleton(n, h) { return Array.from({ length: n }, () => `<div class="skel" style="height:${h}px"></div>`).join(''); }
function regionTabs(cur, make) {
  return ['kr', 'us'].map((r) => `<a class="tab${r === cur ? ' on' : ''}" role="tab" aria-selected="${r === cur}" href="${make(r)}">${RNAME[r]}</a>`).join('');
}
function catChips(cats, r, cur) {
  return cats.map((c) => `<a class="chip${c.slug === cur ? ' on' : ''}" href="${link('category', { c: c.slug, r })}">${esc(c.name)}</a>`).join('');
}
function setTitle(t, desc) {
  document.title = t;
  if (desc) { const m = $('meta[name="description"]'); if (m) m.setAttribute('content', desc); }
}

/* ---------- 홈 ---------- */
async function home() {
  const r = region();
  $('#tabs').innerHTML = regionTabs(r, (x) => link('', { r: x }));
  $('#heroTitle').textContent = r === 'kr' ? '지금 가장 빠르게 뜨는 국내 쇼츠' : '지금 가장 빠르게 뜨는 해외 쇼츠';
  $('#top5').innerHTML = skeleton(5, 420);
  meta().then((m) => { $('#cats').innerHTML = catChips(m.categories, r, null); });
  try {
    const d = await get(`home-${r}.json`);
    $('#stamp').textContent = kst(d.updated) + ' 갱신 · 1시간마다 자동 업데이트';
    const it = d.items || [];
    $('#top5').innerHTML = it.slice(0, 5).map((v, i) => card(v, i + 1)).join('');
    $('#rest').innerHTML = it.slice(5).map((v, i) => card(v, i + 6)).join('');
    $('#restWrap').hidden = it.length <= 5;
  } catch (e) {
    $('#top5').outerHTML = '<div class="empty">순위를 불러오지 못했어요. 잠시 뒤 새로고침해 주세요.</div>';
  }
  if (r === 'kr') {
    try {
      const u = await get('home-us.json');
      $('#usList').innerHTML = (u.items || []).slice(0, 5).map((v) => `<a class="mini" href="${link('video', { id: v.id })}"><div class="tile">${thumb(v.id, '')}</div><div style="min-width:0;display:flex;flex-direction:column;gap:4px"><p class="ct">${esc(title(v.t))}</p><span class="b-blue" style="align-self:flex-start">▲ ${kn(v.vph)}/시간</span></div></a>`).join('');
      $('#strip').hidden = false;
    } catch (e) {}
  }
}

/* ---------- 카테고리 ---------- */
const SORTS = [
  { key: 'by_score', label: '떡상 속도순', help: '최근 3시간 동안 시간당 조회수가 가장 빠르게 늘어난 순서예요. 구독자 대비 조회가 높으면 가산점이 붙어요.' },
  { key: 'by_ratio', label: '구독자 대비순', help: '구독자 수에 비해 조회수가 가장 많이 나온 순서예요. 작은 채널의 떡상을 찾기 좋아요.' },
  { key: 'by_views', label: '조회수순', help: '최근 7일 안에 올라온 쇼츠를 누적 조회수가 많은 순서로 보여 줘요.' },
];
const PERIODS = [{ h: 168, label: '7일' }, { h: 72, label: '3일' }, { h: 24, label: '24시간' }];
async function category() {
  const r = region();
  const m = await meta();
  const slug = params.get('c') || (m.categories[0] || {}).slug;
  const cat = m.categories.find((c) => c.slug === slug);
  if (!cat) { $('#grid').outerHTML = '<div class="empty">없는 카테고리예요. <a href="/">홈으로 가기</a></div>'; return; }
  $('#crumbName').textContent = cat.name;
  $('#name').textContent = `${cat.name} 쇼츠 떡상 순위`;
  setTitle(`${cat.name} 쇼츠 떡상 순위 (${RNAME[r]}) | 라이징쇼츠`, `${cat.name} 분야에서 지금 가장 빠르게 조회수가 늘고 있는 ${RNAME[r]} 유튜브 쇼츠 순위. 1시간마다 갱신.`);
  $('#tabs').innerHTML = regionTabs(r, (x) => link('category', { c: slug, r: x }));
  $('#others').innerHTML = catChips(m.categories.filter((c) => c.slug !== slug), r, null);
  $('#grid').innerHTML = skeleton(10, 420);
  let d;
  try { d = await get(`cat-${slug}-${r}.json`); } catch (e) { $('#grid').outerHTML = '<div class="empty">순위를 불러오지 못했어요.</div>'; return; }
  const st = { sort: 'by_score', period: 168, shown: 20 };
  const total = d.total != null ? d.total : (d.by_score || []).length;
  $('#lead').textContent = `최근 7일 안에 올라온 ${RNAME[r]} ${cat.name} 쇼츠 ${total.toLocaleString('ko-KR')}개를 추적하고 있어요. ${kst(d.updated)} 갱신.`;
  function draw() {
    $('#sorts').innerHTML = SORTS.map((s) => `<button class="seg${s.key === st.sort ? ' on' : ''}" aria-pressed="${s.key === st.sort}" data-sort="${s.key}">${s.label}</button>`).join('');
    $('#periods').innerHTML = PERIODS.map((p) => `<button class="seg soft${p.h === st.period ? ' on' : ''}" aria-pressed="${p.h === st.period}" data-period="${p.h}">${p.label}</button>`).join('');
    $('#help').textContent = SORTS.find((s) => s.key === st.sort).help;
    const all = (d[st.sort] || []).filter((v) => v.age_h == null || v.age_h <= st.period);
    $('#grid').innerHTML = all.length ? all.slice(0, st.shown).map((v, i) => card(v, i + 1)).join('') : '';
    $('#none').hidden = all.length > 0;
    const btn = $('#moreBtn');
    btn.hidden = all.length <= st.shown;
    btn.textContent = `${st.shown + 1}~${all.length}위 더 보기`;
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.sort) { st.sort = b.dataset.sort; st.shown = 20; draw(); }
    else if (b.dataset.period) { st.period = +b.dataset.period; st.shown = 20; draw(); }
    else if (b.id === 'moreBtn') { st.shown = 50; draw(); }
  });
  draw();
}

/* ---------- 검색 ---------- */
const norm = (s) => String(s || '').toLowerCase().replace(/\s+/g, '');
async function search() {
  const r = region();
  const q = (params.get('q') || '').trim();
  $('#bigq').value = q;
  $('#tabs').innerHTML = regionTabs(r, (x) => link('search', { q, r: x }));
  meta().then((m) => { $('#cats').innerHTML = catChips(m.categories, r, null); });
  if (!q) { $('#title').textContent = '키워드로 떡상 쇼츠 찾기'; $('#results').innerHTML = '<div class="empty">찾고 싶은 키워드를 입력해 보세요. 예: 진돗개, 괴담, 챌린지</div>'; return; }
  setTitle(`'${q}' 떡상 쇼츠 검색 | 라이징쇼츠`);
  let d;
  try { d = await get(`search-${r}.json`); } catch (e) { $('#results').innerHTML = '<div class="empty">검색 데이터를 불러오지 못했어요.</div>'; return; }
  const words = q.split(/\s+/).map(norm).filter(Boolean);
  const hits = (d.items || []).filter((v) => {
    const hay = norm(v.t + ' ' + (v.tags || []).join(' ') + ' ' + v.cn);
    return words.every((w) => hay.includes(w));
  });
  const st = { sort: 'score' };
  $('#title').innerHTML = `'${esc(q)}' 떡상 쇼츠 <span style="color:var(--blue)">${hits.length.toLocaleString('ko-KR')}개</span>`;
  $('#sub').textContent = `최근 7일 안에 올라와 추적 중인 ${RNAME[r]} 쇼츠 가운데 제목·태그·채널명에 검색어가 들어간 영상이에요.`;
  if (!hits.length) { $('#results').innerHTML = '<div class="empty">아직 이 키워드로 뜨는 쇼츠가 없어요. 다른 말로 찾아보거나 카테고리를 둘러보세요.</div>'; return; }
  const sumV = hits.reduce((a, v) => a + Math.max(v.vph || 0, 0), 0);
  const chs = {}; hits.forEach((v) => { chs[v.cn] = (chs[v.cn] || 0) + 1; });
  const topCh = Object.entries(chs).sort((a, b) => b[1] - a[1])[0];
  const best = hits.slice().sort((a, b) => (b.ratio || 0) - (a.ratio || 0))[0];
  $('#stats').innerHTML = `
    <div class="stat"><span>합계 시간당 조회</span><span class="v num" style="color:var(--blue)">${kn(sumV)}</span></div>
    <div class="stat"><span>가장 많이 나온 채널</span><span class="v s">${esc(topCh[0])} <small style="font-weight:500;color:var(--muted)">${hits.length}개 중 ${topCh[1]}개</small></span></div>
    <div class="stat warm"><span>구독자 대비 최고</span><span class="v s">${ratioText(best.ratio) || '-'} <small style="font-weight:500;color:var(--muted)">${esc(best.cn)}</small></span></div>`;
  $('#stats').hidden = false;
  function draw() {
    $('#sorts').innerHTML = [['score', '떡상 속도순'], ['ratio', '구독자 대비순'], ['views', '조회수순']].map(([k, l]) => `<button class="seg${k === st.sort ? ' on' : ''}" aria-pressed="${k === st.sort}" data-s="${k}">${l}</button>`).join('');
    const list = hits.slice().sort((a, b) => (b[st.sort] || 0) - (a[st.sort] || 0)).slice(0, 100);
    $('#results').innerHTML = `<div class="table" role="list">
      <div class="row hd hide-sm"><span>순위</span><span></span><span>쇼츠</span><span class="r hide">시간당 조회</span><span class="r hide">구독자 대비</span><span class="r hide">누적 조회</span></div>
      ${list.map((v, i) => `<a class="row" role="listitem" href="${link('video', { id: v.id })}">
        <span class="rk${i < 3 ? ' top' : ''}">${i + 1}</span>
        <span class="tile">${thumb(v.id, '')}</span>
        <span style="min-width:0;display:flex;flex-direction:column;gap:4px"><span class="tt">${esc(title(v.t))}</span><span class="cm">${esc(v.cn)}</span>
          <span class="row-sub"><span class="b-blue">▲ ${kn(v.vph)}/시간</span>${v.ratio != null ? `<span class="b-orange">구독자 ${ratioText(v.ratio)}</span>` : ''}</span></span>
        <span class="r hide num" style="font-weight:800;font-size:17px;color:var(--blue)">▲ ${kn(v.vph)}</span>
        <span class="r hide num" style="font-weight:700;color:var(--orange)">${ratioText(v.ratio) || '-'}</span>
        <span class="r hide num" style="font-weight:700">${kn(v.views)}</span></a>`).join('')}</div>`;
  }
  $('#sorts').addEventListener('click', (e) => { const b = e.target.closest('button'); if (b) { st.sort = b.dataset.s; draw(); } });
  $('#sortWrap').hidden = false;
  draw();
}

/* ---------- 영상 상세 ---------- */
function bigChart(series) {
  const W = 760, H = 260, L = 64, R = 12, T = 20, B = 220;
  const xs = series.map((p) => p[0]), ys = series.map((p) => p[1]);
  const x0 = xs[0], x1 = xs[xs.length - 1], lo = Math.min(...ys), hi = Math.max(...ys);
  const X = (x) => L + ((x - x0) / ((x1 - x0) || 1)) * (W - L - R);
  const Y = (y) => B - ((y - lo) / ((hi - lo) || 1)) * (B - T);
  const pts = series.map((p) => X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1)).join(' ');
  const mid = (lo + hi) / 2;
  const ticks = [];
  const n = Math.min(7, series.length);
  for (let i = 0; i < n; i++) {
    const t = x0 + ((x1 - x0) * i) / ((n - 1) || 1);
    ticks.push(`<text x="${X(t).toFixed(1)}" y="246" text-anchor="middle" font-size="12" fill="#5A616C">${kstHour(t)}시</text>`);
  }
  const dots = series.length <= 60 ? series.map((p) => `<circle cx="${X(p[0]).toFixed(1)}" cy="${Y(p[1]).toFixed(1)}" r="3" fill="#fff" stroke="#1E4FD8" stroke-width="2"/>`).join('') : '';
  const last = series[series.length - 1];
  return `<svg class="chart num" viewBox="0 0 ${W} ${H}" role="img" aria-label="조회수가 ${kn(lo)}에서 ${kn(hi)}로 늘어난 추이" font-family="Inter, 'Noto Sans KR', sans-serif">
    <line x1="${L}" y1="${T}" x2="${W - R}" y2="${T}" stroke="#ECEEF1"/><line x1="${L}" y1="120" x2="${W - R}" y2="120" stroke="#ECEEF1"/><line x1="${L}" y1="${B}" x2="${W - R}" y2="${B}" stroke="#D9DDE3"/>
    <text x="${L - 8}" y="${T + 4}" text-anchor="end" font-size="12" fill="#5A616C">${kn(hi)}</text>
    <text x="${L - 8}" y="124" text-anchor="end" font-size="12" fill="#5A616C">${kn(mid)}</text>
    <text x="${L - 8}" y="${B + 4}" text-anchor="end" font-size="12" fill="#5A616C">${kn(lo)}</text>
    <polygon points="${L},${B} ${pts} ${X(last[0]).toFixed(1)},${B}" fill="#E8EEFC"/>
    <polyline points="${pts}" fill="none" stroke="#1E4FD8" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
    ${dots}<circle cx="${X(last[0]).toFixed(1)}" cy="${Y(last[1]).toFixed(1)}" r="6" fill="#1E4FD8"/>${ticks.join('')}</svg>`;
}
function insight(v, series) {
  if (!series || series.length < 4) return '아직 측정 횟수가 적어요. 1시간마다 조회수를 다시 재서 그래프가 채워집니다.';
  const half = Math.floor(series.length / 2);
  const rate = (a, b) => (b[1] - a[1]) / ((b[0] - a[0]) || 1);
  const early = rate(series[0], series[half]), late = rate(series[half], series[series.length - 1]);
  let s;
  if (late > early * 1.15) s = '최근 들어 조회수가 늘어나는 속도가 더 빨라지고 있어요.';
  else if (late < early * 0.7) s = '처음보다 증가 속도는 줄었지만 아직 꾸준히 오르고 있어요.';
  else s = '측정 기간 내내 비슷한 속도로 꾸준히 오르고 있어요.';
  if (v.ratio != null && v.ratio >= 100) s += ` 구독자 ${kn(v.subs)}명 채널이 구독자의 ${ratioText(v.ratio)} 조회를 만든, 추천을 크게 탄 사례예요.`;
  return s;
}
async function video() {
  const id = params.get('id') || '';
  if (!/^[\w-]{6,20}$/.test(id)) { $('#detail').innerHTML = '<div class="empty">영상을 찾을 수 없어요. <a href="/">홈으로 가기</a></div>'; return; }
  const yt = `https://www.youtube.com/shorts/${id}`;
  let v = null;
  try { v = await get(`v/${id}.json`); } catch (e) {
    for (const r of ['kr', 'us']) {
      try { const d = await get(`search-${r}.json`); v = (d.items || []).find((x) => x.id === id); if (v) { v.region = r; break; } } catch (e2) {}
    }
  }
  if (!v) { $('#detail').innerHTML = `<div class="empty">순위 추적이 끝난 영상이에요 (업로드 7일 경과). <a href="${yt}" target="_blank" rel="noopener">유튜브에서 보기</a></div>`; return; }
  const m = await meta();
  const t = title(v.t);
  setTitle(`${t} - 조회수 추이 | 라이징쇼츠`, `${v.cn}의 쇼츠 "${t}" 조회수 ${kn(v.views)}, 시간당 ${kn(v.vph)} 증가. 구독자 대비 ${ratioText(v.ratio) || '-'}.`);
  const firstCat = (v.ranks || []).find((x) => x.slug);
  $('#crumbs').innerHTML = `<a href="/">홈</a><span aria-hidden="true">›</span>${firstCat ? `<a href="${link('category', { c: firstCat.slug, r: firstCat.region })}">${esc(firstCat.label)}</a><span aria-hidden="true">›</span>` : ''}<b>영상 상세</b>`;
  const series = v.series || [];
  const grow = series.length >= 2 ? { d: series[series.length - 1][1] - series[0][1], h: Math.round(series[series.length - 1][0] - series[0][0]) } : null;
  const badges = (v.ranks || []).map((x, i) => `<a class="b-solid${i ? ' lite' : ''}" href="${x.slug ? link('category', { c: x.slug, r: x.region }) : link('', { r: x.region })}">${esc(x.label)} ${x.rank}위</a>`).join('');
  const tags = (v.tags || []).slice(0, 8).map((g) => `<a class="chip" href="${link('search', { q: g, r: v.region || 'kr' })}"># ${esc(g)}</a>`).join('');
  const subsLine = [v.cn, v.subs != null ? `구독자 ${kn(v.subs)}명` : '', v.age_h != null ? ago(v.age_h) + ' 업로드' : ''].filter(Boolean).map(esc).join(' · ');
  $('#detail').innerHTML = `
  <div class="detail">
    <div class="side">
      <div class="tile">${thumb(id, t + ' 썸네일')}${v.dur ? `<span class="dur">${dur(v.dur)}</span>` : ''}</div>
      <div class="acts" style="display:flex;flex-direction:column;gap:10px">
        <a class="btn dark" href="${yt}" target="_blank" rel="noopener"><svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5 L13 8 L4 13.5 Z" fill="#fff"/></svg>유튜브에서 보기</a>
        <button class="btn" id="copy" type="button">이 페이지 링크 복사</button>
      </div>
    </div>
    <div class="body">
      <div style="display:flex;flex-direction:column;gap:10px">
        ${badges ? `<div class="badges">${badges}</div>` : ''}
        <h1 style="font-size:32px;line-height:1.3;overflow-wrap:anywhere">${esc(t)}</h1>
        <p class="lead">${subsLine}</p>
      </div>
      <div class="stats">
        <div class="stat"><span>시간당 조회</span><span class="v num" style="color:var(--blue)">${kn(v.vph)}</span></div>
        <div class="stat"><span>누적 조회</span><span class="v num">${kn(v.views)}</span></div>
        <div class="stat warm"><span>구독자 대비</span><span class="v num" style="color:var(--orange)">${ratioText(v.ratio) || '-'}</span></div>
        ${grow && grow.h > 0 ? `<div class="stat"><span>최근 ${grow.h}시간 동안 늘어난 조회</span><span class="v num">+${kn(grow.d)}</span></div>` : ''}
      </div>
      ${series.length >= 2 ? `<section class="panel" aria-label="조회수 추이">
        <div class="section-h" style="flex-wrap:wrap"><h2 style="font-size:18px">최근 ${series.length}번 측정한 조회수</h2><span class="cm">1시간마다 자동 측정 · 한국 시간</span></div>
        ${bigChart(series)}
        <p class="note"><b>한눈에 보기</b> · ${esc(insight(v, series))}</p></section>` : ''}
      ${tags ? `<section style="display:flex;flex-direction:column;gap:10px"><h2 style="font-size:16px">태그·키워드</h2><div class="chips">${tags}</div></section>` : ''}
    </div>
  </div>
  ${(v.related || []).length ? `<section class="section"><div class="section-h"><h2>같은 카테고리에서 뜨는 쇼츠</h2>${firstCat ? `<a href="${link('category', { c: firstCat.slug, r: firstCat.region })}">${esc(firstCat.label)} 전체 순위 ›</a>` : ''}</div>
    <div class="grid4">${v.related.map((x) => card(x)).join('')}</div></section>` : ''}`;
  $('#copy').addEventListener('click', async (e) => {
    try { await navigator.clipboard.writeText(location.href); e.target.textContent = '복사했어요'; } catch (err) { e.target.textContent = '복사가 안 되면 주소창을 이용해 주세요'; }
  });
  void m;
}

/* ---------- 시작 ---------- */
const page = document.body.dataset.page;
const nav = document.querySelector(`.nav a[data-nav="${page}"]`);
if (nav) nav.classList.add('on');
const run = { home, category, search, video }[page];
if (run) run();
})();
