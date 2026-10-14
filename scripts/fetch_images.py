#!/usr/bin/env python3
"""Download the full-size original images listed in images/manifest.json.

Usage (from the repository root):
    pip install pillow
    python3 scripts/fetch_images.py

Each manifest entry has a target path (images/<page>/<name>) and the Wix media
id of the ORIGINAL upload. Entries with a "crop" [x, y, w, h] are cropped at
full resolution, reproducing the crop the Wix site applied, so the pages look
exactly as before. Existing files are skipped, so the script is safe to re-run.
"""
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://static.wixstatic.com/media/%s.%s"


def main():
    with open(os.path.join(ROOT, "images", "manifest.json"), encoding="utf-8") as f:
        manifest = json.load(f)

    failed = []
    for e in manifest:
        target = os.path.join(ROOT, e["path"])
        if os.path.exists(target):
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        url = BASE % (e["id"], e["ext"])
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
        except Exception as exc:  # noqa: BLE001
            failed.append((e["path"], str(exc)))
            continue

        if "crop" in e:
            from io import BytesIO
            from PIL import Image

            x, y, w, h = e["crop"]
            img = Image.open(BytesIO(data))
            fmt = img.format
            img = img.crop((x, y, x + w, y + h))
            img.save(target, format=fmt, quality=95) if fmt == "JPEG" else img.save(target, format=fmt)
        else:
            with open(target, "wb") as out:
                out.write(data)
        print("saved", e["path"])

    if failed:
        for p, msg in failed:
            print("FAILED", p, msg, file=sys.stderr)
        sys.exit(1)
    print("done: %d images" % len(manifest))


if __name__ == "__main__":
    main()
