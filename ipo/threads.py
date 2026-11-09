"""공모주데이 Threads 자동 게시 (라이징쇼츠와 같은 Threads 계정 사용).

평일 아침(한국 시간 8~12시 사이 첫 실행) 하루 한 번, '오늘 청약 공모주' 카드와 글을 올린다.
- 준비: python ipo/threads.py prepare <ipos.json> <사이트 출력 폴더> <social.json>
  카드 이미지를 <out>/social/YYYYMMDD.png 로, 게시 정보를 <out>/social/pending.json 으로 만든다.
- 게시: python ipo/threads.py post <out>/social/pending.json  (배포가 끝난 뒤)

Threads 연결 키는 라이징쇼츠 수집기가 매일 새로 고쳐 data 브랜치 상태 파일에 암호화해 둔 것을 읽어 쓴다
(키를 새로 고치지 않음). 없으면 THREADS_TOKEN 환경변수를 쓴다.
"""
import gzip
import json
import os
import subprocess
import sys
import urllib.error
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "collector"))
import social as S  # noqa: E402  (collector/social.py)

SITE = "https://gongmojuday.com"
POST_HOUR_KST = 8
TOKEN_FILE = os.path.join("state", ".threads_token")
FORCE_FILE = os.path.join(ROOT, "ipo", "social_force.txt")
DOW = "월화수목금토일"


def won(n):
    return f"{int(n):,}원" if n else "미정"


def md(s):
    x = date.fromisoformat(s)
    return f"{x.month}/{x.day}({DOW[x.weekday()]})"


def lead(it):
    uws = it.get("underwriters") or []
    names = []
    for u in uws:
        n = {"아이비케이투자증권": "IBK투자증권", "케이비증권": "KB증권", "유진증권": "유진투자증권"}.get(u["name"], u["name"])
        if n not in names:
            names.append(n)
    return ", ".join(names[:2]) + (" 외" if len(names) > 2 else "") or "미정"


def pick(items, today):
    t = today.isoformat()
    wk_end = (today + timedelta(days=6 - today.weekday())).isoformat()
    live = [i for i in items if i["status"] != "withdrawn" and i.get("sub_start")]
    now = [i for i in live if i["sub_start"] <= t <= (i["sub_end"] or i["sub_start"])]
    soon = [i for i in live if t < i["sub_start"] <= wk_end]
    return now, soon


def token():
    """data 브랜치의 라이징쇼츠 상태 파일에서 암호화된 키를 꺼낸다."""
    secret = os.environ.get("YT_API_KEY", "")
    try:
        raw = subprocess.run(["git", "show", "origin/data:state.json.gz"], capture_output=True, check=True).stdout
        st = json.loads(gzip.decompress(raw))
        tok = (st.get("social") or {}).get("tok")
        if tok and secret:
            return S.unseal(tok, secret)
    except Exception as e:  # noqa: BLE001
        print(f"::warning::보관된 Threads 키를 읽지 못함: {str(e)[:120]}")
    env = os.environ.get("THREADS_TOKEN", "").strip()
    if env:
        return env
    raise RuntimeError("Threads 연결 키가 없습니다")


def make_card(now_items, soon, day, path, font_path):
    from PIL import Image, ImageDraw
    F = S._font
    W, H = 1080, 1350
    green, ink, muted, bg = (11, 122, 85), (20, 25, 26), (88, 98, 100), (245, 247, 246)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 250], fill=green)
    d.rounded_rectangle([70, 70, 180, 180], radius=30, outline="white", width=10)
    d.line([(70, 112), (180, 112)], fill="white", width=10)
    d.line([(100, 52), (100, 84)], fill="white", width=10)
    d.line([(150, 52), (150, 84)], fill="white", width=10)
    d.text((215, 62), "공모주데이", font=F(font_path, 40, 800), fill=(205, 236, 222))
    d.text((215, 110), "오늘의 공모주 청약", font=F(font_path, 64, 900), fill="white")
    d.text((W - 70, 70), f"{day.month}월 {day.day}일 ({DOW[day.weekday()]})", font=F(font_path, 34, 700), fill=(205, 236, 222), anchor="ra")
    f_name, f_meta, f_badge, f_sec = F(font_path, 46, 800), F(font_path, 30, 500), F(font_path, 28, 800), F(font_path, 34, 800)
    y = 290
    rows = [(i, True) for i in now_items[:4]] + [(i, False) for i in soon[: max(0, 5 - len(now_items[:4]))]]
    shown_soon_head = False
    if not now_items:
        d.text((60, y), "오늘은 청약하는 공모주가 없어요", font=f_sec, fill=ink)
        y += 70
    for it, is_now in rows:
        if not is_now and not shown_soon_head:
            d.text((60, y + 6), "이번 주 청약 예정", font=f_sec, fill=muted)
            y += 66
            shown_soon_head = True
        h = 170
        d.rounded_rectangle([50, y, W - 50, y + h], radius=28, fill="white", outline=(232, 236, 235), width=2)
        name = S._fit(d, it["name"], f_name, W - 50 - 90 - 260, lines=1)[0]
        d.text((90, y + 56), name, font=f_name, fill=ink, anchor="lm")
        meta = f"공모가 {won(it.get('price'))} · 최소 {won(int(it['price'] * 5) if it.get('price') else None)} · {lead(it)}"
        meta = S._fit(d, meta, f_meta, W - 50 - 90 - 40, lines=1)[0]
        d.text((90, y + 120), meta, font=f_meta, fill=muted, anchor="lm")
        if is_now:
            last = (it["sub_end"] or it["sub_start"]) == day.isoformat()
            badge = "오늘 마감" if last else f"{md(it['sub_end'])} 마감"
            fill, color = ((11, 122, 85), "white") if last else ((228, 244, 236), (7, 92, 64))
        else:
            badge = f"{md(it['sub_start'])} 시작"
            fill, color = (238, 241, 240), muted
        bw = d.textlength(badge, font=f_badge) + 36
        d.rounded_rectangle([W - 90 - bw, y + 34, W - 90, y + 78], radius=12, fill=fill)
        d.text((W - 90 - bw / 2, y + 56), badge, font=f_badge, fill=color, anchor="mm")
        y += h + 20
    d.text((W / 2, H - 110), "최소 증거금 = 10주 × 공모가 × 50%", font=F(font_path, 28, 500), fill=muted, anchor="mm")
    d.text((W / 2, H - 65), "전체 일정 gongmojuday.com · 투자 권유 아님", font=F(font_path, 32, 600), fill=muted, anchor="mm")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, optimize=True)


def caption(now_items, soon, day):
    L = [f"📅 오늘({day.month}/{day.day}) 공모주 청약", ""]
    if now_items:
        for n, it in enumerate(now_items[:5], 1):
            last = (it["sub_end"] or it["sub_start"]) == day.isoformat()
            mind = won(int(it["price"] * 5)) if it.get("price") else "미정"
            L.append(f"{n}. {it['name']} — 공모가 {won(it.get('price'))}, 최소 증거금 {mind}, {lead(it)}"
                     + (" (오늘 마감)" if last else f" ({md(it['sub_end'])} 마감)"))
    else:
        L.append("오늘은 청약하는 공모주가 없어요.")
    if soon:
        L += ["", "이번 주 예정: " + ", ".join(f"{i['name']} {md(i['sub_start'])}" for i in soon[:5])]
    L += ["", "청약일·환불일·증권사 전체 일정 👉 gongmojuday.com", "※ 정보 제공용이며 투자 권유가 아닙니다.", "", "#공모주"]
    return "\n".join(L)[:490]


def prepare(ipos_path, out_dir, social_path):
    now = datetime.now(S.KST)
    today = now.date()
    stamp = today.strftime("%Y%m%d")
    st = {}
    if os.path.exists(social_path):
        with open(social_path, encoding="utf-8") as f:
            st = json.load(f)
    force = os.path.exists(FORCE_FILE) and open(FORCE_FILE).read().strip() == stamp and st.get("forced") != stamp
    if not force:
        if today.weekday() >= 5 or not (POST_HOUR_KST <= now.hour < 12) or st.get("prepared") == stamp:
            return False
    with open(ipos_path, encoding="utf-8") as f:
        items = json.load(f)["items"]
    now_items, soon = pick(items, today)
    if not now_items and not soon:
        print("오늘·이번 주 청약이 없어 게시하지 않음")
        st["prepared"] = stamp
        json.dump(st, open(social_path, "w"), ensure_ascii=False)
        return False
    tok = token()
    os.makedirs("state", exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        f.write(tok)
    os.chmod(TOKEN_FILE, 0o600)
    rel = f"social/{stamp}.png"
    make_card(now_items, soon, today, os.path.join(out_dir, rel), S._get_font())
    with open(os.path.join(out_dir, "social", "pending.json"), "w", encoding="utf-8") as f:
        json.dump({"date": stamp, "image_url": f"{SITE}/{rel}", "text": caption(now_items, soon, today)}, f, ensure_ascii=False)
    st["prepared"] = stamp
    if force:
        st["forced"] = stamp
    with open(social_path, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    print(f"게시 준비: 오늘 {len(now_items)}개, 이번 주 예정 {len(soon)}개")
    return True


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if cmd == "prepare":
            prepare(sys.argv[2], sys.argv[3], sys.argv[4])
        elif cmd == "post":
            S.TOKEN_FILE = TOKEN_FILE
            S.post(sys.argv[2])
    except urllib.error.HTTPError as e:
        print(f"::error::Threads 실패: {e.code} {e.read().decode()[:300]}")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"::error::SNS 게시 오류: {str(e)[:300]}")
        sys.exit(1)
