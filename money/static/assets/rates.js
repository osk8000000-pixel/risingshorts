/* 돈챙김 금리 화면: /api/rates 에서 금감원 공시 금리를 받아 순위로 보여 준다. */
(function () {
  var cache = {};
  function load(kind) {
    if (!cache[kind]) cache[kind] = fetch("/api/rates?kind=" + kind).then(function (r) { return r.json(); });
    return cache[kind];
  }
  function nm(s) { return String(s || "").replace(/\s*\n\s*/g, " ").replace(/^주식회사\s*|\s*주식회사$/g, "").trim(); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function pick(items, term, group) {
    var rows = [];
    items.forEach(function (p) {
      if (group && group !== "all" && p.g !== group) return;
      var best = null;
      p.opts.forEach(function (o) {
        if (o.t !== term) return;
        var r2 = Number(o.r2 || o.r || 0);
        if (!best || r2 > best.r2) best = { r: Number(o.r || 0), r2: r2, type: o.type, rsrv: o.rsrv };
      });
      if (best) rows.push({ p: p, o: best });
    });
    rows.sort(function (a, b) { return b.o.r2 - a.o.r2 || b.o.r - a.o.r; });
    return rows;
  }
  function month(m) { return m ? m.slice(0, 4) + "년 " + Number(m.slice(4)) + "월" : ""; }

  function renderTable(el, opt) {
    el.innerHTML = '<div class="skel"></div><div class="skel"></div><div class="skel"></div><div class="skel"></div>';
    load(opt.kind).then(function (d) {
      if (d.error) throw new Error(d.error);
      var rows = pick(d.items, opt.term, opt.group).slice(0, opt.limit || 50);
      if (!rows.length) { el.innerHTML = '<div class="empty" style="border:0">이 조건의 상품이 없어요.</div>'; return; }
      var h = '<div class="rate-head"><span>순위</span><span>상품</span><span>최고 금리</span><span>기본 금리</span></div>';
      rows.forEach(function (x, i) {
        var p = x.p, o = x.o;
        h += '<div class="rate-row"><span class="rk">' + (i + 1) + '</span>' +
          '<div><div class="bk">' + esc(nm(p.bank)) + (p.g === "savings" ? ' · 저축은행' : '') + (o.rsrv ? ' · ' + esc(o.rsrv) : '') + '</div><div class="pn">' + esc(nm(p.name)) + '</div></div>' +
          '<div class="rt"><b>' + o.r2.toFixed(2) + '%</b><small>우대 포함</small></div>' +
          '<div class="rt base"><b>' + o.r.toFixed(2) + '%</b><small>' + esc(o.type || "기본") + '</small></div>' +
          '<details><summary>가입 조건·우대 조건 보기</summary><p><b>가입 방법</b> ' + esc(p.join) + '\n<b>가입 대상</b> ' + esc(p.member) +
          (p.limit ? '\n<b>최고 한도</b> ' + Number(p.limit).toLocaleString("ko-KR") + '원' : '') +
          '\n\n<b>우대 조건</b>\n' + esc(p.cond) + (p.note ? '\n\n<b>기타</b>\n' + esc(p.note) : '') + '</p></details></div>';
      });
      el.innerHTML = h;
      var s = document.getElementById(opt.srcId || "rate-src");
      if (s) s.textContent = "금융감독원 금융상품통합비교공시(" + month(d.month) + " 공시) 금융회사 상품정보를 사용한 결과입니다. 실제 금리는 가입 시점과 우대 조건에 따라 달라질 수 있으니 가입 전 금융회사에서 확인하세요.";
    }).catch(function () {
      el.innerHTML = '<div class="empty" style="border:0">금리 정보를 잠시 불러오지 못했어요. 잠시 뒤 새로고침해 주세요.</div>';
    });
  }

  function renderMini(el, kind, label) {
    load(kind).then(function (d) {
      var rows = pick(d.items, 12, "all").slice(0, 3);
      el.innerHTML = rows.map(function (x, i) {
        return '<a class="rc' + (kind === "saving" ? " s" : "") + '" href="/rates#' + kind + '"><div class="k">' + label + ' ' + (i + 1) + '위 · ' + esc(nm(x.p.bank)) + '</div><div class="n">' + esc(nm(x.p.name)) +
          '</div><div class="v">' + x.o.r2.toFixed(2) + '<em>%</em></div><div class="m">기본 ' + x.o.r.toFixed(2) + '% · 12개월</div></a>';
      }).join("");
    }).catch(function () { el.innerHTML = '<div class="empty">금리 정보를 잠시 불러오지 못했어요.</div>'; });
  }

  window.DC = { renderTable: renderTable, renderMini: renderMini };

  // 금리 페이지
  var box = document.getElementById("rate-box");
  if (box) {
    var st = { kind: location.hash === "#saving" ? "saving" : "deposit", term: 12, group: "all" };
    function sync() {
      document.querySelectorAll("[data-kind]").forEach(function (b) { b.classList.toggle("on", b.dataset.kind === st.kind); });
      document.querySelectorAll("[data-term]").forEach(function (b) { b.classList.toggle("on", Number(b.dataset.term) === st.term); });
      document.querySelectorAll("[data-group]").forEach(function (b) { b.classList.toggle("on", b.dataset.group === st.group); });
      renderTable(box, st);
    }
    document.addEventListener("click", function (e) {
      var b = e.target.closest("[data-kind],[data-term],[data-group]");
      if (!b) return;
      if (b.dataset.kind) { st.kind = b.dataset.kind; history.replaceState(null, "", "#" + st.kind); }
      if (b.dataset.term) st.term = Number(b.dataset.term);
      if (b.dataset.group) st.group = b.dataset.group;
      sync();
    });
    sync();
  }
  var m1 = document.getElementById("mini-deposit"), m2 = document.getElementById("mini-saving");
  if (m1) renderMini(m1, "deposit", "예금");
  if (m2) renderMini(m2, "saving", "적금");

  // 이자 계산기
  var cf = document.getElementById("calc");
  if (cf) {
    function calc() {
      var kind = cf.kind.value, amt = Number(cf.amt.value.replace(/[^\d]/g, "")) || 0, rate = Number(cf.rate.value) || 0, mon = Number(cf.mon.value) || 12;
      var interest = kind === "deposit" ? amt * rate / 100 * mon / 12 : amt * rate / 100 * (mon * (mon + 1) / 2) / 12;
      var principal = kind === "deposit" ? amt : amt * mon;
      var tax = Math.floor(interest * 0.154);
      document.getElementById("c-int").textContent = Math.round(interest).toLocaleString("ko-KR") + "원";
      document.getElementById("c-tax").textContent = tax.toLocaleString("ko-KR") + "원";
      document.getElementById("c-total").textContent = Math.round(principal + interest - tax).toLocaleString("ko-KR") + "원";
      document.getElementById("c-amt-l").textContent = kind === "deposit" ? "맡길 돈 (원)" : "매달 넣을 돈 (원)";
    }
    cf.addEventListener("input", calc); calc();
  }
})();
