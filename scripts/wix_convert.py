#!/usr/bin/env python3
"""Stage 2 of the Wix blog migration: turn the fetched posts into Jekyll posts.

Input : _probe/wix-posts.json            (from wix_fetch.py)
Output: _posts/YYYY-MM-DD-<slug>.md      one file per Wix post, text copied exactly
        images/blog/manifest.json        which Wix image becomes which local file
        _probe/expected.json             plain text per post, to check the built site against
        migration/old-to-new-urls.csv    old Wix address -> new address (for later redirects)
"""
import csv
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, NavigableString

ZAGREB = ZoneInfo("Europe/Zagreb")
IMG_DIR = "images/blog"
KEEP_TLDS = {"com", "hr", "org", "net", "eu", "be", "info"}
WARN = []


def warn(slug, msg):
    WARN.append("%s: %s" % (slug, msg))


# ── helpers ────────────────────────────────────────────────────
def ascii_slug(s):
    s = s.lower().replace("đ", "dj")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "clanak"


def media_id(u):
    m = re.search(r"/media/([^/?#]+)", u or "")
    return m.group(1) if m else (u or "")


def ext_of(mid):
    e = mid.rsplit(".", 1)[-1].lower() if "." in mid else "jpg"
    return "jpg" if e == "jpeg" else e


def esc(text):
    """Escape characters that Markdown (kramdown) or Liquid would otherwise interpret."""
    text = text.replace("​", "")
    text = text.replace("\\", "\\\\")
    for ch in "*_`[]~<>":
        text = text.replace(ch, "\\" + ch)
    text = text.replace("{", "&#123;").replace("}", "&#125;")
    text = text.replace("...", "\\.\\.\\.")
    text = text.replace("--", "\\-\\-")
    return text


def esc_line_start(line):
    m = re.match(r"^(\d+)([.)])(\s)", line)
    if m:  # "1. text" would become a numbered list: escape the dot, not the digit
        return "%s\\%s%s%s" % (m.group(1), m.group(2), m.group(3), line[m.end():])
    if re.match(r"^(#|\+|-|=)", line):
        return "\\" + line
    return line


def wrap(marker, inner):
    core = inner.strip()
    if not core:
        return inner
    lead = inner[: len(inner) - len(inner.lstrip())]
    trail = inner[len(inner.rstrip()):]
    return "%s%s%s%s%s" % (lead, marker, core, marker, trail)


def good_link(href, text):
    if not href or not text.strip():
        return False
    if href.startswith("mailto:"):
        return True
    host = urlparse(href).netloc.lower()
    return host.rsplit(".", 1)[-1] in KEEP_TLDS


def clean_href(href):
    if "facebook.com" in href and "?" in href:
        return href.split("?", 1)[0]
    return href


def inline(node, slug):
    out = []
    for ch in node.children:
        if isinstance(ch, NavigableString):
            out.append(esc(str(ch)))
            continue
        name = ch.name
        if name == "br":
            if ch.get("role") != "presentation":
                out.append("  \n")
        elif name in ("strong", "b"):
            out.append(wrap("**", inline(ch, slug)))
        elif name in ("em", "i"):
            out.append(wrap("*", inline(ch, slug)))
        elif name == "a":
            txt = inline(ch, slug)
            href = ch.get("href", "")
            plain = ch.get_text()
            if good_link(href, plain):
                lead = txt[: len(txt) - len(txt.lstrip())]
                trail = txt[len(txt.rstrip()):]
                out.append("%s[%s](%s)%s" % (lead, txt.strip(), clean_href(href).replace(" ", "%20").replace(")", "%29"), trail))
            else:
                if plain.strip():
                    warn(slug, "dropped link %r on %r" % (href, plain.strip()[:30]))
                out.append(txt)
        else:  # span, u, etc.: keep the text only
            out.append(inline(ch, slug))
    s = "".join(out)
    return s.replace("****", "").replace("**  **", "  ")


def para_text(el, slug):
    s = inline(el, slug)
    s = re.sub(r"[ \t]+\n", "\n", s).strip()
    s = s.replace(" ", " ") if s.strip("  ") == "" else s
    return s


# ── body conversion ────────────────────────────────────────────
def convert_body(rec, files, cover_path):
    slug = rec["slug"]
    soup = BeautifulSoup(rec["body_html"], "lxml")
    blocks, expected = [], []
    img_n = 0
    for marker in soup.find_all("div", attrs={"data-hook": re.compile(r"^rcv-block\d+$")}):
        typ = marker.get("type")
        content = marker.find_previous_sibling("div")
        if typ == "empty-line" or content is None:
            continue
        if typ == "image":
            wi = content.find("wow-image")
            info = json.loads(wi["data-image-info"]) if wi and wi.get("data-image-info") else {}
            uri = (info.get("imageData") or {}).get("uri", "")
            mid = media_id(uri)
            crop = None
            cm = re.search(r"/crop/x_(\d+),y_(\d+),w_(\d+),h_(\d+)", uri)
            if cm:
                crop = [int(v) for v in cm.groups()]
            key = (mid, tuple(crop) if crop else None)
            if key == files["cover_key"] and cover_path:
                path = cover_path
            else:
                img_n += 1
                path = "%s/%s-%d.%s" % (IMG_DIR, slug_of(rec), img_n + 0, ext_of(mid))
                entry = {"path": path, "id": mid, "ext": ext_of(mid)}
                if crop:
                    entry["crop"] = crop
                files["entries"].append(entry)
            img = content.find("img")
            alt = (img.get("alt") if img else "") or ""
            cap = content.find("figcaption")
            blocks.append("![%s](/%s)" % (esc(alt), path))
            if cap and cap.get_text(strip=True):
                blocks.append("*%s*" % esc(cap.get_text(strip=True)))
            expected.append({"img": path})
            continue
        if typ == "divider":
            blocks.append("* * *")
            expected.append({"hr": True})
            continue
        ul = content.find(["ul", "ol"])
        if ul:
            items = []
            for i, li in enumerate(ul.find_all("li", recursive=False)):
                t = para_text(li, slug)
                if t:
                    prefix = "%d. " % (i + 1) if ul.name == "ol" else "- "
                    items.append(prefix + t.replace("\n", "\n  "))
            if items:
                blocks.append("\n".join(items))
                expected.append({"list": [re.sub(r"\s+", " ", li.get_text()).strip() for li in ul.find_all("li", recursive=False) if li.get_text(strip=True)]})
            continue
        heading = content.find(re.compile(r"^h[1-6]$"))
        if heading:
            t = para_text(heading, slug)
            if t:
                lvl = max(2, int(heading.name[1]))
                blocks.append("%s %s" % ("#" * lvl, t))
                expected.append({"h": heading.get_text().strip()})
            continue
        p = content.find("p")
        if p is None:
            if content.get_text(strip=True):
                warn(slug, "unhandled block %r: %r" % (typ, content.get_text(strip=True)[:40]))
            continue
        t = para_text(p, slug)
        if not t.strip():
            continue
        blocks.append("\n".join(esc_line_start(l) if i == 0 else l for i, l in enumerate(t.split("\n"))))
        expected.append({"p": re.sub(r"\s+", " ", p.get_text().replace("​", "")).strip()})
    return "\n\n".join(blocks) + "\n", expected


_SLUGS = {}


def slug_of(rec):
    return _SLUGS[rec["url"]]


def main():
    posts = json.load(open("_probe/wix-posts.json", encoding="utf-8"))
    os.makedirs("_posts_new", exist_ok=True)
    used, entries, expected_all, csv_rows = set(), [], {}, []
    files = {"entries": entries}
    cat_map = {}

    for rec in sorted(posts, key=lambda r: r["datePublished"]):
        dt = datetime.fromisoformat(rec["datePublished"].replace("Z", "+00:00")).astimezone(ZAGREB)
        base = ascii_slug(rec["slug"])
        slug, n = base, 2
        while (dt.strftime("%Y-%m-%d"), slug) in used:
            slug = "%s-%d" % (base, n)
            n += 1
        used.add((dt.strftime("%Y-%m-%d"), slug))
        _SLUGS[rec["url"]] = slug

        # cover (card thumbnail)
        cover_mid = rec["cover"]
        cover_path = None
        files["cover_key"] = (cover_mid, None)
        if cover_mid:
            cover_path = "%s/%s.%s" % (IMG_DIR, slug, ext_of(cover_mid))
            entries.append({"path": cover_path, "id": cover_mid, "ext": ext_of(cover_mid)})

        body, expected = convert_body(rec, files, cover_path)

        cats = rec["categories"]
        if len(cats) > 1:
            warn(rec["slug"], "has %d categories, using the first: %s" % (len(cats), [c["label"] for c in cats]))
        category = cats[0]["label"] if cats else None
        if category:
            cat_map[category] = cat_map.get(category, 0) + 1

        fm = ["---"]
        fm.append("title: %s" % json.dumps(rec["title"], ensure_ascii=False))
        fm.append("date: %s" % dt.strftime("%Y-%m-%d %H:%M:%S %z"))
        if cover_path:
            fm.append("image: /%s" % cover_path)
            fm.append("hide_image: true")
        if category:
            fm.append("kategorija: %s" % json.dumps(category, ensure_ascii=False))
        fm.append("published: true")
        fm.append("---")
        name = "%s-%s.md" % (dt.strftime("%Y-%m-%d"), slug)
        open("_posts_new/" + name, "w", encoding="utf-8").write("\n".join(fm) + "\n" + body)
        expected_all[slug] = {"title": rec["title"], "date": dt.strftime("%Y-%m-%d"), "category": category, "blocks": expected, "file": name}
        csv_rows.append((rec["url"], "/post/%s/" % slug))

    # unique image entries (several blocks may share a file)
    seen, uniq = set(), []
    for e in entries:
        if e["path"] not in seen:
            seen.add(e["path"])
            uniq.append(e)
    os.makedirs(IMG_DIR, exist_ok=True)
    json.dump(uniq, open(IMG_DIR + "/manifest.json", "w", encoding="utf-8"), indent=1)
    json.dump(expected_all, open("_probe/expected.json", "w", encoding="utf-8"), ensure_ascii=False)
    os.makedirs("migration", exist_ok=True)
    with open("migration/old-to-new-urls.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["old_wix_url", "new_path"])
        w.writerows(csv_rows)
    print("posts written:", len(expected_all), "| images:", len(uniq), "| categories:", cat_map)
    print("warnings:", len(WARN))
    for w in WARN:
        print("  ", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
