#!/usr/bin/env python3
"""Stage 1 of the Wix blog migration: fetch every post page and keep only what we need.

Reads blog-posts-sitemap.xml from the old site, fetches each post page and writes
  _probe/wix-posts.json   one record per post (title, date, cover, categories, body HTML)
  _probe/wix-images.json  size and type of every image the posts use (HEAD requests only)
  _probe/SUMMARY.txt      counts and the kinds of content found, to check the converter against
Nothing is downloaded except the pages themselves.
"""
import json
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

BASE = "https://www.nanamilatic.com"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
OUT = "_probe"


def get(url, tries=4, **kw):
    for i in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=60, **kw)
            if r.status_code == 200:
                return r
            err = "HTTP %s" % r.status_code
        except Exception as e:  # noqa: BLE001
            err = str(e)
        time.sleep(1.5 * (i + 1))
    raise RuntimeError("%s: %s" % (url, err))


def media_id(url):
    m = re.search(r"/media/([^/?#]+)", url or "")
    return m.group(1) if m else None


def parse_post(url, lastmod):
    html = get(url).text
    soup = BeautifulSoup(html, "lxml")
    rec = {"url": url, "slug": unquote(url.split("/post/", 1)[1]).strip("/"), "lastmod": lastmod}

    ld = None
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            d = json.loads(s.string or "")
        except Exception:  # noqa: BLE001
            continue
        if isinstance(d, dict) and d.get("@type") == "BlogPosting":
            ld = d
            break
    rec["ld_ok"] = bool(ld)
    h1 = soup.select_one('h1[data-hook="post-title"]')
    rec["title"] = (h1.get_text(" ", strip=True) if h1 else (ld or {}).get("headline", "")).strip()
    rec["datePublished"] = (ld or {}).get("datePublished") or (soup.find("meta", property="article:published_time") or {}).get("content")
    cover = ((ld or {}).get("image") or {}).get("url") or (soup.find("meta", property="og:image") or {}).get("content")
    rec["cover"] = media_id(cover)
    rec["description"] = (ld or {}).get("description", "")

    cats = []
    footer = soup.select_one('footer[data-hook="post-footer"]')
    if footer:
        for a in footer.select('a[href*="/categories/"]'):
            cats.append({"slug": a["href"].rstrip("/").split("/")[-1], "label": a.get_text(strip=True)})
    rec["categories"] = cats

    body = soup.select_one('section[data-hook="post-description"]')
    if body:
        for t in body.find_all(["script", "style", "svg", "button"]):
            t.decompose()
        rec["body_html"] = str(body)
    else:
        rec["body_html"] = ""
    # hero section (cover shown above the title) if present
    hero = soup.select_one('section[data-hook="post-hero-image"]')
    rec["hero_has_image"] = bool(hero and hero.find("img"))
    return rec


def body_media_ids(body_html):
    ids = []
    for m in re.finditer(r"data-image-info=\"([^\"]+)\"", body_html):
        try:
            info = json.loads(unescape(m.group(1)))
            uri = (info.get("imageData") or {}).get("uri")
            if uri and not uri.startswith("http"):
                ids.append(uri)
        except Exception:  # noqa: BLE001
            pass
    return ids


def head(mid):
    url = "https://static.wixstatic.com/media/" + mid
    try:
        r = requests.head(url, headers=UA, timeout=60, allow_redirects=True)
        return mid, {"status": r.status_code, "bytes": int(r.headers.get("Content-Length", 0)), "type": r.headers.get("Content-Type", "")}
    except Exception as e:  # noqa: BLE001
        return mid, {"status": 0, "error": str(e)}


def main():
    sm = get(BASE + "/blog-posts-sitemap.xml").text
    entries = re.findall(r"<url>\s*<loc>(.*?)</loc>\s*(?:<lastmod>(.*?)</lastmod>)?", sm, re.S)
    entries = [(unescape(u), lm) for u, lm in entries if "/post/" in u]
    print("posts in sitemap:", len(entries))

    posts, errors = [], []

    def work(e):
        try:
            time.sleep(0.15)
            return parse_post(*e)
        except Exception as ex:  # noqa: BLE001
            return {"url": e[0], "error": str(ex)}

    with ThreadPoolExecutor(max_workers=4) as pool:
        for rec in pool.map(work, entries):
            (errors if "error" in rec else posts).append(rec)
    posts.sort(key=lambda r: r.get("datePublished") or "", reverse=True)

    # images
    ids = set()
    for p in posts:
        if p["cover"]:
            ids.add(p["cover"])
        p["body_images"] = body_media_ids(p["body_html"])
        ids.update(p["body_images"])
    with ThreadPoolExecutor(max_workers=8) as pool:
        images = dict(pool.map(head, sorted(ids)))

    import os
    os.makedirs(OUT, exist_ok=True)
    json.dump(posts, open(OUT + "/wix-posts.json", "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(images, open(OUT + "/wix-images.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # summary
    L = []
    L.append("posts fetched: %d, errors: %d" % (len(posts), len(errors)))
    for e in errors[:10]:
        L.append("  ERROR %s" % e)
    L.append("without JSON-LD: %d | without cover: %d | without body: %d | hero image present: %d" % (
        sum(1 for p in posts if not p["ld_ok"]), sum(1 for p in posts if not p["cover"]),
        sum(1 for p in posts if not p["body_html"]), sum(1 for p in posts if p["hero_has_image"])))
    L.append("categories (slug/label): %s" % Counter((c["slug"], c["label"]) for p in posts for c in p["categories"]).most_common())
    L.append("posts with 0/1/2+ categories: %s" % Counter(min(len(p["categories"]), 2) for p in posts))
    L.append("cover equals first inline image: %d of %d with both" % (
        sum(1 for p in posts if p["cover"] and p["body_images"] and p["cover"] == p["body_images"][0]),
        sum(1 for p in posts if p["cover"] and p["body_images"])))
    L.append("posts with inline images: %d, total inline: %d" % (sum(1 for p in posts if p["body_images"]), sum(len(p["body_images"]) for p in posts)))
    tags, types, styles, hooks = Counter(), Counter(), Counter(), Counter()
    for p in posts:
        b = BeautifulSoup(p["body_html"], "lxml")
        for t in b.find_all(True):
            tags[t.name] += 1
            if t.get("type"):
                types[t["type"]] += 1
            for part in (t.get("style") or "").split(";"):
                if ":" in part:
                    styles[part.split(":")[0].strip()] += 1
            if t.get("data-hook"):
                hooks[re.sub(r"\d+", "N", t["data-hook"])] += 1
    L.append("body tags: %s" % tags.most_common(40))
    L.append("rcv block types: %s" % types.most_common())
    L.append("inline style properties: %s" % styles.most_common(30))
    L.append("data-hooks: %s" % hooks.most_common(40))
    ok = [v for v in images.values() if v.get("status") == 200]
    L.append("images: %d unique, %d reachable, total %.1f MB, largest %.1f MB" % (
        len(images), len(ok), sum(v["bytes"] for v in ok) / 1e6, max([v["bytes"] for v in ok] or [0]) / 1e6))
    L.append("image types: %s" % Counter(v.get("type") for v in ok).most_common())
    L.append("unreachable: %s" % [(k, v) for k, v in images.items() if v.get("status") != 200][:10])
    open(OUT + "/SUMMARY.txt", "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n".join(L))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
