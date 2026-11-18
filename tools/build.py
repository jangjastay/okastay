#!/usr/bin/env python3
"""오카맨션 홈페이지 생성기.

data/site.json 을 읽어 모든 HTML·sitemap·config.js 를 다시 만든다.
사용법:  python3 tools/build.py
"""
import json, os, html, datetime, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(os.path.join(ROOT, "data/site.json"), encoding="utf-8"))
S, POL = D["site"], D["policy"]
BASE = ""  # 사용자 도메인(okastay.kr) 연결 기준. github.io/okastay 로 미리보기할 땐 "/okastay"
TODAY = datetime.date.today().isoformat()
PAGES = []  # sitemap용


def e(x):
    return html.escape(str(x), quote=True)


def won(n):
    return f"{n:,}원" if isinstance(n, (int, float)) else "확인 후 안내"


def img(key, alt, cls="", eager=False, sizes="(max-width:720px) 100vw, 50vw"):
    if not key:
        return f'<div class="ph {cls}" role="img" aria-label="{e(alt)}"><span>사진 준비 중</span></div>'
    lazy = "" if eager else 'loading="lazy"'
    return (f'<img class="{cls}" src="{BASE}/assets/img/{key}-s.jpg" '
            f'srcset="{BASE}/assets/img/{key}-s.jpg 720w, {BASE}/assets/img/{key}.jpg 1600w" sizes="{sizes}" '
            f'alt="{e(alt)}" {lazy} decoding="async">')


def room_checkin(r):
    return r.get("checkin") or POL["checkin"], r.get("checkout") or POL["checkout"]


def room_price_text(r):
    p = r["price"]
    if p.get("weekday"):
        return f"평일 {won(p['weekday'])}부터"
    return "요금 문의"


def people_text(r):
    if r.get("base") and r.get("max"):
        return f"기준 {r['base']}인 · 최대 {r['max']}인"
    return "인원 확인 후 안내"


NAV = [("객실", "/rooms/"), ("당일 이용", "/day/"), ("후기", "/reviews.html"), ("사진", "/gallery.html"), ("이용안내", "/guide.html")]


def contact_btns():
    out = []
    if S["phone"]:
        out.append(f'<a class="btn ghost" href="tel:{e(S["phone"])}">전화 문의</a>')
    if S["kakao_channel"]:
        out.append(f'<a class="btn ghost" href="{e(S["kakao_channel"])}" target="_blank" rel="noopener">카카오톡 문의</a>')
    return "".join(out)


def jsonld_business():
    j = {
        "@context": "https://schema.org", "@type": "LodgingBusiness",
        "name": S["name"], "alternateName": [S["brand"], "오카키즈"],
        "url": S["url"], "description": S["description"],
        "image": f'{S["url"]}/assets/img/{S["hero_photo"]}.jpg',
        "address": {"@type": "PostalAddress", "streetAddress": "미원면 운암옥화길 186-16",
                    "addressLocality": "청주시 상당구", "addressRegion": "충청북도", "addressCountry": "KR"},
        "checkinTime": POL["checkin"], "checkoutTime": POL["checkout"],
        "petsAllowed": True,
        "amenityFeature": [{"@type": "LocationFeatureSpecification", "name": n, "value": True}
                           for n in ["애견운동장", "온수풀", "대형 야외수영장", "바베큐", "불멍존", "키즈 놀이시설"]],
    }
    if S["phone"]:
        j["telephone"] = S["phone"]
    if S["lat"] and S["lng"]:
        j["geo"] = {"@type": "GeoCoordinates", "latitude": S["lat"], "longitude": S["lng"]}
    same = [x for x in [S["instagram"], S["instagram_kids"], S.get("youtube_channel")] if x]
    if same:
        j["sameAs"] = same
    return j


def layout(path, title, desc, body, og_img=None, jsonld=None, scripts=(), noindex=False):
    canonical = S["url"] + path
    og = f'{S["url"]}/assets/img/{og_img or S["hero_photo"]}.jpg'
    nav = "".join(f'<a href="{BASE}{h}"{" aria-current=page" if path.startswith(h) and h != "/" else ""}>{t}</a>' for t, h in NAV)
    lds = [jsonld_business()] + (jsonld if isinstance(jsonld, list) else ([jsonld] if jsonld else []))
    verify = ""
    if S["naver_site_verification"]:
        verify += f'<meta name="naver-site-verification" content="{e(S["naver_site_verification"])}">'
    if S["google_site_verification"]:
        verify += f'<meta name="google-site-verification" content="{e(S["google_site_verification"])}">'
    foot_biz = " · ".join(x for x in [
        S["company"], f'대표 {S["ceo"]}' if S["ceo"] else "", f'사업자등록번호 {S["biz_no"]}' if S["biz_no"] else "",
        f'통신판매업 {S["mail_order_no"]}' if S["mail_order_no"] else ""] if x)
    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{e(canonical)}">
<link rel="alternate" type="application/rss+xml" title="{e(S['name'])} 새 글" href="{S['url']}/feed.xml">
{"<meta name=robots content=noindex>" if noindex else ""}
{verify}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(S['name'])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{e(og)}">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#24382c">
<link rel="icon" href="{BASE}/assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="{BASE}/assets/css/style.css">
<script type="application/ld+json">{json.dumps(lds, ensure_ascii=False)}</script>
</head>
<body>
<a class="skip" href="#main">본문 바로가기</a>
<header class="top">
  <div class="wrap top-in">
    <a class="logo" href="{BASE}/" aria-label="{e(S['name'])} 홈"><b>OKA</b><span>오카맨션</span></a>
    <nav class="nav" aria-label="주요 메뉴">{nav}</nav>
    <a class="btn sm" href="{BASE}/reserve.html">예약 신청</a>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="foot">
  <div class="wrap foot-in">
    <div>
      <p class="foot-brand"><b>{e(S['name'])}</b> · {e(S['brand'])}</p>
      <p>{e(S['address'])}</p>
      <p>{e(foot_biz)}</p>
      {f'<p>대표전화 <a href="tel:{e(S["phone"])}">{e(S["phone"])}</a></p>' if S["phone"] else ""}
    </div>
    <div class="foot-links">
      <a href="{BASE}/rooms/">객실</a><a href="{BASE}/day/">당일 이용</a><a href="{BASE}/guide.html#refund">환불규정</a>
      {f'<a href="{e(S["instagram"])}" target="_blank" rel="noopener">인스타그램</a>' if S["instagram"] else ""}
      {f'<a href="{e(S["youtube_channel"])}" target="_blank" rel="noopener">유튜브</a>' if S.get("youtube_channel") else ""}
    </div>
  </div>
</footer>
<a class="fab" href="{BASE}/reserve.html">예약 신청</a>
<script src="{BASE}/assets/js/config.js"></script>
<script src="{BASE}/assets/js/main.js" defer></script>
{"".join(f'<script src="{BASE}/assets/js/{s}" defer></script>' for s in scripts)}
</body>
</html>
"""
    out = path + ("index.html" if path.endswith("/") else "")
    fp = os.path.join(ROOT, out.lstrip("/"))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, "w", encoding="utf-8").write(page)
    if not noindex:
        PAGES.append(path)


# ---------- 조각 ----------
STD = [r["slug"] for r in D["rooms"] if r["group"] == "standard"]


def cover_of(r):
    if not r["photos"]:
        return None
    i = STD.index(r["slug"]) if r["slug"] in STD else 0
    return r["photos"][i % len(r["photos"])]

def room_card(r):
    ci, co = room_checkin(r)
    tags = "".join(f"<li>{e(t)}</li>" for t in r["tags"])
    filt = " ".join(["all", "small"] + (["large"] if r["large_dog"] else []) + (["pool"] if r["pool"] else []) + (["camp"] if r["group"] == "camp" else []) + (["private"] if r["group"] == "private" else []))
    cover = cover_of(r)
    return f"""<article class="card room" data-filter="{filt}">
  <a href="{BASE}/rooms/{r['slug']}.html" class="card-link" aria-label="{e(r['name'])} 자세히 보기"></a>
  <div class="card-img">{img(cover, r['name'] + ' 사진', sizes='(max-width:720px) 100vw, 33vw')}</div>
  <div class="card-body">
    <p class="kicker">{e(r['type'])}</p>
    <h3>{e(r['name'])}</h3>
    <p>{e(r['summary'])}</p>
    <ul class="chips">{tags}</ul>
    <p class="meta">입실 {ci} · 퇴실 {co}<br>{e(people_text(r))}</p>
    <p class="price">{e(room_price_text(r))}</p>
  </div>
</article>"""


def day_card(p):
    cover = p["photos"][0] if p.get("photos") else None
    return f"""<article class="card day">
  <a href="{BASE}/day/{p['slug']}.html" class="card-link" aria-label="{e(p['name'])} 자세히 보기"></a>
  <div class="card-img">{img(cover, p['name'] + ' 사진', sizes='(max-width:720px) 100vw, 33vw')}</div>
  <div class="card-body">
    <p class="kicker">당일 이용</p>
    <h3>{e(p['name'])}</h3>
    <p>{e(p['short'])}</p>
    <p class="price">{e(p['price_text'])}</p>
  </div>
</article>"""


def price_note():
    return "" if D["day_price_confirmed"] else '<p class="note">당일 이용 요금은 현재 게시 금액 기준이며 시즌에 따라 달라질 수 있습니다. 예약 확정 시 최종 금액을 안내드립니다.</p>'


def steps():
    return """<ol class="steps">
  <li><b>1. 예약 신청</b><span>날짜·인원·반려견·옵션을 골라 신청</span></li>
  <li><b>2. 숙소 확인 연락</b><span>빈 객실을 확인해 문자로 안내</span></li>
  <li><b>3. 입금하면 확정</b><span>안내받은 계좌로 입금하면 예약 완료</span></li>
</ol>"""


def gallery_strip(keys, label):
    if not keys:
        return f'<div class="ph wide"><span>{e(label)} 실제 사진 준비 중</span></div>'
    main = img(keys[0], label + " 대표 사진", "g-main", eager=True, sizes="(max-width:720px) 100vw, 60vw")
    rest = "".join(f'<button class="g-thumb" data-full="{BASE}/assets/img/{k}.jpg" aria-label="{e(label)} 사진 {i + 2} 크게 보기">{img(k, f"{label} 사진 {i + 2}", sizes="160px")}</button>' for i, k in enumerate(keys[1:]))
    return f'<div class="gallery-strip"><button class="g-main-btn" data-full="{BASE}/assets/img/{keys[0]}.jpg" aria-label="크게 보기">{main}</button><div class="g-rest">{rest}</div></div>'


def review_cards(items, cls="rv-grid"):
    if not items:
        return ""
    cards = "".join(f'<figure class="review"><blockquote>{e(r["text"])}</blockquote><figcaption>{e(r["who"])} · {("객실 " + e(", ".join(r["rooms"])) + "호 · ") if r.get("rooms") and r["rooms"][0].isdigit() else ("2층 객실 · " if r.get("rooms") == ["std"] else "")}{e(r["when"])} · 네이버 리뷰</figcaption></figure>' for r in items)
    return f'<div class="{cls}">{cards}</div>'


def review_section(items, title, cap=24):
    if not items:
        return ""
    rest = items[6:cap]
    more = f'<details class="rv-more"><summary>후기 {len(rest)}개 더 보기</summary>{review_cards(rest)}</details>' if rest else ""
    return f'<section class="sec"><div class="wrap"><div class="sec-head"><h2>{e(title)}</h2><a class="more" href="{BASE}/reviews.html">후기 전체 보기</a></div>{review_cards(items[:6])}{more}</div></section>'


def breadcrumb(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": S["url"] + u} for i, (n, u) in enumerate(items)]}


# ---------- 이야기(SEO 글) ----------
STORIES = json.load(open(os.path.join(ROOT, "data", "stories.json"), encoding="utf-8"))
LINK_NAMES = {"/rooms/301.html": "301호 단독 애견운동장 객실", "/day/bbq.html": "바베큐 안내", "/reviews.html": "실제 이용 후기",
              "/day/kids.html": "키즈 놀이터 · 물놀이장", "/day/pool.html": "대형 야외수영장", "/day/deck.html": "데크존 · 파라솔존",
              "/day/warm-pool.html": "온수풀 대여", "/day/fire.html": "불멍", "/rooms/": "객실 안내", "/guide.html": "이용안내 · 오시는 길",
              "/reserve.html": "예약 신청", "/gallery.html": "사진", "/day/": "당일 이용", "/day/cafe.html": "카페 · 무인 편의점"}


def story_cards(items):
    return '<div class="story-list">' + "".join(
        f'<a class="story-card" href="{BASE}/story/{s["slug"]}.html">{img(s["cover"], s["h1"])}<div><b>{e(s["h1"])}</b><span>{e(s["desc"][:70])}…</span></div></a>'
        for s in items) + "</div>"


def build_stories():
    topic_map = {"pet": "pet", "kids": "kids", "bbq": "bbq", "winter": "bbq", "local": "kids", "near": "pet"}
    for s in STORIES:
        secs = ""
        for h, t, ph in s["sections"]:
            pics = "".join(img(k, h) for k in ph if k != s["cover"])
            secs += f'<h2>{e(h)}</h2><p>{e(t)}</p>' + (f'<div class="ph">{pics}</div>' if pics else "")
        faq = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in s["faq"])
        tp = topic_map.get(s.get("topic"), s.get("topic"))
        rvs = [r for r in D["reviews"] if tp in r.get("topics", [])][:6]
        names = dict(LINK_NAMES, **{f"/story/{o['slug']}.html": o["h1"] for o in STORIES}, **{f"/dog/{o['slug']}.html": o["name"] + " 여행 가이드" for o in BREEDS})
        links = "".join(f'<li><a href="{BASE}{u}">{e(names.get(u, u))}</a></li>' for u in s.get("links", []))
        srcs = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(t)}</a></li>' for t, u in s.get("sources", []))
        srcs = f'<h2>참고한 자료</h2><ul class="dots">{srcs}</ul><p class="note">운영 시간·요금은 바뀔 수 있으니 방문 전 공식 안내를 확인해 주세요.</p>' if srcs else ""
        others = [o for o in STORIES if o["slug"] != s["slug"]][:3]
        kw = "".join(f"<span>{e(k)}</span>" for k in s["keywords"])
        body = f"""<section class="page-head"><div class="wrap narrow"><p class="eyebrow dark">OKA STORY</p><h1>{e(s['h1'])}</h1><p>{e(s['desc'])}</p></div></section>
<section class="sec pt0"><div class="wrap"><article class="story">{img(s['cover'], s['h1'], eager=True)}{secs}
<h2>자주 묻는 질문</h2><div class="faq">{faq}</div>
<h2>함께 보면 좋아요</h2><ul class="dots">{links}<li><a href="{BASE}/reserve.html">직접 예약 신청</a></li></ul>
{srcs}<div class="kw">{kw}</div></article></div></section>
{review_section(rvs, "실제 이용 후기")}
<section class="sec tint"><div class="wrap"><h2>다른 이야기</h2>{story_cards(others)}</div></section>"""
        ld = [{"@context": "https://schema.org", "@type": "Article", "headline": s["title"], "description": s["desc"],
               "image": [f"{S['url']}/assets/img/{s['cover']}.jpg"], "keywords": ", ".join(s["keywords"]),
               "author": {"@type": "Organization", "name": S["name"]}, "publisher": {"@type": "Organization", "name": S["name"]},
               "mainEntityOfPage": f"{S['url']}/story/{s['slug']}.html", "dateModified": TODAY},
              {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                  {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in s["faq"]]},
              breadcrumb([("홈", "/"), ("이야기", "/story/"), (s["h1"], f"/story/{s['slug']}.html")])]
        layout(f"/story/{s['slug']}.html", s["title"], s["desc"], body, og_img=s["cover"], jsonld=ld)
    body = f"""<section class="page-head"><div class="wrap"><p class="eyebrow dark">OKA STORY</p><h1>오카맨션 이야기</h1>
<p>청주 애견동반 펜션, 아이랑 물놀이, 당일 바베큐 — 오카맨션에서 하루를 보내는 방법을 정리했어요.</p></div></section>
<section class="sec pt0"><div class="wrap">{story_cards(STORIES)}</div></section>"""
    layout("/story/", f"이야기 | {S['name']} 청주 애견동반 · 아이랑 여행 가이드", "청주 애견동반 펜션, 청주 아이랑 갈만한 곳, 청주 당일 바베큐, 옥화구곡 가족여행 가이드.", body)


# ---------- 견종별 여행 가이드 ----------
BREEDS = json.load(open(os.path.join(ROOT, "data", "breeds.json"), encoding="utf-8"))
BREED_PHOTOS = ["pet/lawn", "pet/agility", "pet/dog-pool", "pet/poodles", "pet/amenity", "pet/dog-bbq", "rooms/2f-dog"]


def breed_stay(b):
    lo, hi = b["kg"]
    small = f'<li><a href="{BASE}/rooms/">2층 객실 201~207호</a> — 12kg 미만 소형견은 2마리까지 함께 묵을 수 있어요. (1마리 {won(POL["pet_fee"])})</li>'
    big = f'<li><a href="{BASE}/rooms/301.html">301호 단독 애견운동장 객실</a> — 대형견은 이 객실에서만 가능해요. ({won(POL["large_dog_fee"])}, 사전 문의)</li>'
    if hi < 12:
        return small, f"{b['name']}는 평균 체중이 {lo}~{hi}kg 정도라 오카맨션 전 객실에서 함께 묵을 수 있어요."
    if lo >= 12:
        return big, f"{b['name']}는 평균 체중이 {lo}~{hi}kg 정도로 12kg을 넘는 경우가 많아, 단독 애견운동장이 있는 301호에서 묵을 수 있어요. 예약 전에 꼭 문의해 주세요."
    return small + big, f"{b['name']}는 평균 체중이 {lo}~{hi}kg로 개체마다 달라요. 12kg 미만이면 2층 객실, 그 이상이면 301호를 이용해 주세요."


def build_breeds():
    for i, b in enumerate(BREEDS):
        stay_li, stay_txt = breed_stay(b)
        ph = [BREED_PHOTOS[(i + k) % len(BREED_PHOTOS)] for k in (0, 3)]
        name = b["name"]
        rvs = [r for r in D["reviews"] if name.replace(" ", "")[:3] in r["text"].replace(" ", "")][:6]
        same = [o for o in BREEDS if o["slug"] != b["slug"] and o["size"] == b["size"]][:4] or [o for o in BREEDS if o["slug"] != b["slug"]][:4]
        faq = [(f"{name}와 함께 갈 수 있는 청주 애견동반 펜션이 있나요?", stay_txt + " 반려견 전용 수영장과 인조잔디 애견운동장도 함께 이용할 수 있어요."),
               (f"{name}는 수영을 잘하나요?", b["swim"]),
               (f"{name}와 여행 갈 때 무엇을 챙겨야 하나요?", "사료, 리드줄, 평소 쓰던 담요를 챙기세요. 오카맨션 객실에는 반려견 식기, 배변패드, 침대 계단이 준비돼 있어요. " + b["tips"][0])]
        fq = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
        facts = "".join(f"<tr><th>{k}</th><td>{e(v)}</td></tr>" for k, v in [("영문명", b["en"]), ("원산지", b["origin"]), ("크기", b["size"]),
                         ("평균 체중", f"{b['kg'][0]}~{b['kg'][1]}kg"), ("평균 수명", b["life"]), ("털", b["coat"]), ("활동량", "●" * b["energy"] + "○" * (5 - b["energy"]))])
        body = f"""<section class="page-head"><div class="wrap narrow"><p class="eyebrow dark">견종별 여행 가이드</p><h1>{e(name)} 여행 가이드 — 성격, 역사, 애견동반 펜션 팁</h1>
<p>{e(name)}({e(b['en'])})의 기본 정보와 역사, 함께 여행할 때 알아두면 좋은 점을 정리했어요.</p></div></section>
<section class="sec pt0"><div class="wrap"><article class="story">
<h2>{e(name)} 기본 정보</h2><table class="kv">{facts}</table>
<h2>{e(name)}의 역사</h2><p>{e(b['history'])}</p>
<div class="ph">{"".join(img(k, name + "와 함께하는 애견동반 여행") for k in ph)}</div>
<h2>{e(name)} 성격과 특징</h2><ul class="dots">{"".join(f"<li>{e(t)}</li>" for t in b['traits'])}</ul>
<h2>{e(name)}와 여행할 때 팁</h2><ul class="dots">{"".join(f"<li>{e(t)}</li>" for t in b['tips'])}</ul>
<h2>{e(name)} 물놀이 · 수영</h2><p>{e(b['swim'])} 오카맨션 반려견 전용 수영장은 수심이 얕고, 구명조끼를 빌려 드려요.</p>
<h2>{e(name)}와 오카맨션에서 묵으려면</h2><p>{e(stay_txt)}</p><ul class="dots">{stay_li}</ul>
<h2>자주 묻는 질문</h2><div class="faq">{fq}</div>
<p class="note">일반적인 견종 정보로, 아이마다 체중과 성격은 다를 수 있어요. 건강 문제는 수의사와 상담해 주세요.</p>
<div class="center"><a class="btn lg" href="{BASE}/reserve.html">{e(name)}와 함께 예약 신청</a></div>
</article></div></section>
{review_section(rvs, name + " 보호자 실제 후기") if rvs else ""}
<section class="sec tint"><div class="wrap"><h2>다른 견종 가이드</h2><div class="btn-row">{"".join(f'<a class="btn ghost" href="{BASE}/dog/{o["slug"]}.html">{e(o["name"])}</a>' for o in same)}<a class="btn ghost" href="{BASE}/dog/">전체 견종</a></div></div></section>"""
        ld = [{"@context": "https://schema.org", "@type": "Article", "headline": f"{name} 여행 가이드 — 성격, 역사, 애견동반 펜션 팁",
               "description": f"{name} 기본 정보·역사·여행 팁", "author": {"@type": "Organization", "name": S["name"]},
               "publisher": {"@type": "Organization", "name": S["name"]}, "image": [f"{S['url']}/assets/img/{ph[0]}.jpg"],
               "mainEntityOfPage": f"{S['url']}/dog/{b['slug']}.html", "dateModified": TODAY},
              {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
                  {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
              breadcrumb([("홈", "/"), ("견종별 여행 가이드", "/dog/"), (name, f"/dog/{b['slug']}.html")])]
        layout(f"/dog/{b['slug']}.html", f"{name} 성격·역사·여행 팁 | 애견동반 펜션 가이드 {S['name']}",
               f"{name}({b['en']}) 원산지 {b['origin']}, 평균 {b['kg'][0]}~{b['kg'][1]}kg. 성격과 역사, 수영 가능 여부, 애견동반 펜션 여행 팁을 정리했어요.", body, og_img=ph[0], jsonld=ld)
    groups = ""
    for sz in ["소형", "소형~중형", "중형", "대형"]:
        items = [b for b in BREEDS if b["size"] == sz]
        if items:
            groups += f'<h2>{sz}견</h2><div class="btn-row">' + "".join(f'<a class="btn ghost" href="{BASE}/dog/{b["slug"]}.html">{e(b["name"])}</a>' for b in items) + "</div>"
    body = f"""<section class="page-head"><div class="wrap"><p class="eyebrow dark">DOG GUIDE</p><h1>견종별 여행 가이드</h1>
<p>우리 아이 견종에 맞는 여행 팁, 수영 가능 여부, 함께 묵을 수 있는 객실을 견종별로 정리했어요. 12kg 미만 소형견은 전 객실, 대형견은 301호에서 함께할 수 있어요.</p></div></section>
<section class="sec pt0"><div class="wrap">{groups}</div></section>"""
    layout("/dog/", f"견종별 여행 가이드 | 애견동반 펜션 {S['name']}", "말티즈, 푸들, 포메라니안, 웰시코기, 진돗개, 골든 리트리버 등 견종별 성격·역사·여행 팁과 애견동반 펜션 이용 안내.", body)


# ---------- 메인 ----------
def build_index():
    rooms = "".join(room_card(r) for r in D["rooms"])
    days = "".join(day_card(p) for p in D["day_products"])
    nearby = "".join(f"<li><b>{e(n['name'])}</b><span>{e(n['desc'])}</span></li>" for n in D["nearby"])
    reviews = ""
    mains = [r for r in D["reviews"] if r.get("main")]
    if mains:
        items = "".join(f'<figure class="review"><blockquote>{e(r["text"])}</blockquote><figcaption>{e(r["who"])} · 네이버 리뷰</figcaption></figure>' for r in mains)
        reviews = f'<section class="sec"><div class="wrap"><div class="sec-head"><h2>다녀간 가족들의 이야기</h2><a class="more" href="{BASE}/reviews.html">네이버 리뷰 {D.get("review_total", "")}건+ 보기</a></div></div><div class="marquee"><div class="marquee-track">{items}{items}</div></div></section>'
    faq = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in D["faq"])
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in D["faq"]]}
    body = f"""
<section class="hero">
  {img(S['hero_photo'], '오카맨션 전경 — 수영장과 숲에 둘러싸인 숙소', 'hero-bg', eager=True, sizes='100vw')}
  <div class="hero-shade"></div>
  <div class="wrap hero-in">
    <p class="eyebrow">청주 미원 · 애견동반 · 키즈</p>
    <h1>{e(S['slogan'])},<br>오카맨션</h1>
    <p class="lead">빈손으로 와서 놀고, 먹고, 쉬고.<br>집에 가기 싫으면 자고 가세요.</p>
    <form class="quick" action="{BASE}/reserve.html" method="get" aria-label="빠른 예약">
      <fieldset>
        <legend>오늘 누구와 오세요?</legend>
        <label><input type="radio" name="with" value="kids" checked><span>아이랑</span></label>
        <label><input type="radio" name="with" value="pet"><span>강아지랑</span></label>
        <label><input type="radio" name="with" value="all"><span>가족 모두</span></label>
      </fieldset>
      <fieldset>
        <legend>얼마나 머물까요?</legend>
        <label><input type="radio" name="type" value="day" checked><span>당일</span></label>
        <label><input type="radio" name="type" value="stay"><span>숙박</span></label>
      </fieldset>
      <button class="btn lg" type="submit">날짜 고르기</button>
    </form>
    <div class="hero-cta"><a class="btn lg" href="{BASE}/reserve.html">예약 문의</a><a class="btn lg ghost light" href="tel:{e(S['phone'])}">전화 문의</a></div>
  </div>
</section>

<section class="sec"><div class="wrap narrow center"><p class="eyebrow dark">VIDEO</p><h2>영상으로 먼저 둘러보기</h2>
<div class="video" data-yt="{e(S['youtube_video'])}"><img src="https://i.ytimg.com/vi/{e(S['youtube_video'])}/hqdefault.jpg" alt="오카맨션 애견동반 펜션 소개 영상" loading="lazy"><button class="play" aria-label="오카맨션 소개 영상 재생">▶</button></div></div></section>

<section class="sec why">
  <div class="wrap">
    <h2>준비하지 마세요. 저희가 해둘게요.</h2>
    <div class="grid3">
      <div class="why-i"><b>ZERO PREP</b><h3>짐 싸지 않아도 돼요</h3><p>바베큐 세트를 신청하면 장보기 없이 바로 구울 수 있어요. 캠핑스테이는 텐트도 장비도 필요 없습니다.</p></div>
      <div class="why-i"><b>NO 눈치</b><h3>아이도 강아지도 마음껏</h3><p>애견운동장과 아이 물놀이 공간이 따로 있어요. 서로 눈치 보지 않고 각자 신나게 놀아요.</p></div>
      <div class="why-i"><b>SLEEP OPTIONAL</b><h3>자고 갈지는 나중에</h3><p>하루 놀다 아이가 잠들면, 빈 객실이 있을 때 숙박으로 바꿀 수 있어요.</p></div>
    </div>
  </div>
</section>

<section class="sec" id="rooms">
  <div class="wrap">
    <div class="sec-head"><h2>객실</h2><a class="more" href="{BASE}/rooms/">전체 보기</a></div>
    <div class="filters" role="group" aria-label="객실 거르기">
      <button class="chip on" data-f="all">전체</button>
      <button class="chip" data-f="small">소형견 동반</button>
      <button class="chip" data-f="large">대형견 가능</button>
      <button class="chip" data-f="private">독채</button>
      <button class="chip" data-f="pool">개별 수영장</button>
      <button class="chip" data-f="camp">캠핑스테이</button>
    </div>
    <div class="grid cards" data-filter-grid>{rooms}</div>
  </div>
</section>

<section class="sec tint" id="day">
  <div class="wrap">
    <div class="sec-head"><h2>숙박 없이, 하루만</h2><a class="more" href="{BASE}/day/">당일 이용 안내</a></div>
    <div class="grid cards">{days}</div>
    {price_note()}
  </div>
</section>

<section class="sec route">
  <div class="wrap split">
    <div>
      <p class="eyebrow dark">옥화·미원 가족여행 베이스캠프</p>
      <h2>옥화에서 놀고, 오카에서 쉬세요</h2>
      <ol class="timeline">
        <li><b>오전</b>옥화구곡 · 청석굴 · 미동산수목원 산책</li>
        <li><b>오후</b>오카 도착 — 수영장 · 애견운동장 · 데크존</li>
        <li><b>저녁</b>바베큐 · 노을 · 불멍</li>
        <li><b>밤</b>자고 가거나, 가볍게 귀가</li>
      </ol>
    </div>
    <div>
      <h3 class="small-h">근처 가볼 만한 곳</h3>
      <ul class="nearby">{nearby}</ul>
    </div>
  </div>
</section>

{reviews}

<section class="sec tint">
  <div class="wrap">
    <h2>홈페이지 직접 예약은 이렇게</h2>
    {steps()}
    <div class="center"><a class="btn lg" href="{BASE}/reserve.html">예약 신청하기</a> {contact_btns()}</div>
  </div>
</section>

<section class="sec">
  <div class="wrap"><div class="sec-head"><h2>오카맨션 이야기</h2><a class="more" href="{BASE}/story/">전체 보기</a></div>
  {story_cards(STORIES)}<p class="center" style="margin-top:20px"><a class="btn ghost" href="{BASE}/dog/">견종별 여행 가이드 30종 보기</a></p></div>
</section>

<section class="sec">
  <div class="wrap narrow">
    <h2>자주 묻는 질문</h2>
    <div class="faq">{faq}</div>
  </div>
</section>

<section class="sec tint" id="map">
  <div class="wrap split">
    <div>
      <h2>오시는 길</h2>
      <p class="addr">{e(S['address'])}</p>
      <p>옥화구곡 · 청석굴 · 옥화자연휴양림 인근</p>
      <div class="btn-row">
        <a class="btn ghost" href="https://map.naver.com/p/search/{e(S['address'])}" target="_blank" rel="noopener">네이버 지도</a>
        <a class="btn ghost" href="https://map.kakao.com/?q={e(S['address'])}" target="_blank" rel="noopener">카카오맵</a>
      </div>
    </div>
    <div>{img('site/front', '오카맨션 입구', 'rounded')}</div>
  </div>
</section>
"""
    layout("/", f"{S['name']} | 청주 애견동반 펜션 · 키즈 수영장 · 당일 바베큐 — {S['slogan']}", S["description"], body,
           jsonld=faq_ld)


# ---------- 객실 ----------
def build_rooms():
    cards = "".join(room_card(r) for r in D["rooms"])
    body = f"""<section class="page-head"><div class="wrap"><p class="eyebrow dark">ROOMS</p><h1>객실 안내</h1>
<p>전 객실 반려견 동반. 2층 객실(201~207호)부터 단독 애견운동장 301호, 독채, 장비 없이 자는 캠핑스테이까지.</p></div></section>
<section class="sec"><div class="wrap">
<div class="filters" role="group" aria-label="객실 거르기">
<button class="chip on" data-f="all">전체</button><button class="chip" data-f="small">소형견 동반</button><button class="chip" data-f="large">대형견 가능</button>
<button class="chip" data-f="private">독채</button><button class="chip" data-f="pool">개별 수영장</button><button class="chip" data-f="camp">캠핑스테이</button></div>
<div class="grid cards" data-filter-grid>{cards}</div>
<div class="box"><h3>모든 객실 공통</h3><ul class="dots">
<li>입실 {POL['checkin']} · 퇴실 {POL['checkout']} (독채 2호 입실 17:00 · 캠핑스테이 입실 18:00 / 퇴실 09:00)</li>
<li>{e(POL['pet_rule'])} · {e(POL['large_dog_rule'])}</li>
<li>기준 인원 초과 시 1인 {won(POL['extra_person_fee'])} · {e(POL['infant_rule'])}</li></ul></div>
</div></section>"""
    layout("/rooms/", f"객실 안내 | {S['name']} 청주 애견동반 펜션", "오카맨션 객실 12개 — 2층 애견동반 객실, 대형견 가능한 301호(단독 애견운동장), 독채, 개별 수영장 독채, 캠핑스테이.", body,
           jsonld=breadcrumb([("홈", "/"), ("객실", "/rooms/")]))

    for r in D["rooms"]:
        ci, co = room_checkin(r)
        p = r["price"]
        price_rows = "".join(f"<tr><th>{k}</th><td>{won(p.get(v))}</td></tr>" for k, v in [("평일", "weekday"), ("주말·공휴일 전날", "weekend"), ("성수기", "peak")])
        feats = "".join(f"<li>{e(f)}</li>" for f in r["features"]) or "<li>상세 구성은 문의 주시면 안내드립니다.</li>"
        pet = POL["large_dog_rule"] if r["large_dog"] else POL["pet_rule"]
        same = [o for o in D["rooms"] if o["slug"] != r["slug"]][:3]
        body = f"""<section class="page-head"><div class="wrap">
<nav class="crumb"><a href="{BASE}/">홈</a> › <a href="{BASE}/rooms/">객실</a> › {e(r['name'])}</nav>
<p class="eyebrow dark">{e(r['type'])}</p><h1>{e(r['name'])}</h1><p>{e(r['summary'])}</p></div></section>
<section class="sec pt0"><div class="wrap split detail">
<div>{gallery_strip(r['photos'][STD.index(r['slug']) % len(r['photos']):] + r['photos'][:STD.index(r['slug']) % len(r['photos'])] if r['slug'] in STD else r['photos'], r['name'])}{'<p class="note">201~207호는 구조가 같아 2층 객실 사진을 함께 보여드립니다.</p>' if r['slug'] in STD else ''}</div>
<aside class="side">
  <ul class="chips">{''.join(f'<li>{e(t)}</li>' for t in r['tags'])}</ul>
  <table class="kv"><tr><th>입실 / 퇴실</th><td>{ci} / {co}</td></tr><tr><th>인원</th><td>{e(people_text(r))}</td></tr>
  <tr><th>반려견</th><td>{e(pet)}</td></tr></table>
  <h3 class="small-h">1박 요금</h3><table class="kv">{price_rows}</table>
  <p class="note">요금이 비어 있으면 날짜별로 확인 후 안내드립니다. 추가 인원 1인 {won(POL['extra_person_fee'])} · {e(POL['infant_rule'])}</p>
  <a class="btn lg block" href="{BASE}/reserve.html?type=stay&room={r['slug']}">{e(r['name'])} 예약 신청</a>
  <div class="btn-row">{contact_btns()}</div>
</aside></div></section>
<section class="sec tint"><div class="wrap split">
<div><h2>이 객실의 특징</h2><ul class="dots">{feats}</ul></div>
<div><h2>함께 즐기면 좋아요</h2><ul class="dots">
<li><a href="{BASE}/day/bbq.html">바베큐</a> — 간편 고기세트 신청 시 장보기 없이</li>
<li><a href="{BASE}/day/fire.html">불멍존</a> — 불멍세트 {won(15000)}</li>
<li><a href="{BASE}/day/warm-pool.html">온수풀</a> — 2시간 프라이빗 대여</li></ul></div>
</div></section>
{review_section([x for x in D["reviews"] if r["slug"] in x.get("rooms", [])] + ([x for x in D["reviews"] if x.get("rooms") == ["std"]][(int(r["slug"]) - 201) * 3:] if r["group"] == "standard" else []), r["name"] + " · 2층 객실 다녀간 손님 후기" if r["group"] == "standard" else r["name"] + " 다녀간 손님 후기")}
<section class="sec"><div class="wrap"><h2>다른 객실</h2><div class="grid cards">{''.join(room_card(o) for o in same)}</div></div></section>"""
        ld = {"@context": "https://schema.org", "@type": "HotelRoom", "name": f"{S['name']} {r['name']}", "description": r["summary"],
              "url": f"{S['url']}/rooms/{r['slug']}.html", "petsAllowed": True}
        if r["photos"]:
            ld["image"] = [f"{S['url']}/assets/img/{k}.jpg" for k in r["photos"]]
        layout(f"/rooms/{r['slug']}.html", f"{r['name']} — {r['summary']} | {S['name']} 청주 애견펜션",
               f"오카맨션 {r['name']}: {r['summary']}. 입실 {ci}, 퇴실 {co}. {pet}.", body,
               og_img=r["photos"][0] if r["photos"] else None,
               jsonld=[ld, breadcrumb([("홈", "/"), ("객실", "/rooms/"), (r["name"], f"/rooms/{r['slug']}.html")])])


# ---------- 당일 ----------
def build_day():
    cards = "".join(day_card(p) for p in D["day_products"])
    body = f"""<section class="page-head"><div class="wrap"><p class="eyebrow dark">DAY</p><h1>당일 이용</h1>
<p>숙박하지 않아도 괜찮아요. 수영장, 데크존, 바베큐, 불멍까지 하루만 즐기고 가세요.</p></div></section>
<section class="sec"><div class="wrap"><div class="grid cards">{cards}</div>{price_note()}
<div class="box"><h3>하루 추천 코스</h3><ol class="timeline">
<li><b>13:00</b>도착 · 데크존 자리 잡기</li><li><b>14:00</b>수영장 / 온수풀 2시간</li>
<li><b>17:00</b>바베큐 세트로 저녁</li><li><b>19:00</b>노을 보고 불멍</li><li><b>20:30</b>귀가 — 또는 숙박으로 전환</li></ol></div>
</div></section>"""
    layout("/day/", f"당일 이용 | 청주 당일 수영장 · 바베큐 · 불멍 — {S['name']}", "청주 미원 오카맨션 당일 이용: 온수풀 대여, 대형수영장, 데크·파라솔존, 바베큐, 불멍존. 숙박 없이 아이·반려견과 하루 놀다 가세요.", body,
           jsonld=breadcrumb([("홈", "/"), ("당일 이용", "/day/")]))
    for p in D["day_products"]:
        det = "".join(f"<li>{e(x)}</li>" for x in p["detail"])
        kw = " · ".join(p["keywords"])
        others = [o for o in D["day_products"] if o["slug"] != p["slug"]][:3]
        body = f"""<section class="page-head"><div class="wrap">
<nav class="crumb"><a href="{BASE}/">홈</a> › <a href="{BASE}/day/">당일 이용</a> › {e(p['name'])}</nav>
<p class="eyebrow dark">당일 이용</p><h1>{e(p['name'])}</h1><p>{e(p['short'])}</p></div></section>
<section class="sec pt0"><div class="wrap split detail">
<div>{gallery_strip(p.get('photos', []), p['name'])}</div>
<aside class="side">
  <h3 class="small-h">요금</h3><p class="price big">{e(p['price_text'])}</p>
  <ul class="dots">{det}</ul>
  {price_note()}
  <a class="btn lg block" href="{BASE}/reserve.html?type=day&product={p['slug']}">{e(p['name'])} 예약 신청</a>
  <div class="btn-row">{contact_btns()}</div>
</aside></div></section>
{review_section([x for x in D["reviews"] if p["slug"] in x.get("topics", [])], p["name"] + " 이용 후기")}
<section class="sec tint"><div class="wrap"><h2>함께 이용하면 좋은 것</h2><div class="grid cards">{''.join(day_card(o) for o in others)}</div>
<p class="kw">{e(kw)}</p></div></section>"""
        ld = {"@context": "https://schema.org", "@type": "Service", "name": f"{S['name']} {p['name']}", "description": p["short"],
              "provider": {"@type": "LodgingBusiness", "name": S["name"], "url": S["url"]}, "areaServed": "청주"}
        layout(f"/day/{p['slug']}.html", f"{p['name']} | {p['keywords'][0]} — {S['name']}",
               f"오카맨션 {p['name']}: {p['short']}. {p['price_text']}. {kw}.", body,
               og_img=p["photos"][0] if p.get("photos") else None,
               jsonld=[ld, breadcrumb([("홈", "/"), ("당일 이용", "/day/"), (p["name"], f"/day/{p['slug']}.html")])])


# ---------- 사진·이벤트 ----------
def build_gallery():
    tiles = "".join(f'<button class="tile" data-full="{BASE}/assets/img/{k}.jpg" aria-label="{e(label)} 크게 보기">{img(k, label, sizes="(max-width:720px) 50vw, 25vw")}<span>{e(label)}</span></button>' for label, k in D["gallery"])
    ev = ""
    for v in D["events"]:
        if not (v["photos"] or v["desc"]):
            continue
        ev += f'<article class="event"><div class="ev-imgs">{"".join(img(k, v["name"]) for k in v["photos"][:3])}</div><h3>{e(v["name"])}</h3><p class="meta">{e(v["when"])}</p><p>{e(v["desc"])}</p></article>'
    ev_sec = f'<section class="sec tint"><div class="wrap"><h2>지난 이벤트</h2><div class="grid">{ev}</div></div></section>' if ev else ""
    body = f"""<section class="page-head"><div class="wrap"><p class="eyebrow dark">PHOTOS</p><h1>사진</h1>
<p>보정이나 합성 없이 실제 오카맨션 모습 그대로 담았습니다.</p></div></section>
<section class="sec pt0"><div class="wrap"><div class="masonry">{tiles}</div></div></section>{ev_sec}
<section class="sec"><div class="wrap narrow center"><h2>영상으로 보기</h2>
<div class="video" data-yt="{e(S['youtube_video'])}"><img src="https://i.ytimg.com/vi/{e(S['youtube_video'])}/hqdefault.jpg" alt="오카맨션 소개 영상" loading="lazy"><button class="play" aria-label="영상 재생">▶</button></div>
<div class="btn-row center">{f'<a class="btn ghost" href="{e(S["youtube_channel"])}" target="_blank" rel="noopener">유튜브 채널</a>' if S.get("youtube_channel") else ""}<a class="btn ghost" href="{e(S['instagram'])}" target="_blank" rel="noopener">인스타그램 @stay_oka</a></div></div></section>"""
    layout("/gallery.html", f"사진 · 영상 | {S['name']}", "오카맨션 실제 사진 — 객실, 애견운동장, 온수풀, 대형수영장, 데크존, 바베큐, 불멍존.", body)


# ---------- 이용안내 ----------
def build_guide():
    refund = "".join(f"<tr><th>{e(a)}</th><td>{e(b)}</td></tr>" for a, b in POL["refund"])
    addons = "".join(f"<tr><th>{e(a['name'])}</th><td>{won(a['price'])}</td></tr>" for a in D["addons"])
    bank = ""
    if S["bank"]["account"]:
        bank = f'<p>입금 계좌: <b>{e(S["bank"]["name"])} {e(S["bank"]["account"])}</b> (예금주 {e(S["bank"]["holder"])})</p>'
    body = f"""<section class="page-head"><div class="wrap"><p class="eyebrow dark">GUIDE</p><h1>이용안내</h1></div></section>
<section class="sec pt0"><div class="wrap grid2">
<div class="box"><h2>입·퇴실</h2><table class="kv">
<tr><th>일반 객실</th><td>입실 {POL['checkin']} · 퇴실 {POL['checkout']}</td></tr>
<tr><th>독채 2호</th><td>입실 17:00 · 퇴실 {POL['checkout']}</td></tr>
<tr><th>캠핑스테이</th><td>입실 18:00 · 퇴실 09:00</td></tr></table></div>
<div class="box"><h2>반려견</h2><ul class="dots"><li>{e(POL['pet_rule'])}</li><li>{e(POL['large_dog_rule'])}</li>
<li>공용 공간에서는 리드줄을 해주세요.</li><li>배변 봉투를 지참해 주세요.</li></ul></div>
<div class="box"><h2>인원</h2><ul class="dots"><li>기준 인원 초과 시 1인 {won(POL['extra_person_fee'])}</li><li>{e(POL['infant_rule'])}</li></ul></div>
<div class="box"><h2>부대시설 요금</h2><table class="kv">{addons}</table></div>
<div class="box" id="pay"><h2>예약 · 결제</h2>{steps()}<p>입금 전에는 예약이 확정되지 않습니다. 확인 연락 후 안내드린 시간 안에 입금해 주세요.</p>{bank}</div>
<div class="box" id="refund"><h2>환불 규정</h2><table class="kv">{refund}</table><p class="note">{e(POL['refund_note'])}</p></div>
</div></section>"""
    layout("/guide.html", f"이용안내 · 환불규정 | {S['name']}", "오카맨션 입퇴실 시간, 반려견 동반 규정, 추가 인원 요금, 부대시설 요금, 예약·결제 방법, 환불 규정.", body)


# ---------- 예약 ----------
def build_reserve():
    room_opts = "".join(f'<option value="{r["slug"]}" data-large="{1 if r["large_dog"] else 0}">{e(r["name"])} — {e(r["summary"])}</option>' for r in D["rooms"])
    day_opts = "".join(f'<option value="{p["slug"]}">{e(p["name"])} ({e(p["price_text"])})</option>' for p in D["day_products"])
    addons = "".join(f'<label class="check"><input type="checkbox" name="addons" value="{a["id"]}"><span>{e(a["name"])} <em>{won(a["price"])}</em></span></label>' for a in D["addons"])
    body = f"""<section class="page-head"><div class="wrap"><p class="eyebrow dark">RESERVATION</p><h1>예약 신청</h1>
<p>신청 → 숙소 확인 연락 → 입금하면 확정. 결제는 확인 연락 후에 합니다.</p></div></section>
<section class="sec pt0"><div class="wrap split reserve">
<form id="rsv" novalidate>
  <div class="step"><h2>1. 이용 방식</h2>
    <div class="seg"><label><input type="radio" name="type" value="stay" checked><span>숙박</span></label><label><input type="radio" name="type" value="day"><span>당일 이용</span></label></div>
    <div class="seg"><label><input type="radio" name="with" value="kids"><span>아이랑</span></label><label><input type="radio" name="with" value="pet" checked><span>강아지랑</span></label><label><input type="radio" name="with" value="all"><span>가족 모두</span></label></div>
  </div>
  <div class="step"><h2>2. 객실 / 상품</h2>
    <label class="field only-stay">객실<select name="room" required>{room_opts}</select></label>
    <label class="field only-day">당일 상품<select name="product">{day_opts}</select></label>
    <label class="field only-day">희망 시간<input name="time" placeholder="예: 14:00 ~ 16:00"></label>
  </div>
  <div class="step"><h2>3. 날짜</h2>
    <div id="cal" class="cal" aria-live="polite"></div>
    <p class="cal-legend"><i class="lg-sel"></i>선택 <i class="lg-off"></i>마감 · 확인중</p>
    <p id="dateText" class="date-text">달력에서 날짜를 골라주세요.</p>
  </div>
  <div class="step"><h2>4. 인원 · 반려견</h2>
    <div class="nums">
      <label class="num">성인<input type="number" name="adults" min="1" max="12" value="2"></label>
      <label class="num">어린이<input type="number" name="kids" min="0" max="10" value="0"></label>
      <label class="num">36개월 미만<input type="number" name="infants" min="0" max="5" value="0"></label>
      <label class="num">소형견<input type="number" name="dogs" min="0" max="2" value="1"></label>
      <label class="num">대형견<input type="number" name="bigdogs" min="0" max="2" value="0"></label>
    </div>
    <p class="note" id="petNote">{e(POL['pet_rule'])}. {e(POL['large_dog_rule'])}.</p>
  </div>
  <div class="step"><h2>5. 추가 옵션</h2><div class="checks">{addons}</div></div>
  <div class="step"><h2>6. 예약자</h2>
    <label class="field">이름<input name="name" required autocomplete="name"></label>
    <label class="field">휴대폰<input name="phone" required inputmode="tel" autocomplete="tel" placeholder="010-0000-0000"></label>
    <label class="field">요청사항<textarea name="memo" rows="3" placeholder="반려견 견종·몸무게, 도착 예정 시간 등"></textarea></label>
    <label class="check agree"><input type="checkbox" name="agree" required><span>개인정보(이름·연락처)를 예약 확인 목적으로 수집하고 이용 후 1년 내 파기하는 데 동의합니다. 환불 규정을 확인했습니다.</span></label>
  </div>
  <input type="text" name="website" class="hp" tabindex="-1" autocomplete="off" aria-hidden="true">
</form>
<aside class="side sticky">
  <h2>예상 금액</h2>
  <table class="kv" id="sum"></table>
  <p class="total"><span>합계</span><b id="total">-</b></p>
  <p class="note" id="sumNote"></p>
  <button class="btn lg block" id="submitBtn" form="rsv" type="submit">예약 신청하기</button>
  <p class="note">신청만으로는 확정되지 않아요. 확인 후 문자로 연락드립니다.</p>
  <div id="result" class="result" hidden></div>
  <p class="note"><a href="{BASE}/guide.html#refund">환불 규정 보기</a></p>
</aside>
</div></section>"""
    layout("/reserve.html", f"예약 신청 | {S['name']}", "오카맨션 직접 예약 신청 — 숙박·당일 이용, 반려견·인원·옵션 요금 자동 계산.", body, scripts=("reserve.js",))


def build_reviews():
    groups = [("반려견과 함께", lambda r: any(k in r["text"] for k in ["강아지", "반려", "애견", "댕댕"])),
              ("아이와 물놀이", lambda r: "pool" in r["topics"] or "warm-pool" in r["topics"]),
              ("바비큐 · 데크", lambda r: "bbq" in r["topics"] or "deck" in r["topics"])]
    used, secs = set(), ""
    for title, f in groups:
        items = [r for i, r in enumerate(D["reviews"]) if i not in used and f(r)]
        used |= {i for i, r in enumerate(D["reviews"]) if r in items}
        if items:
            secs += f'<section class="sec pt0"><div class="wrap"><h2>{e(title)}</h2>{review_cards(items)}</div></section>'
    rest = [r for i, r in enumerate(D["reviews"]) if i not in used]
    if rest:
        secs += f'<section class="sec pt0"><div class="wrap"><h2>객실 · 휴식</h2>{review_cards(rest)}</div></section>'
    body = f"""<section class="page-head"><div class="wrap"><p class="eyebrow dark">REVIEWS</p><h1>다녀간 손님 후기</h1>
<p>네이버에 남겨주신 후기 {D.get('review_total', '')}여 건 중 일부를 원문 그대로 옮겼습니다. 아이디는 일부 가렸어요.</p></div></section>{secs}
<section class="sec tint"><div class="wrap narrow center"><h2>다음 후기의 주인공이 되어주세요</h2><a class="btn lg" href="{BASE}/reserve.html">예약 신청</a> {contact_btns()}</div></section>"""
    layout("/reviews.html", f"후기 | {S['name']} 청주 애견동반 펜션 실제 이용 후기", "오카맨션 실제 네이버 이용 후기 — 반려견 동반 숙박, 아이 물놀이, 바비큐, 301호 단독 애견운동장 후기.", body)


def build_misc():
    body = f"""<section class="page-head"><div class="wrap narrow center"><h1>페이지를 찾을 수 없어요</h1>
<p>주소가 바뀌었거나 없는 페이지입니다.</p><div class="btn-row center"><a class="btn" href="{BASE}/">처음으로</a><a class="btn ghost" href="{BASE}/reserve.html">예약 신청</a></div></div></section>"""
    layout("/404.html", f"페이지 없음 | {S['name']}", S["description"], body, noindex=True)

    # config.js — 화면 스크립트가 쓰는 값
    cfg = {"appsScriptUrl": S["apps_script_url"], "phone": S["phone"], "kakao": S["kakao_channel"],
           "bank": S["bank"], "policy": POL, "rooms": D["rooms"], "dayProducts": D["day_products"],
           "addons": D["addons"], "dayPriceConfirmed": D["day_price_confirmed"]}
    open(os.path.join(ROOT, "assets/js/config.js"), "w", encoding="utf-8").write(
        "/* tools/build.py 가 data/site.json 으로 자동 생성 — 직접 고치지 마세요 */\nwindow.OKA=" + json.dumps(cfg, ensure_ascii=False) + ";\n")

    urls = "".join(
        f"<url><loc>{S['url']}{p}</loc><lastmod>{TODAY}</lastmod><priority>{'1.0' if p == '/' else '0.8' if p.count('/') == 2 and p.endswith('/') else '0.7'}</priority></url>\n"
        for p in PAGES)
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    open(os.path.join(ROOT, "robots.txt"), "w").write(f"User-agent: *\nAllow: /\nDisallow: /tools/\nDisallow: /apps-script/\nDisallow: /docs/\nDisallow: /data/\n\nSitemap: {S['url']}/sitemap.xml\n" + (f"\n{S['daum_webmaster']}\n" if S.get("daum_webmaster") else ""))
    open(os.path.join(ROOT, "CNAME"), "w").write(S["domain"] + "\n")
    if S.get("indexnow_key"):
        open(os.path.join(ROOT, S["indexnow_key"] + ".txt"), "w").write(S["indexnow_key"])
    import email.utils
    items = [(x["date"], x["h1"], f"/story/{x['slug']}.html", x["desc"]) for x in STORIES] + \
            [(x["date"], x["name"] + " 여행 가이드 — 성격, 역사, 애견동반 펜션 팁", f"/dog/{x['slug']}.html", x["history"][:120]) for x in BREEDS]
    items.sort(key=lambda t: t[0], reverse=True)

    def rfc(dt):
        y, m, d_ = map(int, dt.split("-"))
        return email.utils.format_datetime(datetime.datetime(y, m, d_, 9, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=9))))
    rss = "".join(f"<item><title>{e(t)}</title><link>{S['url']}{u}</link><guid>{S['url']}{u}</guid><pubDate>{rfc(dt)}</pubDate><description>{e(ds)}</description></item>\n" for dt, t, u, ds in items[:50])
    open(os.path.join(ROOT, "feed.xml"), "w", encoding="utf-8").write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel><title>{e(S["name"])} — 청주 애견동반 펜션 이야기</title><link>{S["url"]}/</link><description>{e(S["description"])}</description><language>ko</language>\n{rss}</channel></rss>\n')
    open(os.path.join(ROOT, ".nojekyll"), "w").write("")


if __name__ == "__main__":
    os.makedirs(os.path.join(ROOT, "assets/js"), exist_ok=True)
    build_index(); build_rooms(); build_day(); build_gallery(); build_guide(); build_reserve(); build_reviews(); build_stories(); build_breeds(); build_misc()
    print(f"{len(PAGES)} pages built")
