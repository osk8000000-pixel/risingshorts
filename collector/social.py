"""SNS 자동 게시: 매일 저녁 '오늘의 떡상 쇼츠 TOP 5' 카드 이미지와 글을 만들고 Threads 에 올린다.

흐름 (GitHub Actions 한 번의 실행 안에서)
1. 수집기(collect.py)가 한국 시간 20시 이후 첫 실행에서 prepare() 를 부른다.
   - 카드 이미지를 site/social/YYYYMMDD.png 로 만들고 (사이트와 함께 배포됨)
   - 게시할 글과 이미지 주소를 site/social/pending.json 에 적고
   - Threads 연결 키를 새로 고쳐 (60일 만료 방지) 암호화해 상태 파일에 보관하고,
     이번 실행에서 쓸 키를 state/.threads_token 에 둔다 (저장소에 올라가지 않음)
2. 배포가 끝나면 워크플로가 `python collector/social.py post` 로 실제 게시한다.
"""
import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
SITE = "https://risingshorts.com"
GRAPH = "https://graph.threads.net/v1.0"
POST_HOUR_KST = 20
FONT_URLS = [
    "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf",
    "https://github.com/google/fonts/raw/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf",
]
TOKEN_FILE = os.path.join("state", ".threads_token")


# ---------- 키 보관 (공개 저장소라 평문 저장 금지: YT_API_KEY 로 만든 키스트림으로 암호화) ----------
def _stream(key, n):
    out, i = b"", 0
    while len(out) < n:
        out += hashlib.sha256(key + i.to_bytes(4, "big")).digest()
        i += 1
    return out[:n]


def seal(text, secret):
    nonce = os.urandom(16)
    data = text.encode()
    ks = _stream(hashlib.sha256(secret.encode() + nonce).digest(), len(data))
    return base64.b64encode(nonce + bytes(a ^ b for a, b in zip(data, ks))).decode()


def unseal(blob, secret):
    raw = base64.b64decode(blob)
    nonce, data = raw[:16], raw[16:]
    ks = _stream(hashlib.sha256(secret.encode() + nonce).digest(), len(data))
    return bytes(a ^ b for a, b in zip(data, ks)).decode()


def _get_json(url, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def refresh_token(token):
    q = urllib.parse.urlencode({"grant_type": "th_refresh_token", "access_token": token})
    return _get_json(f"https://graph.threads.net/refresh_access_token?{q}")["access_token"]


def current_token(social, secret):
    """보관된 키 → 환경변수(GitHub Secret) 순서로 시도해 새로 고친 키를 돌려준다."""
    cands = []
    if social.get("tok") and secret:
        try:
            cands.append(unseal(social["tok"], secret))
        except Exception:
            pass
    env = os.environ.get("THREADS_TOKEN", "").strip()
    if env and env not in cands:
        cands.append(env)
    last = None
    for t in cands:
        try:
            return refresh_token(t)
        except urllib.error.HTTPError as e:
            last = e.read().decode()[:200]
        except Exception as e:  # noqa: BLE001
            last = str(e)[:200]
        # 새로 고침이 막혀도(발급 24시간 이내 등) 키 자체는 쓸 수 있을 수 있음
        try:
            _get_json(f"{GRAPH}/me?fields=id&access_token={urllib.parse.quote(t)}")
            return t
        except Exception:
            continue
    raise RuntimeError(f"Threads 연결 키를 쓸 수 없음: {last}")


# ---------- 표시 규칙 ----------
def _trim1(n):
    s = f"{n:.1f}"
    return s[:-2] if s.endswith(".0") else s


def kn(n):
    n = max(n or 0, 0)
    if n >= 1e8:
        return _trim1(n / 1e8) + "억"
    if n >= 1e5:
        return f"{round(n / 1e4):,}만"
    if n >= 1e4:
        return _trim1(n / 1e4) + "만"
    if n >= 1e3:
        return _trim1(n / 1e3) + "천"
    return str(round(n))


def ratio_text(r):
    if r is None:
        return None
    return f"{round(r):,}배" if r >= 10 else _trim1(r) + "배"


def clean_title(t):
    import re
    c = re.sub(r"\s+", " ", re.sub(r"#[^\s#]+", " ", t or "")).strip()
    return c or (t or "")


# ---------- 카드 이미지 ----------
CJK_DIR = "/usr/share/fonts/opentype/noto"


def _font(path, size, weight):
    from PIL import ImageFont
    if path.endswith(".ttc"):  # 시스템 Noto Sans CJK (한국어 글꼴은 묶음의 2번째)
        name = "Black" if weight >= 850 else "Bold" if weight >= 650 else "Medium" if weight >= 550 else "Regular"
        return ImageFont.truetype(os.path.join(os.path.dirname(path), f"NotoSansCJK-{name}.ttc"), size, index=1)
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def _fit(draw, text, font, width, lines=2):
    words, out, cur = list(text), [], ""
    for ch in words:
        if draw.textlength(cur + ch, font=font) <= width:
            cur += ch
        else:
            out.append(cur)
            cur = ch
            if len(out) == lines:
                break
    if len(out) < lines and cur:
        out.append(cur)
    if len(out) == lines and "".join(out) != text:
        last = out[-1]
        while last and draw.textlength(last + "…", font=font) > width:
            last = last[:-1]
        out[-1] = last + "…"
    return out


def make_card(items, day, path, font_path):
    from PIL import Image, ImageDraw
    W, H = 1080, 1350
    blue, ink, muted, bg = (30, 79, 216), (21, 24, 29), (90, 97, 108), (246, 247, 249)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 250], fill=blue)
    # 로고 화살표
    d.line([(70, 150), (112, 102), (138, 128), (182, 74)], fill="white", width=14, joint="curve")
    d.line([(150, 74), (182, 74), (182, 106)], fill="white", width=14, joint="curve")
    d.text((215, 62), "라이징쇼츠", font=_font(font_path, 40, 800), fill=(214, 225, 252))
    d.text((215, 110), "오늘의 떡상 쇼츠 TOP 5", font=_font(font_path, 64, 900), fill="white")
    d.text((W - 70, 70), f"{day.month}월 {day.day}일", font=_font(font_path, 34, 700), fill=(214, 225, 252), anchor="ra")
    f_rank = _font(font_path, 72, 900)
    f_title = _font(font_path, 40, 700)
    f_meta = _font(font_path, 30, 500)
    f_badge = _font(font_path, 30, 800)
    y = 300
    for i, v in enumerate(items[:5]):
        d.rounded_rectangle([50, y, W - 50, y + 170], radius=28, fill="white", outline=(236, 238, 241), width=2)
        d.text((95, y + 85), str(i + 1), font=f_rank, fill=blue if i < 3 else muted, anchor="lm")
        line = _fit(d, clean_title(v["t"]), f_title, W - 50 - 190 - 40, lines=1)[0]
        d.text((190, y + 58), line, font=f_title, fill=ink, anchor="lm")
        d.text((190, y + 122), (v.get("cn") or "")[:20], font=f_meta, fill=muted, anchor="lm")
        badge = f"▲ 시간당 {kn(v.get('vph'))}"
        bw = d.textlength(badge, font=f_badge) + 36
        d.rounded_rectangle([W - 90 - bw, y + 100, W - 90, y + 144], radius=12, fill=(232, 238, 252))
        d.text((W - 90 - bw / 2, y + 122), badge, font=f_badge, fill=blue, anchor="mm")
        y += 190
    d.text((W / 2, H - 70), "전체 순위 risingshorts.com · 1시간마다 갱신", font=_font(font_path, 32, 600), fill=muted, anchor="mm")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True)


def caption(items, day):
    lines = [f"📈 오늘 가장 빠르게 뜨는 국내 쇼츠 TOP 5 ({day.month}/{day.day})", ""]
    for i, v in enumerate(items[:5]):
        t = clean_title(v["t"])
        t = t if len(t) <= 34 else t[:33] + "…"
        extra = f", 구독자 {ratio_text(v['ratio'])}" if v.get("ratio") and v["ratio"] >= 10 else ""
        lines.append(f"{i + 1}. {t} (시간당 {kn(v.get('vph'))}{extra})")
    lines += ["", "카테고리별 전체 순위 👉 risingshorts.com"]
    if day.weekday() == 0:
        lines.append("이번 주 리포트 👉 risingshorts.com/report")
    lines += ["", "#쇼츠"]
    text = "\n".join(lines)
    return text[:490]


def _get_font():
    sys_font = os.path.join(CJK_DIR, "NotoSansCJK-Bold.ttc")
    if os.path.exists(sys_font):
        return sys_font
    path = os.path.join("state", "NotoSansKR.ttf")
    if os.path.exists(path):
        return path
    for u in FONT_URLS:
        try:
            with urllib.request.urlopen(u, timeout=60) as r:
                data = r.read()
            with open(path, "wb") as f:
                f.write(data)
            return path
        except Exception:
            continue
    raise RuntimeError("한글 글꼴을 받지 못함")


def prepare(state, site_dir, now=None, force=False):
    """수집기에서 호출. 오늘 게시물을 준비했으면 True."""
    now = (now or datetime.now(timezone.utc)).astimezone(KST)
    social = state.setdefault("social", {})
    today = now.strftime("%Y%m%d")
    if not force and (now.hour < POST_HOUR_KST or social.get("prepared") == today):
        return False
    if not os.environ.get("THREADS_TOKEN") and not social.get("tok"):
        return False
    with open(os.path.join(site_dir, "data", "home-kr.json"), encoding="utf-8") as f:
        items = json.load(f).get("items", [])
    if len(items) < 5:
        return False
    secret = os.environ.get("YT_API_KEY", "")
    token = current_token(social, secret)
    if secret:
        social["tok"] = seal(token, secret)
    os.makedirs("state", exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(token)
    os.chmod(TOKEN_FILE, 0o600)
    img_rel = f"social/{today}.png"
    make_card(items, now, os.path.join(site_dir, img_rel), _get_font())
    with open(os.path.join(site_dir, "social", "pending.json"), "w", encoding="utf-8") as f:
        json.dump({"date": today, "image_url": f"{SITE}/{img_rel}", "text": caption(items, now)}, f, ensure_ascii=False)
    social["prepared"] = today
    return True


def post(pending_path):
    with open(pending_path, encoding="utf-8") as f:
        p = json.load(f)
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    # 배포된 이미지가 열릴 때까지 기다림 (최대 5분)
    for _ in range(30):
        try:
            with urllib.request.urlopen(p["image_url"] + "?v=" + str(int(time.time())), timeout=20) as r:
                if r.status == 200:
                    break
        except Exception:
            pass
        time.sleep(10)
    body = urllib.parse.urlencode({"media_type": "IMAGE", "image_url": p["image_url"], "text": p["text"],
                                   "access_token": token}).encode()
    cid = _get_json(f"{GRAPH}/me/threads", data=body)["id"]
    time.sleep(30)  # Meta 권장: 컨테이너 처리 대기
    pub = _get_json(f"{GRAPH}/me/threads_publish",
                    data=urllib.parse.urlencode({"creation_id": cid, "access_token": token}).encode())
    print(f"Threads 게시 완료: {pub.get('id')}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "post":
        try:
            post(sys.argv[2])
        except urllib.error.HTTPError as e:
            print(f"::error::Threads 게시 실패: {e.code} {e.read().decode()[:300]}")
            sys.exit(1)
