"""페이지 틀(templates/*.html)을 만드는 스크립트.
수집기(collector/render.py)가 매시간 이 틀에 순위 내용을 채워 site/ 에 최종 페이지를 씁니다.
사용법: python3 tools/make_pages.py templates
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
out = sys.argv[1] if len(sys.argv) > 1 else "templates"
HEAD = '''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{robots}<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="라이징쇼츠">
<meta property="og:url" content="https://risingshorts.com/">
<link rel="canonical" href="https://risingshorts.com/">
<meta property="og:image" content="https://risingshorts.com/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1E4FD8">
<meta name="naver-site-verification" content="cf7616a752d049e0737ca7715e7c97812802a33a" />
<link rel="icon" href="/assets/icon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&family=Inter:wght@500;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/app.css?v=3">
</head>
<body data-page="{page}">
<header class="top">
  <div class="wrap">
    <a class="logo" href="/" aria-label="라이징쇼츠 홈">
      <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true"><rect width="30" height="30" rx="9" fill="#1E4FD8"/><path d="M8 20 L13.5 13.5 L17 17 L22 10" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M18 10 H22 V14" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span>라이징쇼츠</span>
    </a>
    <nav class="nav" aria-label="주 메뉴">
      <a href="/" data-nav="home">지금 뜨는 쇼츠</a>
      <a href="/kr/dog" data-nav="category">카테고리</a>
      <a href="/report" data-nav="report">주간 리포트</a>
      <a href="/guide" data-nav="guide">가이드</a>
    </nav>
    <form class="qbox" role="search" action="/search" method="get">
      <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="#5A616C" stroke-width="2"/><path d="M20 20 L16 16" stroke="#5A616C" stroke-width="2" stroke-linecap="round"/></svg>
      <label class="sr" for="q">키워드 검색</label>
      <input id="q" name="q" type="search" placeholder="키워드로 찾기 (예: 진돗개, 괴담)" autocomplete="off">
    </form>
  </div>
</header>
<main class="wrap">
'''
FOOT = '''
<footer class="foot">
  <span>라이징쇼츠는 YouTube Data API를 사용하며 YouTube와 제휴 관계가 아닙니다.</span>
  <nav aria-label="사이트 정보"><a href="/about">소개</a><a href="/guide">가이드</a><a href="/contact">문의</a><a href="/privacy">개인정보처리방침</a></nav>
</footer>
</main>
{script}
</body>
</html>
'''
JS = '<script src="/assets/app.js?v=3" defer></script>'
pages = {
'index.html': dict(page='home', title='라이징쇼츠 | 지금 뜨는 유튜브 쇼츠 실시간 떡상 순위',
  desc='최근 7일 안에 올라온 유튜브 쇼츠 가운데 지금 가장 빠르게 조회수가 늘고 있는 영상을 1시간마다 집계합니다. 국내·해외 20개 카테고리.',
  body='''
<section class="head">
  <div>
    <p class="stamp" id="stamp"><!--@stamp--></p>
    <h1 id="heroTitle"><!--@heroTitle--></h1>
    <p class="lead">조회수 합계가 아니라 <b>지금 오르는 속도</b>로 순위를 매겨요. 구독자에 비해 많이 본 영상일수록 가산점이 붙어요.</p>
  </div>
  <div class="tabs" role="tablist" aria-label="지역" id="tabs"><!--@tabs--></div>
</section>
<nav class="chips scroll" aria-label="카테고리" id="cats" style="margin-top:24px"><!--@cats--></nav>
<section aria-label="1~5위" class="grid5" id="top5" style="margin-top:20px"><!--@top5--></section>
<aside class="strip" id="strip"<!--@stripHidden-->>
  <div class="strip-h"><div><h2>해외에서 먼저 뜨는 쇼츠</h2><p>국내에 들어오기 전에 포맷을 먼저 확인해 보세요.</p></div><a class="btn" href="/us">해외 순위 전체 보기</a></div>
  <div class="minis" id="usList"><!--@usList--></div>
</aside>
<section class="section" id="restWrap"<!--@restHidden-->>
  <div class="section-h"><h2>6위부터</h2></div>
  <div class="grid5" id="rest"><!--@rest--></div>
</section>
<!--@intro-->
'''),
'category.html': dict(page='category', title='카테고리별 쇼츠 떡상 순위 | 라이징쇼츠',
  desc='카테고리별로 지금 가장 빠르게 조회수가 늘고 있는 유튜브 쇼츠 순위.',
  body='''
<nav class="crumb" aria-label="현재 위치"><a href="/">홈</a><span aria-hidden="true">›</span><span>카테고리</span><span aria-hidden="true">›</span><b id="crumbName"><!--@crumbName--></b></nav>
<section class="head" style="margin-top:18px">
  <div><h1 id="name"><!--@name--></h1><p class="lead" id="lead"><!--@lead--></p></div>
  <div class="tabs" role="tablist" aria-label="지역" id="tabs"><!--@tabs--></div>
</section>
<div class="bar">
  <div class="segs" role="group" aria-label="정렬" id="sorts"></div>
  <div class="segs" role="group" aria-label="업로드 기간" id="periods"></div>
</div>
<p class="help" id="help"></p>
<section aria-label="순위" class="grid5" id="grid" style="margin-top:20px"><!--@grid--></section>
<div class="empty" id="none" hidden style="margin-top:20px">이 기간에 올라온 쇼츠가 아직 없어요. 기간을 넓혀 보세요.</div>
<div class="more"><button class="btn" id="moreBtn" type="button" hidden style="min-width:220px"></button></div>
<section class="section"><h2 style="font-size:20px">다른 카테고리</h2><nav class="chips" id="others"><!--@others--></nav></section>
<!--@intro-->
'''),
'search.html': dict(page='search', title='키워드로 떡상 쇼츠 찾기 | 라이징쇼츠',
  desc='키워드로 지금 뜨는 유튜브 쇼츠를 찾아보세요.',
  body='''
<form class="bigq" role="search" action="/search" method="get">
  <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" fill="none" stroke="#1E4FD8" stroke-width="2"/><path d="M20 20 L16 16" stroke="#1E4FD8" stroke-width="2" stroke-linecap="round"/></svg>
  <label class="sr" for="bigq">키워드 검색</label>
  <input id="bigq" name="q" type="search" placeholder="예: 진돗개, 괴담, 챌린지" autocomplete="off">
  <button type="submit">검색</button>
</form>
<section class="head" style="margin-top:28px">
  <div><h1 id="title" style="font-size:30px">검색</h1><p class="lead" id="sub"></p></div>
  <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center">
    <div class="tabs" role="tablist" aria-label="지역" id="tabs"><!--@tabs--></div>
    <div class="segs bar" style="margin:0;padding:4px" role="group" aria-label="정렬" id="sortWrap" hidden><span class="segs" id="sorts"></span></div>
  </div>
</section>
<div class="stats" id="stats" hidden style="margin-top:20px"></div>
<section aria-label="검색 결과" id="results" style="margin-top:20px"></section>
<section class="section"><h2 style="font-size:18px">카테고리로 둘러보기</h2><nav class="chips" id="cats"></nav></section>
'''),
'video.html': dict(page='video', title='쇼츠 조회수 추이 | 라이징쇼츠',
  desc='쇼츠 영상의 시간대별 조회수 추이와 떡상 지표.',
  body='''
<nav class="crumb" aria-label="현재 위치" id="crumbs"><!--@crumbs--></nav>
<div id="detail"><!--@detail--></div>
'''),
'about.html': dict(page='about', title='라이징쇼츠 소개', desc='라이징쇼츠는 지금 뜨는 유튜브 쇼츠를 속도 기준으로 보여 주는 무료 서비스입니다.',
  body='''
<article class="prose">
<h1 style="font-size:30px">라이징쇼츠 소개</h1>
<p>라이징쇼츠는 최근 7일 안에 올라온 유튜브 쇼츠 가운데 <b>지금 가장 빠르게 조회수가 늘고 있는 영상</b>을 보여 주는 무료 서비스입니다. 쇼츠 채널을 운영하거나 기획하는 분들이 요즘 뜨는 주제와 포맷을 빨리 찾을 수 있도록 만들었습니다.</p>
<h2>순위는 이렇게 매겨요</h2>
<ul>
<li>국내·해외(영어권) 20개 카테고리에서 새로 올라온 쇼츠를 하루 두 번 찾아 추적 목록에 넣습니다.</li>
<li>추적 중인 쇼츠의 조회수를 1시간마다 다시 재서, 최근 3시간 동안의 <b>시간당 조회수 증가량</b>을 계산합니다.</li>
<li>구독자 수에 비해 조회수가 많을수록 가산점(최대 4배)을 붙입니다. 작은 채널의 떡상을 놓치지 않기 위해서입니다.</li>
<li>3분 이하이면서 세로 화면인 영상만 쇼츠로 봅니다. 업로드 7일이 지나면 추적을 끝냅니다.</li>
</ul>
<h2>데이터 출처</h2>
<p>모든 수치는 YouTube Data API로 공개된 정보만 받아 계산합니다. 라이징쇼츠는 YouTube 또는 Google과 제휴 관계가 아니며, 영상의 권리는 각 제작자에게 있습니다. 영상은 유튜브로 연결해 보여 드립니다.</p>
</article>
'''),
'privacy.html': dict(page='privacy', title='개인정보처리방침 | 라이징쇼츠', desc='라이징쇼츠 개인정보처리방침',
  body='''
<article class="prose">
<h1 style="font-size:30px">개인정보처리방침</h1>
<p>라이징쇼츠(이하 "사이트")는 회원가입이 없으며 이름, 이메일 같은 개인정보를 직접 받지 않습니다.</p>
<h2>자동으로 저장되는 정보</h2>
<p>사이트는 쿠키나 브라우저 저장소에 이용자 정보를 남기지 않습니다. 방문 통계를 위해 Cloudflare가 쿠키 없이 접속 수 같은 집계 정보만 기록할 수 있습니다.</p>
<h2>외부 서비스</h2>
<p>썸네일 이미지는 YouTube 서버에서 불러오며, 글꼴은 Google Fonts에서 불러옵니다. 이 과정에서 해당 서비스가 접속 정보(IP 주소 등)를 받을 수 있습니다. 앞으로 Google 애드센스 같은 광고를 게재하면, 광고 사업자가 쿠키를 사용해 맞춤 광고를 보여 줄 수 있으며 그때 이 방침을 갱신합니다.</p>
<h2>시행일</h2>
<p>이 방침은 2026년 11월 6일부터 적용됩니다.</p>
</article>
'''),
}
from guides_content import GUIDES
pages['guide.html'] = dict(page='guide', title='쇼츠 가이드 | 라이징쇼츠', desc='쇼츠 순위 데이터로 정리한 쇼츠 기획·분석 가이드 모음.',
  body='<section class="head"><div><h1>쇼츠 가이드</h1><p class="lead">라이징쇼츠가 매시간 모으는 순위 데이터를 바탕으로, 쇼츠를 기획하고 분석할 때 도움이 되는 내용을 정리했어요.</p></div></section><section class="section"><div class="guides">'
  + ''.join(f'<a class="guide-card" href="/guide/{g["slug"]}"><h2>{g["title"]}</h2><p>{g["desc"]}</p><span class="cm">{g["date"].replace("-", ".")}</span></a>' for g in GUIDES)
  + '</div></section>')
for i, g in enumerate(GUIDES):
    others = ''.join(f'<li><a href="/guide/{o["slug"]}">{o["title"]}</a></li>' for o in GUIDES if o is not g)
    pages[f'guide/{g["slug"]}.html'] = dict(page='guide', title=g['title'] + ' | 라이징쇼츠', desc=g['desc'],
      body=f'<nav class="crumb" aria-label="현재 위치"><a href="/">홈</a><span aria-hidden="true">›</span><a href="/guide">가이드</a></nav>'
        + f'<article class="prose article" style="margin-top:16px"><p class="cm">{g["date"].replace("-", ".")} · 라이징쇼츠</p><h1>{g["title"]}</h1>{g["body"]}'
        + '<div class="cta"><p><b>지금 뜨는 쇼츠를 직접 확인해 보세요.</b> 1시간마다 갱신되는 국내·해외 20개 카테고리 순위.</p><a class="btn dark" href="/">순위 보러 가기</a></div></article>'
        + f'<section class="section"><h2 style="font-size:19px">다른 가이드</h2><ul class="links">{others}</ul></section>')
pages['contact.html'] = dict(page='contact', title='문의 | 라이징쇼츠', desc='라이징쇼츠 문의 안내',
  body='<article class="prose"><h1 style="font-size:30px">문의</h1><p>라이징쇼츠에 대한 의견, 오류 제보, 순위에서 영상 제외 요청, 제휴 문의는 아래 이메일로 보내 주세요. 보통 2~3일 안에 답장드립니다.</p><p style="font-size:18px"><b>이메일</b>: <!--@email--></p><h2>영상 제외 요청</h2><p>본인 영상이 순위에 보이는 것을 원하지 않으면 영상 주소와 함께 메일을 보내 주세요. 확인 후 순위에서 제외합니다.</p></article>')
pages['report.html'] = dict(page='report', title='이번 주 쇼츠 리포트 | 라이징쇼츠', desc='이번 주 국내·해외에서 가장 빠르게 뜬 쇼츠와 카테고리 흐름을 자동으로 정리한 주간 리포트.',
  body='<!--@report-->')
for name, p in pages.items():
    script = JS if p['page'] in ('home', 'category', 'search', 'video') else JS
    p.setdefault('robots', '<meta name="robots" content="noindex, follow">\n' if p['page'] == 'search' else '')
    html = HEAD.format(**p) + p['body'] + FOOT.format(script=script)
    os.makedirs(os.path.dirname(os.path.join(out, name)), exist_ok=True)
    open(os.path.join(out, name), 'w', encoding='utf-8').write(html)
print('ok', len(pages))
