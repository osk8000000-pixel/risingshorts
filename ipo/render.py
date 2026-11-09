"""공모주데이 정적 사이트 생성기.

사용: python ipo/render.py <ipos.json> <출력 폴더>
ipo/static 의 파일을 복사하고, 홈·달력·종목·증권사·가이드·안내 페이지 HTML 과 sitemap.xml 을 만든다.
"""
import calendar as pycal
import hashlib
import json
import os
import shutil
import sys
from datetime import date, datetime, timedelta
from html import escape as E

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guides import GUIDES  # noqa: E402

SITE = "https://gongmojuday.com"
NAME = "공모주데이"
CONTACT = "risingshorts.help@gmail.com"
ADSENSE = "ca-pub-2895025957691898"
MIN_SHARES = 10      # 균등배정 최소 청약 수량(관행)
DEPOSIT_RATE = 0.5   # 청약 증거금률(관행)
DOW = "월화수목금토일"
STATUS = {"subscribing": "청약 중", "upcoming": "청약 예정", "refund": "환불 대기",
          "done": "청약 마감", "withdrawn": "공모 철회", "unknown": "일정 미정"}

BROKERS = {  # 공시 표기 -> (화면 표기, 주소)
    "한국투자증권": ("한국투자증권", "kis"), "미래에셋증권": ("미래에셋증권", "miraeasset"),
    "삼성증권": ("삼성증권", "samsung"), "NH투자증권": ("NH투자증권", "nh"), "엔에이치투자증권": ("NH투자증권", "nh"),
    "KB증권": ("KB증권", "kb"), "케이비증권": ("KB증권", "kb"), "대신증권": ("대신증권", "daishin"),
    "신한투자증권": ("신한투자증권", "shinhan"), "하나증권": ("하나증권", "hana"), "키움증권": ("키움증권", "kiwoom"),
    "아이비케이투자증권": ("IBK투자증권", "ibk"), "IBK투자증권": ("IBK투자증권", "ibk"),
    "유진투자증권": ("유진투자증권", "eugene"), "유진증권": ("유진투자증권", "eugene"),
    "신영증권": ("신영증권", "shinyoung"), "우리투자증권": ("우리투자증권", "woori"),
    "BNK투자증권": ("BNK투자증권", "bnk"), "비엔케이투자증권": ("BNK투자증권", "bnk"),
    "교보증권": ("교보증권", "kyobo"), "DB금융투자": ("DB증권", "db"), "DB증권": ("DB증권", "db"), "디비금융투자": ("DB증권", "db"),
    "한화투자증권": ("한화투자증권", "hanwha"), "하이투자증권": ("iM증권", "im"), "아이엠증권": ("iM증권", "im"), "iM증권": ("iM증권", "im"),
    "유안타증권": ("유안타증권", "yuanta"), "현대차증권": ("현대차증권", "hyundai"), "SK증권": ("SK증권", "sk"), "에스케이증권": ("SK증권", "sk"),
    "상상인증권": ("상상인증권", "sangsangin"), "LS증권": ("LS증권", "ls"), "엘에스증권": ("LS증권", "ls"),
    "메리츠증권": ("메리츠증권", "meritz"), "다올투자증권": ("다올투자증권", "daol"), "부국증권": ("부국증권", "bookook"),
    "한양증권": ("한양증권", "hanyang"), "케이프투자증권": ("케이프투자증권", "cape"), "토스증권": ("토스증권", "toss"),
}


def broker(n):
    n = n.strip()
    if n in BROKERS:
        return BROKERS[n]
    return n, "b" + hashlib.md5(n.encode()).hexdigest()[:6]


# ---------- 형식 ----------
def d(s):
    return date.fromisoformat(s) if s else None


def fd(s, year=False):
    x = d(s)
    if not x:
        return "미정"
    return (f"{x.year}." if year else "") + f"{x.month}.{x.day}({DOW[x.weekday()]})"


def frange(a, b):
    if not a:
        return "미정"
    return fd(a) if not b or a == b else f"{fd(a)}~{fd(b)}"


def won(n):
    return f"{int(n):,}원" if n else "미정"


def eok(n):
    if not n:
        return "미정"
    v = n / 1e8
    return f"{v:,.0f}억 원" if v >= 10 else f"{v:,.1f}억 원"


def min_dep(it):
    return int(it["price"] * MIN_SHARES * DEPOSIT_RATE) if it.get("price") else None


def badge(st):
    return f'<span class="badge b-{st}">{STATUS.get(st, st)}</span>'


def lead_uw(it):
    uws = it.get("underwriters") or []
    leads = [u for u in uws if "대표" in (u.get("role") or "")] or uws[:1]
    return [broker(u["name"]) for u in leads]


def uw_text(it):
    names = []
    for u in it.get("underwriters") or []:
        n = broker(u["name"])[0]
        if n not in names:
            names.append(n)
    return ", ".join(names) or "미정"


def price_text(it):
    if not it.get("price"):
        return "미정"
    return won(it["price"]) + ("" if it.get("price_confirmed") else " (희망가)")


def josa(word, a, b):
    ch = word[-1]
    if "가" <= ch <= "힣":
        return a if (ord(ch) - 0xAC00) % 28 else b
    return b


# ---------- 틀 ----------
NAV = [("/", "home", "청약 일정"), ("/calendar", "calendar", "달력"), ("/broker", "broker", "증권사별"), ("/guide", "guide", "가이드")]
ICON = ('<svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><rect width="30" height="30" rx="9" fill="#0B7A55"/>'
        '<rect x="7" y="9" width="16" height="13" rx="2.5" fill="none" stroke="#fff" stroke-width="2.2"/>'
        '<path d="M7 13.5H23M11.5 7v4M18.5 7v4" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>'
        '<path d="M12 18l2 1.8 4-4" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def page(path, title, desc, body, nav="", noindex=False, extra=""):
    url = SITE + (path if path != "/" else "/")
    full = title if title.startswith(NAME) else f"{title} | {NAME}"
    navh = "".join(f'<a href="{h}"{" class=on" if k == nav else ""}>{t}</a>' for h, k, t in NAV)
    robots = '<meta name="robots" content="noindex">\n' if noindex else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(full)}</title>
<meta name="description" content="{E(desc)}">
{robots}<link rel="canonical" href="{url}">
<meta property="og:title" content="{E(full)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{NAME}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0B7A55">
<link rel="icon" href="/assets/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=Inter:wght@500;700;800&display=swap" rel="stylesheet">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE}" crossorigin="anonymous"></script>
<link rel="stylesheet" href="/assets/style.css?v=2">
{extra}</head>
<body>
<header class="top"><div class="wrap">
<a class="logo" href="/" aria-label="{NAME} 홈">{ICON}<span>{NAME}</span></a>
<nav class="nav" aria-label="주 메뉴">{navh}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
<nav aria-label="사이트 안내"><a href="/about">소개</a><a href="/guide">가이드</a><a href="/contact">문의</a><a href="/privacy">개인정보처리방침</a></nav>
<p>공모주데이는 금융감독원 전자공시시스템(DART) 공시를 바탕으로 공모주 청약 일정을 정리합니다. 정보는 1시간마다 갱신되지만 늦거나 틀릴 수 있으니, 청약 전 증권사 공지와 공시 원문을 꼭 확인하세요.</p>
<p>투자 권유가 아니며, 투자 판단과 책임은 투자자 본인에게 있습니다. © {date.today().year} {NAME}</p>
</div></footer>
</body>
</html>
"""


def ipo_url(it):
    return f"/ipo/{it['corp_code']}"


def name_html(it):
    return E(it["name"]) + ('<span class="tag">스팩</span>' if it.get("spac") else "")


def table(items, cols=("date", "name", "price", "uw", "min", "status")):
    head = {"date": "청약일", "name": "종목", "price": "공모가", "uw": "주관사", "min": "최소 증거금", "status": "상태"}
    th = "".join(f'<th{" class=r" if c in ("price", "min") else ""}>{head[c]}</th>' for c in cols)
    rows = []
    for it in items:
        cell = {
            "date": f'<td class="c-date num">{frange(it["sub_start"], it["sub_end"])}</td>',
            "name": f'<td class="c-name"><a href="{ipo_url(it)}">{name_html(it)}</a></td>',
            "price": f'<td class="c-price r num">{won(it.get("price"))}{"" if it.get("price_confirmed") or not it.get("price") else '<span class="sub">희망가</span>'}</td>',
            "uw": f'<td class="c-uw">{E(uw_text(it))}</td>',
            "min": f'<td class="c-min r num">{won(min_dep(it))}</td>',
            "status": f'<td class="c-status">{badge(it["status"])}</td>',
        }
        rows.append("<tr>" + "".join(cell[c] for c in cols) + "</tr>")
    return f'<div class="tbl-wrap"><table class="tbl"><thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def card(it, hot=False):
    return f"""<a class="card{' hot' if hot else ''}" href="{ipo_url(it)}">
<div style="display:flex;justify-content:space-between;gap:10px;align-items:center"><span class="name">{name_html(it)}</span>{badge(it['status'])}</div>
<dl><dt>청약일</dt><dd class="num">{frange(it['sub_start'], it['sub_end'])}</dd>
<dt>공모가</dt><dd class="num">{price_text(it)}</dd>
<dt>최소 증거금</dt><dd class="num">{won(min_dep(it))} <span style="color:var(--muted);font-weight:400">(10주)</span></dd>
<dt>주관사</dt><dd>{E(uw_text(it))}</dd>
<dt>환불일</dt><dd class="num">{fd(it['refund'])}</dd></dl></a>"""


# ---------- 홈 ----------
def render_home(items, today, updated):
    wk0 = today - timedelta(days=today.weekday())
    wk1 = wk0 + timedelta(days=6)
    live = [i for i in items if i["status"] != "withdrawn"]
    this_week = [i for i in live if i["sub_start"] and d(i["sub_start"]) <= wk1 and d(i["sub_end"] or i["sub_start"]) >= wk0]
    subs = [i for i in items if i["status"] == "subscribing"]
    up = [i for i in items if i["status"] == "upcoming"]
    ref = [i for i in items if i["status"] == "refund"]
    done = sorted([i for i in items if i["status"] in ("done", "withdrawn")], key=lambda x: x["sub_start"] or "", reverse=True)[:12]

    if this_week:
        names = ", ".join(i["name"] for i in this_week[:6]) + (f" 외 {len(this_week) - 6}개" if len(this_week) > 6 else "")
        summary = f"이번 주({wk0.month}.{wk0.day}~{wk1.month}.{wk1.day}) 청약하는 공모주는 <b>{len(this_week)}개</b>입니다: {E(names)}."
    else:
        summary = f"이번 주({wk0.month}.{wk0.day}~{wk1.month}.{wk1.day})에는 청약 일정이 없습니다."
    if subs:
        now_html = '<div class="cards">' + "".join(card(i, True) for i in subs) + "</div>"
    else:
        nxt = up[0] if up else None
        msg = f'다음 청약은 <a href="{ipo_url(nxt)}">{E(nxt["name"])}</a>, {fd(nxt["sub_start"])}부터입니다.' if nxt else "예정된 청약이 아직 없습니다."
        now_html = f'<div class="empty">오늘 청약할 수 있는 공모주는 없습니다. {msg}</div>'
    week_cards = [i for i in this_week if i["status"] == "upcoming"]
    body = f"""
<h1>공모주 청약 일정</h1>
<p class="lead">{summary} 청약일, 공모가, 주관 증권사, 최소 증거금, 환불일을 DART 공시에서 모아 1시간마다 갱신합니다.</p>
<p class="stamp">마지막 갱신 {E(updated)}</p>

<section><h2>오늘 청약 가능</h2>{now_html}</section>
{f'<section><h2>이번 주 청약 예정</h2><div class="cards">{"".join(card(i) for i in week_cards)}</div></section>' if week_cards else ''}
<section><div class="sec-head"><h2>다가오는 청약 일정</h2><a href="/calendar">달력으로 보기 →</a></div>
{table(up) if up else '<div class="empty">예정된 청약이 없습니다.</div>'}
<p class="note">공모가 옆 '희망가'는 수요예측 전 증권신고서에 적힌 값으로, 확정 공모가 공시가 나오면 바뀔 수 있습니다. 최소 증거금은 10주·증거금률 50% 기준입니다.</p></section>
{f'<section><h2>환불 예정</h2>{table(ref, ("date", "name", "price", "uw", "status"))}<p class="note">배정받지 못한 증거금은 각 종목의 환불일에 돌아옵니다: ' + ", ".join(E(i["name"]) + " " + fd(i["refund"]) for i in ref) + '.</p></section>' if ref else ''}
<section><h2>최근 청약 마감</h2>{table(done, ("date", "name", "price", "uw", "status")) if done else '<div class="empty">최근 마감된 청약이 없습니다.</div>'}</section>
<section><h2>처음이라면</h2><div class="links">{''.join(f'<a href="/guide/{g["slug"]}">{E(g["title"].split(":")[0])}<span>→</span></a>' for g in GUIDES[:4])}</div></section>
"""
    return page("/", f"{NAME} | 공모주 청약 일정·공모가·환불일 한눈에",
                "이번 주 공모주 청약 일정을 한눈에. 청약일, 공모가, 주관 증권사, 최소 증거금, 환불일을 DART 공시에서 모아 1시간마다 갱신합니다.",
                body, "home")


# ---------- 종목 ----------
def render_ipo(it, today):
    leads = lead_uw(it)
    lead_txt = ", ".join(n for n, _ in leads) or "주관사"
    p = it.get("price")
    mind = min_dep(it)
    conf = "확정 공모가" if it.get("price_confirmed") else "희망 공모가(확정 전)"
    t = today.isoformat()

    def step(label, s):
        if not s:
            return ""
        cls = "past" if s < t else ("now" if s == t else "next")
        return f'<li class="{cls}"><span class="dot"></span><span>{label}</span><span class="when num">{fd(s, True)}</span></li>'

    timeline = (step("청약 시작", it["sub_start"]) + (step("청약 마감", it["sub_end"]) if it["sub_end"] != it["sub_start"] else "")
                + step("환불·납입", it["refund"]))
    uw_rows = "".join(
        f'<li><a href="/broker/{broker(u["name"])[1]}">{E(broker(u["name"])[0])}</a><span>{E(u.get("role") or "")}'
        f'{" · " + format(int(u["shares"]), ",") + "주" if u.get("shares") else ""}</span></li>' for u in it.get("underwriters") or [])
    filings = "".join(f'<li><a href="{E(f["url"])}" rel="nofollow noopener" target="_blank">{E(f["title"])}</a>'
                      f'<span class="num" style="color:var(--muted);white-space:nowrap">{f["date"][:4]}.{f["date"][4:6]}.{f["date"][6:]}</span></li>'
                      for f in reversed(it.get("filings") or []))
    nm = it["name"]
    if it["status"] == "withdrawn":
        text = f"{nm}{josa(nm, '은', '는')} 공모 철회 신고서가 제출되어 이번 청약이 진행되지 않습니다. 회사가 다시 증권신고서를 내면 새 일정이 이 페이지에 반영됩니다."
    else:
        text = (f"{nm}{josa(nm, '은', '는')} {lead_txt}{josa(lead_txt, '이', '가')} 대표 주관하는 신규 상장 공모주입니다. "
                f"일반 청약은 {frange(it['sub_start'], it['sub_end'])}에 진행되며, {conf}는 {won(p)}입니다. "
                + (f"보통 최소 청약 수량인 10주를 신청하면 증거금은 {won(mind)}이고, " if mind else "")
                + f"배정받지 못한 증거금은 {fd(it['refund'])}에 환불됩니다. "
                + (f"공모 주식 수는 {int(it['shares']):,}주, 공모 규모는 약 {eok(it.get('amount'))}입니다." if it.get("shares") else ""))
    if it.get("spac"):
        text += " 이 종목은 다른 회사와의 합병을 목적으로 상장하는 스팩(기업인수목적회사)입니다."
    calc = ""
    if p:
        calc = f"""<div class="box calc"><h3>청약 증거금 계산기</h3>
<label for="q">신청할 주식 수</label>
<div class="row"><input id="q" type="number" min="1" step="1" value="{MIN_SHARES}" inputmode="numeric"><span>주</span></div>
<p class="out">필요한 증거금 <b class="num" id="dep">{won(mind)}</b></p>
<p class="note">공모가 {won(p)} × 주식 수 × 증거금률 50%. 청약 수수료는 증권사마다 달라 포함하지 않았습니다.</p>
<script>(function(){{var q=document.getElementById('q'),o=document.getElementById('dep');q.addEventListener('input',function(){{var n=Math.max(0,parseInt(q.value||0,10));o.textContent=(Math.round(n*{p}*{DEPOSIT_RATE})).toLocaleString('ko-KR')+'원';}});}})();</script>
</div>"""
    body = f"""
<div class="crumb"><a href="/">청약 일정</a><span>›</span><span>{E(nm)}</span></div>
<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><h1>{E(nm)} 공모주 청약</h1>{badge(it['status'])}{'<span class="tag" style="margin:0">스팩</span>' if it.get('spac') else ''}</div>
<p class="lead">{E(text)}</p>
<div class="facts">
<div class="fact"><div class="k">청약일</div><div class="v num">{frange(it['sub_start'], it['sub_end'])}</div><div class="s">{it['sub_start'][:4] + '년' if it['sub_start'] else ''}</div></div>
<div class="fact"><div class="k">공모가</div><div class="v num">{won(p)}</div><div class="s">{'확정' if it.get('price_confirmed') else '희망가 · 수요예측 뒤 확정'}</div></div>
<div class="fact"><div class="k">최소 증거금</div><div class="v num">{won(mind)}</div><div class="s">10주 · 증거금률 50%</div></div>
<div class="fact"><div class="k">환불일</div><div class="v num">{fd(it['refund'])}</div><div class="s">미배정 증거금 반환</div></div>
</div>
<section class="two">
<div style="display:flex;flex-direction:column;gap:20px">
<div class="box"><h2>공모 개요</h2><dl class="kv">
<dt>공모 주식 수</dt><dd class="num">{format(int(it['shares']), ',') + '주' if it.get('shares') else '미정'}</dd>
<dt>공모 규모</dt><dd class="num">{eok(it.get('amount'))}</dd>
<dt>액면가</dt><dd class="num">{won(it.get('face'))}</dd>
<dt>공모 방법</dt><dd>{E(it.get('method') or '미정')}</dd>
<dt>주관사</dt><dd>{E(uw_text(it))}</dd>
</dl></div>
<div class="box"><h2>인수단 (청약 가능 증권사)</h2><ul class="uw">{uw_rows or '<li>공시에 아직 없습니다</li>'}</ul>
<p class="note">이 증권사들 가운데 한 곳에서만 청약할 수 있습니다. 같은 종목을 여러 증권사에서 중복 청약하면 먼저 접수된 한 건만 인정됩니다.</p></div>
<div class="box"><h2>관련 공시</h2><ul class="filings">{filings}</ul></div>
</div>
<div style="display:flex;flex-direction:column;gap:20px">
<div class="box"><h2>일정</h2><ul class="timeline">{timeline}</ul></div>
{calc}
<div class="box"><h3>더 알아보기</h3><div class="links" style="grid-template-columns:1fr">
<a href="/guide/equal-vs-proportional">균등배정과 비례배정<span>→</span></a>
<a href="/guide/deposit-refund">증거금과 환불일<span>→</span></a>
<a href="/guide/demand-forecast">수요예측 결과 읽는 법<span>→</span></a></div></div>
</div>
</section>
<p class="warn">이 페이지는 DART 공시({fd(it['filings'][-1]['date'][:4] + '-' + it['filings'][-1]['date'][4:6] + '-' + it['filings'][-1]['date'][6:], True) if it.get('filings') else ''} 기준)를 자동으로 정리한 것입니다. 청약 시간, 수수료, 계좌 조건은 증권사마다 다르니 청약 전 증권사 공지를 확인하세요. 투자 권유가 아닙니다.</p>
"""
    desc = (f"{nm} 공모주 청약일 {frange(it['sub_start'], it['sub_end'])}, 공모가 {won(p)}, 주관사 {uw_text(it)}, "
            f"최소 증거금 {won(mind)}, 환불일 {fd(it['refund'])}.")
    return page(ipo_url(it), f"{nm} 공모주 청약 일정·공모가·주관사", desc, body)


# ---------- 달력 ----------
def months_span(items, today):
    ds = [d(i["sub_start"]) for i in items if i["sub_start"]] + [d(i["refund"]) for i in items if i["refund"]] + [today]
    a, b = min(ds), max(ds)
    out, y, m = [], a.year, a.month
    while (y, m) <= (b.year, b.month):
        out.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def render_calendar(items, y, m, months, today, path):
    events = {}
    for it in items:
        s, e = d(it["sub_start"]), d(it["sub_end"] or it["sub_start"])
        if not s:
            continue
        cls = "wd" if it["status"] == "withdrawn" else "sub"
        x = s
        while x <= e:
            if x.weekday() < 5 or x in (s, e):
                events.setdefault(x, []).append((0, f'<a class="ev {cls}" href="{ipo_url(it)}" title="{E(it["name"])} 청약">{E(it["name"])}</a>'))
            x += timedelta(days=1)
        if it["refund"] and it["status"] != "withdrawn":
            events.setdefault(d(it["refund"]), []).append((1, f'<a class="ev ref" href="{ipo_url(it)}" title="{E(it["name"])} 환불">{E(it["name"])} 환불</a>'))
    cells = "".join(f'<div class="dow">{c}</div>' for c in "월화수목금토일")
    for wk in pycal.Calendar(0).monthdatescalendar(y, m):
        for x in wk:
            ev = "".join(h for _, h in sorted(events.get(x, []), key=lambda z: z[0]))
            cls = ["day"]
            if x.month != m:
                cls.append("out")
            if x == today:
                cls.append("today")
            if not ev:
                cls.append("none")
            cells += (f'<div class="{" ".join(cls)}"><span class="d" data-dow="({DOW[x.weekday()]})">'
                      f'{x.day if x.month == m else str(x.month) + "." + str(x.day)}{"" if x.month == m else ""}</span>{ev if x.month == m else ""}</div>')
    i = months.index((y, m))
    prev = months[i - 1] if i > 0 else None
    nxt = months[i + 1] if i + 1 < len(months) else None
    link = lambda ym, label: f'<a href="/calendar/{ym[0]}-{ym[1]:02d}" aria-label="{ym[0]}년 {ym[1]}월">{label}</a>' if ym else f'<span class="off">{label}</span>'
    n_sub = len({it["corp_code"] for it in items if it["sub_start"] and it["sub_start"][:7] == f"{y}-{m:02d}" and it["status"] != "withdrawn"})
    body = f"""
<h1>{y}년 {m}월 공모주 청약 달력</h1>
<p class="lead">{y}년 {m}월에 청약을 시작하는 공모주는 {n_sub}개입니다. 초록색은 청약일, 주황색은 증거금 환불일입니다. 종목을 누르면 공모가와 주관사를 볼 수 있습니다.</p>
<div class="cal-nav">{link(prev, '‹')}<span class="ym num">{y}.{m:02d}</span>{link(nxt, '›')}</div>
<div class="legend"><span><i style="background:var(--green-l)"></i>청약</span><span><i style="background:var(--amber-l)"></i>환불</span><span><i style="background:var(--red-l)"></i>철회</span></div>
<div class="cal">{cells}</div>
<p class="note">환불일과 다른 종목의 청약일이 같은 날이면, 돌려받은 증거금으로 바로 다음 청약을 할 수 있습니다. <a href="/guide/deposit-refund">자세히 보기</a></p>
"""
    return page(path, f"{y}년 {m}월 공모주 청약 일정 달력",
                f"{y}년 {m}월 공모주 청약일과 환불일을 달력으로 정리했습니다. 이번 달 청약 공모주 {n_sub}개.", body, "calendar")


# ---------- 증권사 ----------
def broker_map(items):
    out = {}
    for it in items:
        for u in it.get("underwriters") or []:
            n, slug = broker(u["name"])
            b = out.setdefault(slug, {"name": n, "items": []})
            if it not in b["items"]:
                b["items"].append(it)
    return out


def render_broker(slug, b):
    act = [i for i in b["items"] if i["status"] in ("subscribing", "upcoming")]
    past = [i for i in b["items"] if i not in act]
    n = b["name"]
    body = f"""
<div class="crumb"><a href="/broker">증권사별</a><span>›</span><span>{E(n)}</span></div>
<h1>{E(n)} 공모주 청약 일정</h1>
<p class="lead">{E(n)}에서 청약할 수 있는 공모주는 지금 {len(act)}개입니다. 대표 주관사뿐 아니라 인수단에 들어간 종목도 함께 모았습니다. 청약 전 {E(n)} 계좌가 있어야 합니다.</p>
<section><h2>청약 예정·진행 중</h2>{table(act) if act else '<div class="empty">지금은 예정된 청약이 없습니다.</div>'}</section>
{f'<section><h2>지난 청약</h2>{table(past, ("date", "name", "price", "status"))}</section>' if past else ''}
"""
    return page(f"/broker/{slug}", f"{n} 공모주 청약 일정",
                f"{n}에서 청약할 수 있는 공모주 일정. 지금 청약 예정·진행 중 {len(act)}개, 청약일·공모가·최소 증거금 정리.", body, "broker")


def render_broker_index(bm):
    rows = sorted(bm.items(), key=lambda kv: (-sum(1 for i in kv[1]["items"] if i["status"] in ("subscribing", "upcoming")), kv[1]["name"]))
    links = "".join(
        f'<a href="/broker/{s}">{E(b["name"])}<span>예정 {sum(1 for i in b["items"] if i["status"] in ("subscribing", "upcoming"))}개</span></a>'
        for s, b in rows)
    body = f"""
<h1>증권사별 공모주 청약 일정</h1>
<p class="lead">공모주는 주관사와 인수단에 들어간 증권사에서만 청약할 수 있습니다. 가지고 있는 계좌의 증권사를 눌러 청약 가능한 종목을 확인하세요.</p>
<section><div class="links">{links}</div></section>
<section class="prose"><h2>증권사 계좌, 어디부터 만들까</h2>
<p>최근 공모주를 가장 많이 맡은 곳은 대형 증권사지만, 청약자가 많이 몰리면 균등배정으로 받는 주식이 적어집니다. 인수단에만 들어간 증권사는 물량이 적은 대신 경쟁도 덜할 수 있습니다. 위 목록에서 예정된 종목 수를 비교해 보세요.</p></section>
"""
    return page("/broker", "증권사별 공모주 청약 일정", "한국투자증권, 미래에셋증권, 삼성증권, NH투자증권 등 증권사별로 청약할 수 있는 공모주 일정을 모았습니다.", body, "broker")


# ---------- 가이드·안내 ----------
def render_guides():
    out = {}
    lst = "".join(f'<a href="/guide/{g["slug"]}">{E(g["title"])}<span>→</span></a>' for g in GUIDES)
    out["guide"] = page("/guide", "공모주 청약 가이드", "공모주 청약 방법, 균등배정, 증거금과 환불, 수요예측, 스팩, 상장일 규칙까지 처음 하는 사람을 위한 안내.",
                        f'<h1>공모주 청약 가이드</h1><p class="lead">공모주를 처음 청약하는 사람이 알아야 할 것들을 정리했습니다.</p><section><div class="links" style="grid-template-columns:1fr">{lst}</div></section>', "guide")
    for i, g in enumerate(GUIDES):
        others = "".join(f'<a href="/guide/{o["slug"]}">{E(o["title"])}<span>→</span></a>' for o in GUIDES if o is not g)
        body = f"""<div class="crumb"><a href="/guide">가이드</a><span>›</span><span>{E(g['title'].split(':')[0])}</span></div>
<article class="prose" style="max-width:760px"><h1>{E(g['title'])}</h1><p class="lead" style="margin-bottom:28px">{E(g['desc'])}</p>{g['body']}</article>
<section style="max-width:760px"><div class="links" style="grid-template-columns:1fr"><a href="/">이번 주 공모주 청약 일정 보기<span>→</span></a></div></section>
<section style="max-width:760px"><h2>다른 가이드</h2><div class="links" style="grid-template-columns:1fr">{others}</div></section>"""
        out[f"guide/{g['slug']}"] = page(f"/guide/{g['slug']}", g["title"], g["desc"], body, "guide")
    return out


def render_static_pages():
    about = f"""<h1>공모주데이 소개</h1><div class="prose" style="max-width:760px;margin-top:20px">
<p>공모주데이는 공모주 청약 일정을 한곳에서 보기 쉽게 정리한 무료 사이트입니다. 청약일, 공모가, 주관 증권사, 최소 증거금, 환불일을 종목마다 한 페이지에 모았습니다.</p>
<h2>데이터는 어디서 오나요</h2>
<p>모든 정보는 금융감독원 전자공시시스템(DART)의 공개 API에서 가져옵니다. 증권신고서, 투자설명서, 발행조건확정 공시, 철회신고서를 1시간마다 확인해 자동으로 갱신합니다. 각 종목 페이지 아래에 공시 원문 링크가 있습니다.</p>
<h2>무엇을 하지 않나요</h2>
<p>공모주데이는 특정 종목을 추천하거나 투자를 권하지 않습니다. 증권사를 대신해 청약을 받지 않으며, 개인정보나 계좌 정보를 요구하지 않습니다.</p>
<h2>정보가 틀렸다면</h2>
<p>자동 수집이라 공시 정정이 늦게 반영되거나 형식이 다른 공시를 잘못 읽을 수 있습니다. 틀린 부분을 발견하면 <a href="/contact">문의</a>로 알려 주세요.</p></div>"""
    privacy = f"""<h1>개인정보처리방침</h1><div class="prose" style="max-width:760px;margin-top:20px">
<p>공모주데이(이하 '사이트')는 회원가입 없이 이용할 수 있으며, 이름·연락처·계좌 등 개인정보를 직접 수집하지 않습니다.</p>
<h2>자동으로 수집되는 정보</h2>
<p>사이트를 운영하는 호스팅 서비스(Cloudflare)는 보안과 서비스 제공을 위해 접속 IP, 브라우저 종류, 접속 시각 같은 기술 정보를 기록할 수 있습니다.</p>
<h2>광고와 쿠키</h2>
<p>사이트는 Google 애드센스 광고를 게재할 수 있습니다. Google을 포함한 제3자 광고 사업자는 쿠키를 사용해 이용자가 이 사이트나 다른 사이트를 방문한 기록을 바탕으로 광고를 보여 줄 수 있습니다. 이용자는 <a href="https://www.google.com/settings/ads" rel="nofollow noopener" target="_blank">Google 광고 설정</a>에서 맞춤 광고를 끌 수 있고, <a href="https://www.aboutads.info" rel="nofollow noopener" target="_blank">aboutads.info</a>에서 다른 광고 사업자의 맞춤 광고도 끌 수 있습니다. 브라우저 설정에서 쿠키를 거부할 수도 있습니다.</p>
<h2>문의</h2><p>개인정보와 관련한 문의는 {CONTACT} 로 보내 주세요.</p>
<p>시행일: 2026년 11월 9일</p></div>"""
    contact = f"""<h1>문의</h1><div class="prose" style="max-width:760px;margin-top:20px">
<p>잘못된 일정, 빠진 종목, 제안이 있으면 이메일로 알려 주세요. 종목명과 내용을 함께 적어 주시면 빠르게 확인하겠습니다.</p>
<p style="font-size:20px;font-weight:700"><a href="mailto:{CONTACT}">{CONTACT}</a></p>
<p>개별 종목의 투자 상담이나 청약 대행 요청에는 답변하지 않습니다. 청약 관련 문의는 해당 증권사 고객센터로 해 주세요.</p></div>"""
    nf = '<h1>페이지를 찾을 수 없습니다</h1><p class="lead">주소가 바뀌었거나 목록에서 빠진 종목일 수 있습니다.</p><section><div class="links"><a href="/">공모주 청약 일정<span>→</span></a><a href="/calendar">청약 달력<span>→</span></a></div></section>'
    return {
        "about": page("/about", "공모주데이 소개", "공모주데이는 DART 공시를 바탕으로 공모주 청약 일정을 정리하는 무료 사이트입니다.", about),
        "privacy": page("/privacy", "개인정보처리방침", "공모주데이 개인정보처리방침과 광고 쿠키 안내.", privacy),
        "contact": page("/contact", "문의", "공모주데이 문의 방법.", contact),
        "404": page("/404", "페이지를 찾을 수 없습니다", "요청한 페이지가 없습니다.", nf, noindex=True),
    }


# ---------- 전체 ----------
def render_all(data, out):
    items = data["items"]
    updated_iso = data["updated"]
    now = datetime.fromisoformat(updated_iso)
    today = now.date()
    updated = f"{now.year}.{now.month}.{now.day} {now.hour:02d}:{now.minute:02d}"
    pages = {"index": render_home(items, today, updated)}
    for it in items:
        pages[f"ipo/{it['corp_code']}"] = render_ipo(it, today)
    months = months_span(items, today)
    for (y, m) in months:
        pages[f"calendar/{y}-{m:02d}"] = render_calendar(items, y, m, months, today, f"/calendar/{y}-{m:02d}")
    pages["calendar"] = render_calendar(items, today.year, today.month, months, today, "/calendar")
    bm = broker_map(items)
    for slug, b in bm.items():
        pages[f"broker/{slug}"] = render_broker(slug, b)
    pages["broker"] = render_broker_index(bm)
    pages.update(render_guides())
    pages.update(render_static_pages())

    static = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    if os.path.isdir(out):
        shutil.rmtree(out)
    shutil.copytree(static, out)
    for k, html in pages.items():
        p = os.path.join(out, k + ".html")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(html)
    skip = {"404", "calendar"}
    urls = []
    for k in pages:
        if k in skip:
            continue
        loc = "/" if k == "index" else "/" + k
        pri = "1.0" if k == "index" else ("0.8" if k.startswith("ipo/") else "0.6")
        urls.append(f"<url><loc>{SITE}{loc}</loc><lastmod>{today.isoformat()}</lastmod><priority>{pri}</priority></url>")
    urls.insert(1, f"<url><loc>{SITE}/calendar</loc><lastmod>{today.isoformat()}</lastmod><priority>0.9</priority></url>")
    with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")
    return len(pages)


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    print("pages:", render_all(data, out))
