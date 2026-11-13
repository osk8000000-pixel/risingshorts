"""돈챙김 정적 사이트 생성기.

사용: python money/render.py <services.json> <출력 폴더>
ipo/공모주데이와 같은 방식: static 폴더를 복사하고 HTML 과 sitemap.xml 을 만든다.
금리는 저장하지 않고 /api/rates(Pages Function)에서 방문할 때 받아 온다.
"""
import json
import os
import shutil
import sys
from datetime import date, datetime
from html import escape as E

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from guides import GUIDES  # noqa: E402
from collector import TARGETS  # noqa: E402

SITE = "https://donchaengim.com"
NAME = "돈챙김"
CONTACT = "risingshorts.help@gmail.com"
ADSENSE = "ca-pub-2895025957691898"
DOW = "월화수목금토일"
REGIONS = [("서울", "seoul"), ("경기", "gyeonggi"), ("인천", "incheon"), ("부산", "busan"), ("대구", "daegu"),
           ("전남·광주", "gwangju-jeonnam"), ("대전", "daejeon"), ("울산", "ulsan"), ("세종", "sejong"), ("강원", "gangwon"),
           ("충북", "chungbuk"), ("충남", "chungnam"), ("전북", "jeonbuk"), ("경북", "gyeongbuk"), ("경남", "gyeongnam"),
           ("제주", "jeju")]
TNAME = {s: n for s, n, _ in TARGETS}
ICON = ('<svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><rect width="30" height="30" rx="15" fill="#0C9A6A"/>'
        '<path d="M9 12.5c0-2 2.7-3.5 6-3.5s6 1.5 6 3.5-2.7 3.5-6 3.5-6 1.5-6 3.5 2.7 3.5 6 3.5 6-1.5 6-3.5" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>'
        '<path d="M15 6.5v17" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/></svg>')
NAV = [("/", "home", "홈"), ("/support", "support", "지원금"), ("/deadline", "deadline", "마감 임박"),
       ("/rates", "rates", "금리 비교"), ("/guide", "guide", "가이드")]


def d(s):
    return date.fromisoformat(s) if s else None


def fd(s, year=False):
    x = d(s)
    if not x:
        return ""
    return (f"{x.year}." if year else "") + f"{x.month}.{x.day}({DOW[x.weekday()]})"


def josa(word, a, b):
    ch = (word or " ")[-1]
    if "가" <= ch <= "힣":
        return a if (ord(ch) - 0xAC00) % 28 else b
    return b


def page(path, title, desc, body, nav="", noindex=False, scripts=""):
    url = SITE + path
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
<meta name="theme-color" content="#0C9A6A">
<link rel="icon" href="/assets/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=Inter:wght@500;700;800&display=swap" rel="stylesheet">
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE}" crossorigin="anonymous"></script>
<script>if(location.hostname.endsWith('.pages.dev'))location.replace('{SITE}'+location.pathname+location.search+location.hash);</script>
<link rel="stylesheet" href="/assets/style.css?v=1">
</head>
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
<p>돈챙김은 행정안전부 '대한민국 공공서비스(혜택) 정보'와 금융감독원 금융상품통합비교공시 정보를 바탕으로 지원금과 예적금 금리를 정리합니다. 자격과 금액은 바뀔 수 있으니 신청·가입 전 공식 안내와 금융회사에서 꼭 확인하세요.</p>
<p>정보 제공용이며 투자·금융상품 가입을 권유하지 않습니다. © {date.today().year} {NAME}</p>
</div></footer>
{scripts}</body>
</html>
"""


# ---------- 지원금 조각 ----------
def s_url(it):
    return f"/support/{it['id']}"


def dday(it, today):
    if it.get("open_now") and it.get("dl_end"):
        n = (d(it["dl_end"]) - today).days
        return ("오늘 마감" if n == 0 else f"D-{n}"), ("hot" if n <= 7 else "soon")
    if it.get("dl_start") and it["dl_start"] > today.isoformat():
        return f"{fd(it['dl_start'])} 시작", "far"
    dl = it.get("deadline") or ""
    if "상시" in dl or "연중" in dl or "수시" in dl:
        return "상시", "far"
    return "", ""


def kind_txt(k):
    return " · ".join(dict.fromkeys(x.strip() for x in (k or "").split("||") if x.strip()))


def scard(it, today):
    bt, bc = dday(it, today)
    badge = f'<span class="b {bc}">{E(bt)}</span>' if bt else '<span></span>'
    pills = [f'<span class="pill">{E(it["region"])}</span>']
    if it.get("kind"):
        pills.append(f'<span class="pill g">{E(kind_txt(it["kind"]))}</span>')
    end = f"~{fd(it['dl_end'])}" if it.get("open_now") and it.get("dl_end") else ""
    return f"""<a class="icard" href="{s_url(it)}">
<div class="row">{badge}<span class="dt">{E(it['field'])}</span></div>
<div class="nm" style="font-size:19px">{E(it['name'])}</div>
<div style="font-size:14.5px;color:var(--ink2);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">{E(it['summary'])}</div>
<div class="pills">{''.join(pills)}</div>
<div class="ft"><span>{E(it['org'])}</span><span class="num">{end}</span></div></a>"""


def grid(items, today):
    return '<div class="igrid">' + "".join(scard(i, today) for i in items) + "</div>" if items else '<div class="empty">해당하는 지원금이 없어요.</div>'


def links_targets(items):
    cnt = {s: 0 for s, _, _ in TARGETS}
    for it in items:
        for t in it["targets"]:
            cnt[t] += 1
    return '<div class="rlist">' + "".join(f'<a href="/target/{s}">{E(n)}<span>{cnt[s]:,}개</span></a>' for s, n, _ in TARGETS) + "</div>"


def links_regions(items):
    cnt = {}
    for it in items:
        cnt[it["region"]] = cnt.get(it["region"], 0) + 1
    return '<div class="rlist">' + "".join(f'<a href="/region/{s}">{E(n)}<span>{cnt.get(n, 0):,}개</span></a>' for n, s in REGIONS if cnt.get(n)) + "</div>"


# ---------- 페이지 ----------
def render_home(items, today, updated):
    t = today.isoformat()
    open_ = sorted([i for i in items if i["open_now"] and i["page"]], key=lambda x: (x["dl_end"], -x["views"]))
    month_end = [i for i in open_ if i["dl_end"][:7] == t[:7]]
    popular = [i for i in items if i["region"] == "전국" and i["page"]][:12]
    first = open_[0] if open_ else None
    sub = (f"마감이 가장 가까운 지원금은 <a href=\"{s_url(first)}\">{E(first['name'])}</a>, {fd(first['dl_end'])}까지예요."
           if first else "지금 신청할 수 있는 지원금을 모았어요.")
    body = f"""
<section class="hello">
<div><p class="eyebrow">지원금 · 예적금 금리 · {fd(t)}</p><h1>지금 신청할 수 있는 지원금<br><em>{len(open_)}개</em>를 찾았어요</h1><p class="sub">{sub}</p></div>
<div class="sum"><div><b class="num">{len(open_)}</b><small>접수 중</small></div><div><b class="num">{len(month_end)}</b><small>이번 달 마감</small></div><div><b class="num" id="sum-rate">-</b><small>최고 예금금리</small></div></div>
</section>
<section><div class="sec-head"><h2>마감 임박 지원금</h2><a href="/deadline">전체 보기 →</a></div>{grid(open_[:9], today)}</section>
<section><div class="sec-head"><h2>오늘의 최고 금리</h2><a href="/rates">금리 비교 전체 →</a></div>
<div class="mini" id="mini-deposit"><div class="skel" style="border-radius:20px"></div><div class="skel" style="border-radius:20px"></div><div class="skel" style="border-radius:20px"></div></div>
<div class="mini" id="mini-saving" style="margin-top:12px"></div>
<p class="src">금융감독원 금융상품통합비교공시 금융회사 상품정보를 방문할 때마다 바로 받아 보여 줍니다. 우대 조건을 모두 채웠을 때의 금리예요.</p></section>
<section><h2>누구를 위한 지원금?</h2>{links_targets(items)}</section>
<section><div class="sec-head"><h2>많이 찾는 전국 지원금</h2><a href="/support">인기 순위 →</a></div>{grid(popular, today)}</section>
<section><h2>우리 지역 지원금</h2>{links_regions(items)}</section>
<section><h2>알아두면 돈이 되는 글</h2><div class="links">{''.join(f'<a href="/guide/{g["slug"]}">{E(g["title"])}<span>→</span></a>' for g in GUIDES[:4])}</div>
<p class="note">지원금 정보 갱신 {E(updated)} · 행정안전부 공공서비스(혜택) 정보 기준</p></section>
"""
    js = ('<script src="/assets/rates.js?v=1" defer></script>'
          '<script>addEventListener("load",function(){fetch("/api/rates?kind=deposit").then(r=>r.json()).then(function(d){var m=0;(d.items||[]).forEach(function(p){p.opts.forEach(function(o){if(o.t===12)m=Math.max(m,Number(o.r2||o.r||0))})});if(m)document.getElementById("sum-rate").textContent=m.toFixed(2)+"%"}).catch(function(){})});</script>')
    return page("/", f"{NAME} | 지금 받을 수 있는 정부 지원금·예적금 최고 금리",
                f"지금 신청할 수 있는 정부·지자체 지원금 {len(open_)}개와 마감일, 은행·저축은행 예적금 최고 금리를 한곳에서. 받을 돈과 불릴 돈을 챙기세요.",
                body, "home", scripts=js)


def render_detail(it, items, today):
    bt, bc = dday(it, today)
    pills = [f'<span class="pill">{E(it["region"])}</span>', f'<span class="pill">{E(it["field"])}</span>']
    if it.get("kind"):
        pills.append(f'<span class="pill g">{E(kind_txt(it["kind"]))}</span>')
    for t in it["targets"][:3]:
        pills.append(f'<a class="pill b" href="/target/{t}" style="text-decoration:none">{E(TNAME[t])}</a>')
    nm, org = it["name"], it["org"]
    lead = f"{nm}{josa(nm, '은', '는')} {org}에서 운영하는 {it['field']} 분야 지원"
    lead += f"({kind_txt(it['kind'])})입니다." if it.get("kind") else "입니다."
    if it.get("open_now") and it.get("dl_end"):
        lead += f" 지금 신청할 수 있고 {fd(it['dl_end'], True)}에 마감됩니다."
    elif it.get("deadline") and len(it["deadline"]) <= 30 and "\n" not in it["deadline"]:
        lead += f" 신청 기한은 '{it['deadline'].strip('○ ')}'입니다."

    def sec(title, txt):
        return f'<div class="sec"><h2>{title}</h2><div class="txt">{E(txt)}</div></div>' if txt and txt.strip() not in ("", "-", "해당없음") else ""

    rel = [x for x in items if x["page"] and x["id"] != it["id"] and
           (set(x["targets"]) & set(it["targets"]) or x["field"] == it["field"]) and x["region"] in ("전국", it["region"])][:6]
    ctas = ""
    if it.get("online_url", "").startswith("http"):
        ctas += f'<a class="cta" href="{E(it["online_url"])}" rel="nofollow noopener" target="_blank">온라인 신청하러 가기 ↗</a>'
    if it.get("gov_url", "").startswith("http"):
        ctas += f'<a class="cta ghost" href="{E(it["gov_url"])}" rel="nofollow noopener" target="_blank">정부 공식 안내 보기 ↗</a>'
    facts = [("신청 기한", it.get("deadline") or "공식 안내 확인"), ("접수 기관", it.get("reception") or org),
             ("문의처", it.get("contact") or "-"), ("운영 기관", f"{org} {it.get('dept') or ''}".strip())]
    kv = "".join(f"<dt>{k}</dt><dd>{E(v)}</dd>" for k, v in facts)
    body = f"""
<div class="crumb"><a href="/">홈</a><span>›</span><a href="/support">지원금</a><span>›</span><span>{E(nm)}</span></div>
<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">{f'<span class="b {bc}">{E(bt)}</span>' if bt else ''}<div class="pills">{''.join(pills)}</div></div>
<h1 style="margin-top:10px">{E(nm)}</h1>
<p class="lead">{E(lead)}</p>
<div class="ctas">{ctas}</div>
<section class="two" style="margin-top:24px">
<div>
{sec("한눈에 보기", it.get("summary"))}
{sec("지원 대상", it.get("target"))}
{sec("선정 기준", it.get("criteria"))}
{sec("지원 내용", it.get("benefit"))}
{sec("신청 방법", it.get("how"))}
{sec("구비 서류", it.get("docs"))}
</div>
<div style="display:flex;flex-direction:column;gap:16px">
<div class="box"><h2>신청 정보</h2><dl class="kv">{kv}</dl></div>
<div class="box"><h3>더 알아보기</h3><div class="links" style="grid-template-columns:1fr">
<a href="/guide/find-support">지원금 찾고 신청하는 법<span>→</span></a><a href="/guide/median-income">기준 중위소득이란?<span>→</span></a><a href="/rates">예적금 최고 금리 보기<span>→</span></a></div></div>
</div></section>
{f'<section><h2>비슷한 지원금</h2>{grid(rel, today)}</section>' if rel else ''}
<p class="warn">이 페이지는 행정안전부 '대한민국 공공서비스(혜택) 정보'(수정일 {it.get('updated', '')[:4]}.{it.get('updated', '')[4:6]}.{it.get('updated', '')[6:8]})를 정리한 것입니다. 자격·금액·기한은 바뀔 수 있으니 신청 전 공식 안내와 문의처에서 꼭 확인하세요.</p>
"""
    desc = f"{nm} — {it['summary'][:90]} 신청 기한: {(it.get('deadline') or '공식 안내 확인')[:40]}"
    return page(s_url(it), f"{nm} 신청 방법·대상·기한", desc, body, "support")


def render_list(path, title, h1, lead, its, today, nav="support", extra=""):
    body = f"""<h1>{E(h1)}</h1><p class="lead">{lead}</p>{extra}<section>{grid(its, today)}</section>"""
    return page(path, title, lead[:150], body, nav)


def render_deadline(items, today):
    t = today.isoformat()
    open_ = sorted([i for i in items if i["open_now"] and i["page"]], key=lambda x: (x["dl_end"], -x["views"]))
    soon = sorted([i for i in items if i["dl_start"] and i["dl_start"] > t and i["page"]], key=lambda x: x["dl_start"])
    week = [i for i in open_ if (d(i["dl_end"]) - today).days <= 7]
    rest = [i for i in open_ if i not in week]
    body = f"""<h1>마감 임박 지원금</h1>
<p class="lead">신청 기간이 정해진 지원금 가운데 지금 접수 중인 {len(open_)}개를 마감이 가까운 순서로 모았어요. 마감이 지나면 다음 공고까지 기다려야 하니 미리 챙기세요.</p>
<section><h2>7일 안에 마감 ({len(week)}개)</h2>{grid(week, today)}</section>
<section><h2>그 뒤에 마감 ({len(rest)}개)</h2>{grid(rest, today)}</section>
{f'<section><h2>곧 접수 시작 ({len(soon)}개)</h2>{grid(soon, today)}</section>' if soon else ''}
<p class="note">'상시신청' 지원금은 언제든 신청할 수 있어 이 목록에 넣지 않았어요. <a href="/support">전체 지원금 보기</a></p>"""
    return page("/deadline", "마감 임박 정부 지원금 — 지금 신청 가능", f"지금 접수 중인 정부·지자체 지원금 {len(open_)}개를 마감일 순으로 정리했습니다. 7일 안에 마감되는 지원금 {len(week)}개.", body, "deadline")


def render_support(items, today):
    top = [i for i in items if i["page"]][:120]
    fields = {}
    for i in items:
        fields[i["field"]] = fields.get(i["field"], 0) + 1
    body = f"""<h1>인기 지원금 순위</h1>
<p class="lead">정부·지자체 지원 서비스 {len(items):,}개 가운데 많이 찾는 순서로 120개를 골랐어요. 나에게 맞는 지원금은 대상별·지역별 목록에서 더 빨리 찾을 수 있어요.</p>
<section><h2>대상별</h2>{links_targets(items)}</section>
<section><h2>지역별</h2>{links_regions(items)}</section>
<section><h2>많이 찾는 지원금</h2>{grid(top, today)}</section>
<p class="note">분야별 개수: {E(', '.join(f'{k} {v:,}' for k, v in sorted(fields.items(), key=lambda kv: -kv[1])))}</p>"""
    return page("/support", "인기 정부 지원금 순위·대상별·지역별 찾기", f"정부·지자체 지원 서비스 {len(items):,}개 중 많이 찾는 지원금 순위와 청년·어르신·출산·주거 등 대상별, 지역별 지원금 목록.", body, "support")


def render_rates():
    body = """<h1>예적금 금리 비교</h1>
<p class="lead">은행과 저축은행의 정기예금·적금 금리를 금융감독원 공시에서 바로 받아 높은 순서로 보여 드려요. '최고 금리'는 우대 조건을 모두 채웠을 때, '기본 금리'는 조건 없이 받는 금리예요.</p>
<section>
<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
<div class="tabs" role="tablist"><button class="tab" data-kind="deposit">정기예금</button><button class="tab" data-kind="saving">적금</button></div>
<div class="tabs"><button class="tab" data-term="6">6개월</button><button class="tab" data-term="12">12개월</button><button class="tab" data-term="24">24개월</button><button class="tab" data-term="36">36개월</button></div>
<div class="tabs"><button class="tab" data-group="all">전체</button><button class="tab" data-group="bank">은행</button><button class="tab" data-group="savings">저축은행</button></div>
</div>
<div class="rates" id="rate-box" style="margin-top:14px"></div>
<p class="src" id="rate-src">금융감독원 금융상품통합비교공시 금융회사 상품정보를 사용한 결과입니다.</p>
</section>
<section class="box"><h2>세후 이자 계산기</h2>
<form id="calc" class="calc2" onsubmit="return false">
<div><label>상품</label><select name="kind"><option value="deposit">정기예금 (목돈 한 번에)</option><option value="saving">적금 (매달 같은 금액)</option></select></div>
<div><label id="c-amt-l">맡길 돈 (원)</label><input name="amt" inputmode="numeric" value="10000000"></div>
<div><label>연 금리 (%)</label><input name="rate" inputmode="decimal" value="3.5"></div>
<div><label>기간 (개월)</label><input name="mon" inputmode="numeric" value="12"></div>
</form>
<div class="calc-out"><div><small>세전 이자</small><b id="c-int">-</b></div><div><small>세금 (15.4%)</small><b id="c-tax">-</b></div><div class="main"><small>만기에 받는 돈</small><b id="c-total">-</b></div></div>
<p class="note">단리 기준 어림값이에요. 실제 금액은 금융회사의 이자 계산 방식(복리, 일할 계산)과 우대 조건에 따라 달라요. <a href="/guide/deposit-vs-saving">예금과 적금 이자가 다른 이유</a></p>
</section>
<section class="prose" style="max-width:760px"><h2>금리 비교할 때 꼭 볼 것</h2>
<p>최고 금리와 기본 금리의 차이가 큰 상품은 우대 조건(급여 이체, 카드 실적 등)을 채워야 높은 금리를 받을 수 있어요. 각 상품의 '가입 조건·우대 조건 보기'를 눌러 내가 채울 수 있는 조건인지 확인하세요. 저축은행 예금도 1인당 1억 원까지 예금자보호를 받아요. <a href="/guide/deposit-protection">예금자보호 자세히</a></p></section>
"""
    return page("/rates", "예금·적금 최고 금리 비교 (은행·저축은행)", "은행·저축은행 정기예금과 적금 금리를 금융감독원 공시로 바로 비교. 6·12·24·36개월 기간별 최고 금리 순위와 세후 이자 계산기.",
                body, "rates", scripts='<script src="/assets/rates.js?v=1" defer></script>')


def render_guides():
    out = {}
    lst = "".join(f'<a href="/guide/{g["slug"]}">{E(g["title"])}<span>→</span></a>' for g in GUIDES)
    out["guide"] = page("/guide", "지원금·예적금 가이드", "정부 지원금 찾는 법, 기준 중위소득, 예금과 적금 이자 차이, 우대금리, 예금자보호까지 돈 챙기는 법.",
                        f'<h1>돈 챙기는 가이드</h1><p class="lead">지원금과 예적금을 처음 챙기는 분을 위해 꼭 알아야 할 것들을 정리했어요.</p><section><div class="links" style="grid-template-columns:1fr">{lst}</div></section>', "guide")
    for g in GUIDES:
        others = "".join(f'<a href="/guide/{o["slug"]}">{E(o["title"])}<span>→</span></a>' for o in GUIDES if o is not g)
        body = f"""<div class="crumb"><a href="/guide">가이드</a><span>›</span><span>{E(g['title'])}</span></div>
<article class="prose" style="max-width:760px"><h1>{E(g['title'])}</h1><p class="lead" style="margin-bottom:28px">{E(g['desc'])}</p>{g['body']}</article>
<section style="max-width:760px"><div class="links" style="grid-template-columns:1fr"><a href="/deadline">마감 임박 지원금 보기<span>→</span></a><a href="/rates">예적금 최고 금리 보기<span>→</span></a></div></section>
<section style="max-width:760px"><h2>다른 가이드</h2><div class="links" style="grid-template-columns:1fr">{others}</div></section>"""
        out[f"guide/{g['slug']}"] = page(f"/guide/{g['slug']}", g["title"], g["desc"], body, "guide")
    return out


def render_static_pages():
    about = """<h1>돈챙김 소개</h1><div class="prose" style="max-width:760px;margin-top:20px">
<p>돈챙김은 '받을 돈'과 '불릴 돈'을 한곳에서 챙길 수 있게 만든 무료 사이트입니다. 정부·지자체 지원금과 은행·저축은행 예적금 금리를 보기 쉽게 정리합니다.</p>
<h2>데이터는 어디서 오나요</h2>
<p>지원금은 행정안전부가 공공데이터포털로 공개하는 '대한민국 공공서비스(혜택) 정보'를 하루 여러 번 받아 정리합니다. 예적금 금리는 금융감독원 금융상품통합비교공시 오픈API에서 방문할 때마다 바로 받아 보여 주며, 금리 정보를 따로 저장하지 않습니다.</p>
<h2>무엇을 하지 않나요</h2>
<p>신청이나 가입을 대행하지 않고, 개인정보를 받지 않습니다. 특정 금융상품을 추천하거나 가입을 권하지 않습니다.</p>
<h2>정보가 틀렸다면</h2>
<p>자동으로 정리하다 보니 공식 정보와 다르게 보일 수 있습니다. 틀린 부분은 <a href="/contact">문의</a>로 알려 주세요.</p></div>"""
    privacy = f"""<h1>개인정보처리방침</h1><div class="prose" style="max-width:760px;margin-top:20px">
<p>돈챙김(이하 '사이트')은 회원가입 없이 이용할 수 있으며, 이름·연락처·계좌 등 개인정보를 직접 수집하지 않습니다.</p>
<h2>자동으로 수집되는 정보</h2><p>사이트를 운영하는 호스팅 서비스(Cloudflare)는 보안과 서비스 제공을 위해 접속 IP, 브라우저 종류, 접속 시각 같은 기술 정보를 기록할 수 있습니다.</p>
<h2>광고와 쿠키</h2><p>사이트는 Google 애드센스 광고를 게재할 수 있습니다. Google을 포함한 제3자 광고 사업자는 쿠키를 사용해 이용자가 이 사이트나 다른 사이트를 방문한 기록을 바탕으로 광고를 보여 줄 수 있습니다. 이용자는 <a href="https://www.google.com/settings/ads" rel="nofollow noopener" target="_blank">Google 광고 설정</a>에서 맞춤 광고를 끌 수 있고, <a href="https://www.aboutads.info" rel="nofollow noopener" target="_blank">aboutads.info</a>에서 다른 광고 사업자의 맞춤 광고도 끌 수 있습니다.</p>
<h2>문의</h2><p>개인정보와 관련한 문의는 {CONTACT} 로 보내 주세요.</p><p>시행일: 2026년 11월 13일</p></div>"""
    contact = f"""<h1>문의</h1><div class="prose" style="max-width:760px;margin-top:20px">
<p>잘못된 정보, 빠진 지원금, 제안이 있으면 이메일로 알려 주세요.</p>
<p style="font-size:20px;font-weight:700"><a href="mailto:{CONTACT}">{CONTACT}</a></p>
<p>개별 지원금의 자격 판정이나 금융상품 상담에는 답변하지 않습니다. 해당 기관이나 금융회사로 문의해 주세요.</p></div>"""
    nf = '<h1>페이지를 찾을 수 없습니다</h1><p class="lead">지원금 목록에서 빠졌거나 주소가 바뀌었을 수 있어요.</p><section><div class="links"><a href="/support">지원금 찾기<span>→</span></a><a href="/rates">금리 비교<span>→</span></a></div></section>'
    return {
        "about": page("/about", "돈챙김 소개", "돈챙김은 공공 데이터를 바탕으로 정부 지원금과 예적금 금리를 정리하는 무료 사이트입니다.", about),
        "privacy": page("/privacy", "개인정보처리방침", "돈챙김 개인정보처리방침과 광고 쿠키 안내.", privacy),
        "contact": page("/contact", "문의", "돈챙김 문의 방법.", contact),
        "404": page("/404", "페이지를 찾을 수 없습니다", "요청한 페이지가 없습니다.", nf, noindex=True),
    }


def render_all(data, out):
    items = data["items"]
    now = datetime.fromisoformat(data["updated"])
    today = now.date()
    updated = f"{now.year}.{now.month}.{now.day} {now.hour:02d}:{now.minute:02d}"
    pages = {"index": render_home(items, today, updated), "deadline": render_deadline(items, today),
             "support": render_support(items, today), "rates": render_rates()}
    for it in items:
        if it["page"]:
            pages[f"support/{it['id']}"] = render_detail(it, items, today)
    for slug, nm, _ in TARGETS:
        its = [i for i in items if slug in i["targets"] and i["page"]][:150]
        pages[f"target/{slug}"] = render_list(f"/target/{slug}", f"{nm} 지원금 모음 — 신청 대상·방법", f"{nm} 지원금",
                                              f"{nm}을 위한 정부·지자체 지원금을 많이 찾는 순서로 {len(its)}개 모았어요. 각 지원금을 누르면 대상, 선정기준, 신청 방법, 마감일을 볼 수 있어요.", its, today)
    reg_idx = links_regions(items)
    pages["region"] = page("/region", "지역별 지원금 — 우리 동네 지원금 찾기", "서울·경기·부산 등 시도별로 우리 동네 지자체 지원금을 모았습니다.",
                           f'<h1>지역별 지원금</h1><p class="lead">시·군·구가 운영하는 지원금은 그 지역 주민만 받을 수 있어요. 사는 곳을 골라 보세요.</p><section>{reg_idx}</section>', "support")
    for nm, slug in REGIONS:
        its = [i for i in items if i["region"] == nm and i["page"]][:150]
        pages[f"region/{slug}"] = render_list(f"/region/{slug}", f"{nm} 지원금 모음 — 시·군·구 지원 혜택", f"{nm} 지원금",
                                              f"{nm} 지역 시·군·구가 운영하는 지원금을 많이 찾는 순서로 {len(its)}개 모았어요. 전국 공통 지원금은 <a href='/support'>지원금 순위</a>에서 볼 수 있어요.", its, today,
                                              extra=f'<section><div class="rlist">{"".join(f"<a href=/region/{s}>{E(n)}</a>" for n, s in REGIONS)}</div></section>')
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
    urls = []
    for k in pages:
        if k == "404":
            continue
        loc = "/" if k == "index" else "/" + k
        pri = "1.0" if k == "index" else ("0.6" if k.startswith("support/") else "0.8")
        urls.append(f"<url><loc>{SITE}{loc}</loc><lastmod>{today.isoformat()}</lastmod><priority>{pri}</priority></url>")
    with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")
    return len(pages)


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    print("pages:", render_all(data, sys.argv[2]))
