#!/usr/bin/env python3
"""Check the built site against the original Wix text.

Usage: python3 scripts/wix_verify.py _site
Compares, for every migrated post, the built page (title, date, category, text blocks,
images, lists) with _probe/expected.json, and checks the blog overview and image files.
Writes _probe/VERIFY.txt and exits non-zero if anything differs.
"""
import json
import os
import re
import sys
from collections import Counter

from bs4 import BeautifulSoup

SITE = sys.argv[1] if len(sys.argv) > 1 else "_site"
BASEURL = "/nanafitmama"
expected = json.load(open("_probe/expected.json", encoding="utf-8"))
L, bad = [], []


def norm(s):
    return re.sub(r"\s+", " ", (s or "").replace("​", "").replace(" ", " ")).strip()


def local(src):
    p = src
    if p.startswith(BASEURL + "/"):
        p = p[len(BASEURL):]
    return os.path.join(SITE, p.lstrip("/"))


def blocks_of(body):
    out = []
    for el in body.find_all(recursive=False):
        if el.name == "p":
            imgs = el.find_all("img")
            if imgs and not norm(el.get_text()):
                for im in imgs:
                    out.append({"img": im.get("src", "")})
            else:
                out.append({"p": norm(el.get_text())})
        elif el.name in ("ul", "ol"):
            out.append({"list": [norm(li.get_text()) for li in el.find_all("li", recursive=False)]})
        elif re.match(r"h[1-6]$", el.name):
            out.append({"h": norm(el.get_text())})
        elif el.name == "hr":
            out.append({"hr": True})
        elif el.name == "blockquote":
            out.append({"p": norm(el.get_text())})
        else:
            out.append({"other": el.name})
    return out


ok_posts = 0
for slug, exp in expected.items():
    path = os.path.join(SITE, "post", slug, "index.html")
    if not os.path.exists(path):
        bad.append("%s: page missing" % slug)
        continue
    soup = BeautifulSoup(open(path, encoding="utf-8").read(), "lxml")
    problems = []
    h1 = soup.select_one("h1.post-title")
    if not h1 or norm(h1.get_text()) != norm(exp["title"]):
        problems.append("title %r != %r" % (norm(h1.get_text()) if h1 else None, norm(exp["title"])))
    by = soup.select_one(".post-byline")
    y, m, d = exp["date"].split("-")
    if not by or ("%s.%s.%s." % (d, m, y)) not in by.get_text():
        problems.append("date %r not in byline %r" % (exp["date"], by.get_text() if by else None))
    tag = soup.select_one(".post-tags .tag")
    if (tag.get_text(strip=True) if tag else None) != exp["category"]:
        problems.append("category %r != %r" % (tag.get_text(strip=True) if tag else None, exp["category"]))
    if soup.select_one(".post-cover"):
        problems.append("cover shown on top although hide_image is set")
    body = soup.select_one(".post-body")
    got = blocks_of(body) if body else []
    want = []
    for b in exp["blocks"]:
        if "img" in b:
            want.append({"img": BASEURL + "/" + b["img"]})
        else:
            want.append(b)
    if len(got) != len(want):
        problems.append("block count %d != %d" % (len(got), len(want)))
    for i, (g, w) in enumerate(zip(got, want)):
        if "p" in w and "p" in g:
            if norm(g["p"]) != norm(w["p"]):
                problems.append("block %d text differs: %r vs %r" % (i, g["p"][:60], w["p"][:60]))
                break
        elif "list" in w and "list" in g:
            if [norm(x) for x in g["list"]] != [norm(x) for x in w["list"]]:
                problems.append("block %d list differs" % i)
                break
        elif g != w and not ("h" in w and "h" in g and norm(g["h"]) == norm(w["h"])):
            problems.append("block %d %s != %s" % (i, str(g)[:60], str(w)[:60]))
            break
    if body:
        for im in body.find_all("img"):
            if not os.path.isfile(local(im.get("src", ""))):
                problems.append("image missing: %s" % im.get("src"))
            if im.get("loading") != "lazy":
                problems.append("image not lazy-loaded: %s" % im.get("src"))
    if problems:
        bad.append("%s: %s" % (slug, "; ".join(problems[:3])))
    else:
        ok_posts += 1

L.append("posts checked: %d | identical to Wix text/structure: %d | with differences: %d" % (len(expected), ok_posts, len(expected) - ok_posts))

# overview
ov = os.path.join(SITE, "blog", "index.html")
if os.path.exists(ov):
    s = BeautifulSoup(open(ov, encoding="utf-8").read(), "lxml")
    cards = s.select(".post-card")
    L.append("overview cards: %d (expected %d)" % (len(cards), len(expected)))
    if len(cards) != len(expected):
        bad.append("overview card count %d != %d" % (len(cards), len(expected)))
    miss = [c.select_one("img").get("src") for c in cards if c.select_one("img") and not os.path.isfile(local(c.select_one("img").get("src")))]
    noimg = sum(1 for c in cards if not c.select_one("img"))
    L.append("overview: thumbnails missing on disk: %d | cards without image: %d" % (len(miss), noimg))
    bad += ["thumbnail missing: %s" % m for m in miss[:5]]
    cats = Counter(c.get("data-category") for c in cards)
    L.append("overview categories: %s" % dict(cats))
    L.append("filter chips: %s" % [b.get_text(strip=True) for b in s.select(".filter-chip")])
    first = [c.select_one(".post-card-title").get_text(strip=True) for c in cards[:3]]
    L.append("first cards (newest first): %s" % first)
else:
    bad.append("blog/index.html missing")

# feed + existing pages
for f in ["feed.xml", "index.html", "o-meni.html", "program.html", "galerija.html"]:
    if not os.path.exists(os.path.join(SITE, f)):
        bad.append("%s missing" % f)
n_post_dirs = len(os.listdir(os.path.join(SITE, "post"))) if os.path.isdir(os.path.join(SITE, "post")) else 0
L.append("post folders in built site: %d" % n_post_dirs)
L.append("PROBLEMS: %d" % len(bad))
L += ["  " + b for b in bad[:40]]
os.makedirs("_probe", exist_ok=True)
open("_probe/VERIFY.txt", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
sys.exit(1 if bad else 0)
