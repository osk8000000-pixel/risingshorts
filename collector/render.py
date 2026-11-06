"""완성된 HTML 페이지 만들기.

브라우저가 데이터를 받아 그리기 전에도 순위가 보이도록(네이버 검색 로봇·느린 휴대폰 대비),
templates/*.html 틀의 <!--@이름--> 자리에 순위 내용을 채워 site/ 에 씁니다.
화면이 열린 뒤에는 assets/app.js 가 같은 내용을 다시 그리며 정렬·필터를 붙입니다.
"""
import html
import math
import os
import re
from datetime import datetime, timedelta, timezone

import config

SITE = "https://risingshorts.com"
KST = timezone(timedelta(hours=9))
RNAME = {"kr": "국내", "us": "해외"}

# 카테고리 소개 글 (검색엔진·방문자용 설명)
CAT_INTRO = {
    "dog": "반려견 일상, 훈련, 견종별 반응처럼 강아지가 주인공인 쇼츠를 모았어요. 짧은 상황극과 '왜 그랬을까' 형식의 제목이 특히 빠르게 퍼지는 분야예요.",
    "gaming": "롤·발로란트·배그·메이플스토리 같은 게임의 하이라이트와 밈 쇼츠예요. 프로 경기 명장면과 웃긴 실수 장면이 하루 안에 크게 뜨는 경우가 많아요.",
    "cat": "고양이와 아기 고양이의 반응, 집사 일상 쇼츠예요. 대사 없이도 통하는 영상이 많아 국내 영상이 해외에서도 함께 뜨는 일이 잦아요.",
    "mukbang": "먹방, 맛집 소개, 편의점 신상 리뷰 쇼츠예요. 음식 이름이 제목 맨 앞에 오는 영상이 검색과 추천을 동시에 타는 경향이 있어요.",
    "mystery": "괴담, 무서운 이야기, 도시전설, 미제 사건 쇼츠예요. '이해하면 무서운 이야기'처럼 시리즈로 이어지는 채널이 꾸준히 상위권에 올라요.",
    "beauty": "메이크업 튜토리얼, 화장품 비교, 피부 관리 쇼츠예요. 전후 비교가 분명한 영상이 짧은 시간에 높은 조회수를 얻어요.",
    "lifehacks": "살림 꿀팁, 다이소 추천템, 정리·청소 요령, DIY 쇼츠예요. 바로 따라 할 수 있는 한 가지 팁만 담은 영상이 저장과 공유를 많이 받아요.",
    "animals": "아기 동물과 야생 동물 쇼츠예요. 동물원·보호소의 실제 장면과 자연 다큐 클립이 국내외 순위에 함께 오르는 분야예요.",
    "ai-video": "AI로 만든 애니메이션, 동물 캐릭터, 영상 쇼츠예요. 같은 캐릭터로 이어 가는 시리즈가 작은 채널에서 수백만 조회를 만드는 일이 많은 분야예요.",
    "travel": "여행지 추천, 현지 풍경, 여행 꿀팁 쇼츠예요. 계절과 연휴 일정에 따라 순위가 크게 바뀌어서 시기를 잘 맞춘 영상이 빠르게 올라와요.",
    "cooking": "집밥 레시피, 간단 요리, 자취 요리 쇼츠예요. 재료 수가 적고 1분 안에 완성되는 레시피가 특히 잘 퍼져요.",
    "fitness": "홈트레이닝, 다이어트 운동, 헬스 자세 교정 쇼츠예요. 따라 하기 쉬운 동작 하나를 반복해 보여 주는 형식이 강세예요.",
    "comedy": "웃긴 상황극, 예능 클립, 개그 쇼츠예요. 연예인 예능 장면과 일반인 상황극이 함께 경쟁하는 가장 큰 분야 가운데 하나예요.",
    "parenting": "아기와 신생아 일상, 형제·남매 케미, 육아 공감 쇼츠예요. 반려동물과 아기가 함께 나오는 영상은 강아지·고양이 순위에도 같이 올라요.",
    "dance": "댄스 챌린지, 커버 댄스, 노래 라이브 쇼츠예요. 새 챌린지가 시작되면 며칠 사이 비슷한 영상이 한꺼번에 순위에 들어오는 분야예요.",
    "cars": "신차 소개, 자동차 리뷰, 운전 꿀팁 쇼츠예요. 블랙박스 영상과 차량 기능 소개가 꾸준히 높은 반응을 얻어요.",
    "money": "재테크, 경제 상식, 돈 모으는 방법 쇼츠예요. 구체적인 금액과 숫자가 들어간 제목이 클릭을 많이 받는 분야예요.",
    "facts": "몰랐던 사실, 상식, 과학·역사 잡학 쇼츠예요. 질문으로 시작해 마지막에 답을 알려 주는 구성이 끝까지 보게 만드는 힘이 커요.",
    "tech": "스마트폰·전자기기 언박싱과 리뷰 쇼츠예요. 신제품 발표 직후 며칠 동안 관련 영상이 순위를 크게 차지해요.",
    "fashion": "데일리 코디, 계절 옷차림, 패션 아이템 추천 쇼츠예요. 체형별·상황별로 하나의 주제에 집중한 영상이 반응이 좋아요.",
}


# ---------- 숫자·글자 표시 (assets/app.js 와 같은 규칙) ----------
def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def _trim1(n):
    s = f"{n:.1f}"
    return s[:-2] if s.endswith(".0") else s


def kn(n):
    if n is None:
        return "-"
    n = max(n, 0)
    a = abs(n)
    if a >= 1e8:
        return _trim1(n / 1e8) + "억"
    if a >= 1e5:
        return f"{round(n / 1e4):,}만"
    if a >= 1e4:
        return _trim1(n / 1e4) + "만"
    if a >= 1e3:
        return _trim1(n / 1e3) + "천"
    return str(round(n))


def ratio_text(r):
    if r is None:
        return None
    return f"{round(r):,}배" if r >= 10 else _trim1(r) + "배"


def ago(h):
    if h is None:
        return ""
    if h < 1:
        return "방금"
    if h < 24:
        return f"{int(h)}시간 전"
    return f"{int(h // 24)}일 전"


def dur(s):
    if s is None:
        return ""
    return f"{s // 60}:{s % 60:02d}"


HASHTAG = re.compile(r"#[^\s#]+")


def title(t):
    c = re.sub(r"\s+", " ", HASHTAG.sub(" ", t or "")).strip()
    return c or (t or "")


def kst_text(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(KST)
    return f"{d.month}월 {d.day}일 {d.hour}:{d.minute:02d}"


# ---------- 조각 ----------
def thumb(vid, alt=""):
    v = esc(vid)
    return (f'<img src="https://i.ytimg.com/vi/{v}/oar2.jpg" data-fb="https://i.ytimg.com/vi/{v}/hqdefault.jpg" '
            f'alt="{esc(alt)}" loading="lazy" decoding="async">')


def spark(series):
    if not series or len(series) < 2:
        return ""
    last = series[-1][0]
    s = [p for p in series if p[0] >= last - 12] or series[-2:]
    if len(s) < 2:
        s = series[-2:]
    x0, x1 = s[0][0], s[-1][0]
    ys = [p[1] for p in s]
    lo, hi = min(ys), max(ys)
    span, tspan = (hi - lo) or 1, (x1 - x0) or 1
    pts = " ".join(f"{(p[0] - x0) / tspan * 160:.1f},{36 - 3 - (p[1] - lo) / span * 30:.1f}" for p in s)
    return ('<svg class="spark" viewBox="0 0 160 36" preserveAspectRatio="none" role="img" aria-label="최근 12시간 조회수 추이">'
            f'<polygon points="0,36 {pts} 160,36" fill="#E8EEFC"/><polyline points="{pts}" fill="none" stroke="#1E4FD8" '
            'stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')


def card(v, rank=None):
    ratio = ratio_text(v.get("ratio"))
    meta = esc(v.get("cn")) + (" · " + ago(v["age_h"]) if v.get("age_h") is not None else "")
    return (f'<a class="card" href="/v/{esc(v["id"])}"><div class="tile">{thumb(v["id"])}'
            + (f'<span class="rank">{rank}</span>' if rank else "")
            + (f'<span class="dur">{dur(v["dur"])}</span>' if v.get("dur") else "")
            + f'</div><div class="cb"><p class="ct">{esc(title(v["t"]))}</p><p class="cm">{meta}</p>{spark(v.get("series"))}'
            + f'<div class="badges"><span class="b-blue">▲ {kn(v.get("vph"))}/시간</span>'
            + (f'<span class="b-orange">구독자 {ratio}</span>' if ratio else "")
            + "</div></div></a>")


def tabs(cur, make):
    return "".join(f'<a class="tab{" on" if r == cur else ""}" role="tab" aria-selected="{str(r == cur).lower()}" href="{make(r)}">{RNAME[r]}</a>'
                   for r in ("kr", "us"))


def cat_chips(r, exclude=None):
    return "".join(f'<a class="chip" href="/{r}/{c["slug"]}">{esc(c["name"])}</a>'
                   for c in config.CATEGORIES if c["slug"] != exclude)


def fill(tpl, values, title_text=None, desc=None, path="/"):
    out = tpl
    for k, v in values.items():
        out = out.replace(f"<!--@{k}-->", v)
    out = re.sub(r"<!--@[A-Za-z0-9]+-->", "", out)
    if title_text:
        out = re.sub(r"<title>.*?</title>", f"<title>{esc(title_text)}</title>", out, count=1)
        out = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{esc(title_text)}">', out, count=1)
    if desc:
        out = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{esc(desc)}">', out, count=1)
        out = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{esc(desc)}">', out, count=1)
    out = out.replace('<link rel="canonical" href="https://risingshorts.com/">', f'<link rel="canonical" href="{SITE}{path}">')
    out = out.replace('<meta property="og:url" content="https://risingshorts.com/">', f'<meta property="og:url" content="{SITE}{path}">')
    return out


def _w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------- 요약 문장 ----------
def summary_lines(items, rname):
    """순위 목록에서 눈에 띄는 점을 문장으로 뽑는다 (매시간 바뀌는 설명글)."""
    if not items:
        return []
    lines = []
    top = items[0]
    lines.append(f"지금 {rname} 1위는 {esc(top['cn'])}의 「{esc(title(top['t']))}」로, 시간당 조회수가 약 {kn(top.get('vph'))}씩 늘고 있어요.")
    small = [v for v in items[:20] if v.get("subs") is not None and v["subs"] < 10000]
    if small:
        lines.append(f"상위 20개 가운데 {len(small)}개는 구독자 1만 명이 안 되는 작은 채널의 영상이에요.")
    durs = [v["dur"] for v in items[:20] if v.get("dur")]
    if durs:
        short = sum(1 for d in durs if d <= 30)
        lines.append(f"상위권 영상의 길이는 평균 {round(sum(durs) / len(durs))}초이고, 30초 이하 영상이 {short}개예요.")
    young = [v for v in items[:20] if v.get("age_h") is not None and v["age_h"] < 48]
    if young:
        lines.append(f"올라온 지 이틀이 안 된 영상이 {len(young)}개 들어 있어요.")
    return lines


def intro_block(heading, paragraphs, bullets=None):
    body = "".join(f"<p>{p}</p>" for p in paragraphs)
    if bullets:
        body += "<ul>" + "".join(f"<li>{b}</li>" for b in bullets) + "</ul>"
    return f'<section class="section prose" style="max-width:none"><h2 style="margin-top:0">{heading}</h2>{body}</section>'


HOW_TO = [
    "<b>시간당 조회</b>는 최근 3시간 동안 1시간에 조회수가 평균 얼마나 늘었는지예요. 누적 조회수가 아니라 지금의 속도라서, 막 뜨기 시작한 영상을 먼저 찾을 수 있어요.",
    "<b>구독자 대비</b>는 조회수를 채널 구독자 수로 나눈 값이에요. 100배가 넘으면 구독자가 아닌 사람들에게 추천으로 크게 퍼졌다는 뜻이에요.",
    "추이 그래프는 최근 12시간 동안 조회수가 어떻게 늘었는지 보여 줘요. 오른쪽으로 갈수록 가팔라지면 지금 속도가 붙고 있는 영상이에요.",
]


# ---------- 페이지 ----------
def render_all(site_dir, tpl_dir, homes, cats, details, updated, reports=None):
    """homes: {region: items}, cats: {(slug, region): payload}, details: {id: detail}."""
    tpl = {n: open(os.path.join(tpl_dir, n), encoding="utf-8").read()
           for n in os.listdir(tpl_dir) if n.endswith(".html")}
    stamp = kst_text(updated) + " 갱신 · 1시간마다 자동 업데이트"
    written = 0

    # 홈 (국내: /, 해외: /us)
    for r in ("kr", "us"):
        items = homes.get(r, [])
        us_list = ""
        if r == "kr":
            us_list = "".join(
                f'<a class="mini" href="/v/{esc(v["id"])}"><div class="tile">{thumb(v["id"])}</div><div style="min-width:0;display:flex;flex-direction:column;gap:4px">'
                f'<p class="ct">{esc(title(v["t"]))}</p><span class="b-blue" style="align-self:flex-start">▲ {kn(v.get("vph"))}/시간</span></div></a>'
                for v in homes.get("us", [])[:5])
        intro = intro_block(f"지금 {RNAME[r]} 쇼츠 흐름", summary_lines(items, RNAME[r])) + \
            intro_block("순위 보는 법", HOW_TO)
        page = fill(tpl["index.html"], {
            "stamp": stamp,
            "heroTitle": f"지금 가장 빠르게 뜨는 {RNAME[r]} 쇼츠",
            "tabs": tabs(r, lambda x: "/us" if x == "us" else "/"),
            "cats": cat_chips(r),
            "top5": "".join(card(v, i + 1) for i, v in enumerate(items[:5])),
            "rest": "".join(card(v, i + 6) for i, v in enumerate(items[5:])),
            "restHidden": "" if len(items) > 5 else " hidden",
            "usList": us_list,
            "stripHidden": "" if us_list else " hidden",
            "intro": intro,
        }, title_text=("라이징쇼츠 | 지금 뜨는 유튜브 쇼츠 실시간 떡상 순위" if r == "kr" else "해외 쇼츠 떡상 순위 (영어권) | 라이징쇼츠"),
           desc=f"{RNAME[r]} 유튜브 쇼츠 가운데 지금 가장 빠르게 조회수가 늘고 있는 영상을 1시간마다 집계합니다. 20개 카테고리별 순위와 조회수 추이.",
           path="/" if r == "kr" else "/us")
        _w(os.path.join(site_dir, "index.html" if r == "kr" else "us.html"), page)
        written += 1

    # 카테고리 (/kr/slug, /us/slug)
    for c in config.CATEGORIES:
        for r in ("kr", "us"):
            d = cats.get((c["slug"], r)) or {}
            items = d.get("by_score", [])
            total = d.get("total", len(items))
            lead = f"최근 7일 안에 올라온 {RNAME[r]} {esc(c['name'])} 쇼츠 {total:,}개를 추적하고 있어요. {kst_text(updated)} 갱신."
            intro = intro_block(f"{esc(c['name'])} 쇼츠는 이런 분야예요", [CAT_INTRO.get(c["slug"], "")] + summary_lines(items, f"{RNAME[r]} {esc(c['name'])}")) + \
                intro_block("순위 보는 법", HOW_TO)
            page = fill(tpl["category.html"], {
                "crumbName": esc(c["name"]),
                "name": f"{esc(c['name'])} 쇼츠 떡상 순위",
                "lead": lead,
                "tabs": tabs(r, lambda x, s=c["slug"]: f"/{x}/{s}"),
                "grid": "".join(card(v, i + 1) for i, v in enumerate(items[:20])),
                "others": cat_chips(r, exclude=c["slug"]),
                "intro": intro,
            }, title_text=f"{c['name']} 쇼츠 떡상 순위 ({RNAME[r]}) | 라이징쇼츠",
               desc=f"{c['name']} 분야에서 지금 가장 빠르게 조회수가 늘고 있는 {RNAME[r]} 유튜브 쇼츠 순위. 1시간마다 갱신.",
               path=f"/{r}/{c['slug']}")
            _w(os.path.join(site_dir, r, f"{c['slug']}.html"), page)
            written += 1

    # 영상 상세 (/v/id): 글자 정보만 미리 채우고, 그래프는 화면에서 그림
    vdir = os.path.join(site_dir, "v")
    if os.path.isdir(vdir):
        for n in os.listdir(vdir):
            os.remove(os.path.join(vdir, n))
    for vid, v in details.items():
        t = title(v["t"])
        ranks = v.get("ranks") or []
        first_cat = next((x for x in ranks if x["slug"]), None)
        crumbs = '<a href="/">홈</a><span aria-hidden="true">›</span>' + \
            (f'<a href="/{first_cat["region"]}/{first_cat["slug"]}">{esc(first_cat["label"])}</a><span aria-hidden="true">›</span>' if first_cat else "") + \
            "<b>영상 상세</b>"
        badges = "".join(
            f'<a class="b-solid{" lite" if i else ""}" href="{("/" + x["region"] + "/" + x["slug"]) if x["slug"] else ("/us" if x["region"] == "us" else "/")}">{esc(x["label"])} {x["rank"]}위</a>'
            for i, x in enumerate(ranks))
        sub = " · ".join(p for p in [esc(v.get("cn")), f"구독자 {kn(v['subs'])}명" if v.get("subs") is not None else "",
                                      ago(v.get("age_h")) + " 업로드" if v.get("age_h") is not None else ""] if p)
        detail = (f'<div class="detail"><div class="side"><div class="tile">{thumb(vid, t + " 썸네일")}'
                  + (f'<span class="dur">{dur(v["dur"])}</span>' if v.get("dur") else "")
                  + f'</div><div class="acts" style="display:flex;flex-direction:column;gap:10px"><a class="btn dark" href="https://www.youtube.com/shorts/{esc(vid)}" target="_blank" rel="noopener">유튜브에서 보기</a></div></div>'
                  + f'<div class="body"><div style="display:flex;flex-direction:column;gap:10px">{("<div class=badges>" + badges + "</div>") if badges else ""}'
                  + f'<h1 style="font-size:32px;line-height:1.3;overflow-wrap:anywhere">{esc(t)}</h1><p class="lead">{sub}</p></div>'
                  + '<div class="stats">'
                  + f'<div class="stat"><span>시간당 조회</span><span class="v num" style="color:var(--blue)">{kn(v.get("vph"))}</span></div>'
                  + f'<div class="stat"><span>누적 조회</span><span class="v num">{kn(v.get("views"))}</span></div>'
                  + f'<div class="stat warm"><span>구독자 대비</span><span class="v num" style="color:var(--orange)">{ratio_text(v.get("ratio")) or "-"}</span></div>'
                  + "</div></div></div>")
        if v.get("related"):
            detail += '<section class="section"><div class="section-h"><h2>같은 카테고리에서 뜨는 쇼츠</h2></div><div class="grid4">' + \
                "".join(card(x) for x in v["related"]) + "</div></section>"
        desc = f"{v.get('cn')}의 쇼츠 「{t}」 조회수 {kn(v.get('views'))}, 시간당 {kn(v.get('vph'))} 증가, 구독자 대비 {ratio_text(v.get('ratio')) or '-'}."
        page = fill(tpl["video.html"], {"crumbs": crumbs, "detail": detail},
                    title_text=f"{t[:60]} - 조회수 추이 | 라이징쇼츠", desc=desc, path=f"/v/{vid}")
        _w(os.path.join(vdir, f"{vid}.html"), page)
        written += 1

    # 주간 리포트 (이번 주 + 지난 주들)
    current = report_data(homes, cats, updated)
    if reports is not None:
        reports[current["key"]] = current
    render_reports(site_dir, tpl["report.html"], current, reports or {})
    written += 1

    # 문의 (이메일은 config.CONTACT_EMAIL)
    email = getattr(config, "CONTACT_EMAIL", "")
    mail = f'<a href="mailto:{esc(email)}">{esc(email)}</a>' if email else "준비 중"
    _w(os.path.join(site_dir, "contact.html"), fill(tpl["contact.html"], {"email": mail}, path="/contact"))

    # 그 밖의 페이지는 틀 그대로 (빈 자리만 지움)
    for name in ("search.html", "about.html", "privacy.html", "video.html", "category.html", "guide.html"):
        if name in tpl:
            p = "/" + name[:-5] if name not in ("video.html", "category.html") else "/"
            _w(os.path.join(site_dir, name), fill(tpl[name], {}, path=p))
    gdir = os.path.join(tpl_dir, "guide")
    if os.path.isdir(gdir):
        for n in os.listdir(gdir):
            t = open(os.path.join(gdir, n), encoding="utf-8").read()
            _w(os.path.join(site_dir, "guide", n), fill(t, {}, path="/guide/" + n[:-5]))
    # 추적이 끝난 영상 주소(/v/옛ID)용 404 페이지: 화면 스크립트가 안내를 보여 줌
    _w(os.path.join(site_dir, "404.html"), fill(tpl["video.html"], {}, path="/"))
    return written


def guide_slugs(tpl_dir):
    gdir = os.path.join(tpl_dir, "guide")
    return sorted(n[:-5] for n in os.listdir(gdir)) if os.path.isdir(gdir) else []


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return 0
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


CARD_KEYS = ("id", "t", "cn", "views", "vph", "ratio", "dur", "age_h", "subs")


def week_info(updated):
    """KST 기준 그 주 월요일과 주차 키 (예: 2026-W45)."""
    d = datetime.fromisoformat(updated.replace("Z", "+00:00")).astimezone(KST)
    monday = (d - timedelta(days=d.weekday())).date()
    y, w, _ = monday.isocalendar()
    return f"{y}-W{w:02d}", monday


def report_data(homes, cats, updated):
    """리포트에 필요한 숫자만 뽑아 둔다 (주차별로 상태 파일에 저장해 지난 리포트를 남김)."""
    key, monday = week_info(updated)
    out = {"key": key, "monday": monday.isoformat(), "updated": updated, "regions": {}}
    for r in ("kr", "us"):
        seen, pool = set(), []
        for c in config.CATEGORIES:
            for v in (cats.get((c["slug"], r)) or {}).get("by_views", []):
                if v["id"] not in seen:
                    seen.add(v["id"])
                    pool.append(v)
        pool.sort(key=lambda v: -(v.get("views") or 0))
        stats = []
        for c in config.CATEGORIES:
            it = (cats.get((c["slug"], r)) or {}).get("by_score", [])[:20]
            if it:
                stats.append([c["slug"], _median([v.get("vph") or 0 for v in it]), _median([v["dur"] for v in it if v.get("dur")])])
        stats.sort(key=lambda x: -x[1])
        out["regions"][r] = {"top": [{k: v.get(k) for k in CARD_KEYS} for v in pool[:10]], "stats": stats}
    return out


def report_html(data, current=True, archive=()):
    names = {c["slug"]: c["name"] for c in config.CATEGORIES}
    updated = data["updated"]
    monday = datetime.fromisoformat(data["monday"])
    sunday = monday + timedelta(days=6)
    if current:
        end = datetime.fromisoformat(updated.replace("Z", "+00:00")).astimezone(KST)
        start = end - timedelta(days=7)
        stamp = f"{start.month}월 {start.day}일 ~ {end.month}월 {end.day}일 업로드 쇼츠 · {kst_text(updated)} 갱신"
        h1 = "이번 주 쇼츠 리포트"
    else:
        stamp = f"{monday.month}월 {monday.day}일 ~ {sunday.month}월 {sunday.day}일 주간 · 마지막 집계 {kst_text(updated)}"
        h1 = f"{monday.year}년 {monday.month}월 {monday.day}일 주간 쇼츠 리포트"
    parts = [f'<section class="head"><div><p class="stamp">{stamp}</p><h1>{h1}</h1>'
             '<p class="lead">최근 7일 동안 올라온 쇼츠 가운데 국내와 해외에서 무엇이 가장 크게 떴는지, '
             '라이징쇼츠가 1시간마다 모은 데이터로 자동 정리한 리포트예요.</p></div></section>']
    for r in ("kr", "us"):
        reg = data["regions"].get(r) or {"top": [], "stats": []}
        top, stats = reg["top"], reg["stats"]
        verb = "가장 많이 본" if current else "가장 많이 본"
        lines = []
        if top:
            v = top[0]
            lines.append(f"{'이번 주' if current else '이 주에'} {RNAME[r]}에서 {verb} 쇼츠는 {esc(v['cn'])}의 「{esc(title(v['t']))}」로, 누적 조회수 {kn(v.get('views'))}를 기록했어요.")
        if stats:
            lines.append(("지금" if current else "이 주에") + " 가장 빠르게 조회수가 늘던 분야는 " +
                         ", ".join(f"{esc(names.get(sl, sl))}(상위 20개 시간당 조회 중앙값 {kn(m)})" for sl, m, _ in stats[:3]) + "였어요.")
            lines.append("반대로 " + ", ".join(esc(names.get(sl, sl)) for sl, _, _ in stats[-3:]) + " 분야는 상위권 영상의 속도가 상대적으로 느렸어요.")
        rows = "".join(f'<tr><td><a href="/{r}/{sl}">{esc(names.get(sl, sl))}</a></td><td class="num">{kn(m)}</td><td class="num">{round(d)}초</td></tr>'
                       for sl, m, d in stats)
        parts.append(f'<section class="section"><h2>{RNAME[r]}{" (영어권)" if r == "us" else ""}</h2>'
                     + "".join(f'<p class="lead" style="color:var(--ink2)">{l}</p>' for l in lines)
                     + f'<h3 style="margin:10px 0 0;font-size:17px">가장 많이 본 쇼츠 TOP 10</h3><div class="grid5">'
                     + "".join(card(v, i + 1) for i, v in enumerate(top)) + "</div>"
                     + '<h3 style="margin:18px 0 0;font-size:17px">카테고리별 속도와 길이</h3>'
                     + '<div class="prose" style="max-width:none;padding:8px 18px"><table class="tbl"><thead><tr><th>카테고리</th><th>시간당 조회 (상위 20개 중앙값)</th><th>영상 길이 (중앙값)</th></tr></thead><tbody>'
                     + rows + "</tbody></table></div></section>")
    if archive:
        parts.append('<section class="section"><h2 style="font-size:19px">지난 리포트</h2><ul class="links">'
                     + "".join(f'<li><a href="/report/{k}">{lab}</a></li>' for k, lab in archive) + "</ul></section>")
    parts.append('<p class="help">숫자는 유튜브 공개 데이터로 계산한 추정치예요. '
                 '<a href="/guide/how-to-read-rankings">지표 읽는 법 보기</a></p>')
    return "".join(parts)


def render_reports(site_dir, tpl, current, archive_data):
    """/report (이번 주) 와 /report/2026-W45 같은 지난 주 리포트들."""
    past = sorted((d for k, d in archive_data.items() if k != current["key"]), key=lambda d: d["key"], reverse=True)

    def label(d):
        m = datetime.fromisoformat(d["monday"])
        return f"{m.year}년 {m.month}월 {m.day}일 주간"
    links = [(d["key"], label(d)) for d in past]
    _w(os.path.join(site_dir, "report.html"), fill(tpl, {"report": report_html(current, True, links)}, path="/report"))
    rdir = os.path.join(site_dir, "report")
    os.makedirs(rdir, exist_ok=True)
    for d in past:
        others = [(k, l) for k, l in links if k != d["key"]]
        _w(os.path.join(rdir, f"{d['key']}.html"),
           fill(tpl, {"report": report_html(d, False, others)}, title_text=f"{label(d)} 쇼츠 리포트 | 라이징쇼츠",
                desc=f"{label(d)} 국내·해외에서 가장 많이 본 쇼츠 TOP 10과 카테고리별 흐름.", path=f"/report/{d['key']}"))
    return [d["key"] for d in past]
