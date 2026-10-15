#!/usr/bin/env python3
"""Download the full-size originals listed in images/blog/manifest.json.

Entries with a "crop" [x, y, w, h] are cropped at full resolution, reproducing the
crop the old Wix page applied. Existing files are skipped, so the script can be re-run.
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import requests
from PIL import Image

BASE = "https://static.wixstatic.com/media/"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}


def fetch(entry):
    target = entry["path"]
    if os.path.exists(target) and os.path.getsize(target) > 0:
        return entry["path"], "exists", None
    os.makedirs(os.path.dirname(target), exist_ok=True)
    err = None
    for i in range(4):
        try:
            r = requests.get(BASE + entry["id"], headers=UA, timeout=90)
            if r.status_code != 200 or not r.content:
                err = "HTTP %s" % r.status_code
                time.sleep(2 * (i + 1))
                continue
            data = r.content
            if "crop" in entry:
                x, y, w, h = entry["crop"]
                img = Image.open(BytesIO(data))
                fmt = img.format
                img = img.crop((x, y, x + w, y + h))
                out = BytesIO()
                img.save(out, format=fmt, **({"quality": 95} if fmt == "JPEG" else {}))
                data = out.getvalue()
            with open(target, "wb") as f:
                f.write(data)
            return entry["path"], "saved", None
        except Exception as e:  # noqa: BLE001
            err = str(e)
            time.sleep(2 * (i + 1))
    return entry["path"], "failed", err


def main():
    manifest = json.load(open("images/blog/manifest.json", encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(fetch, manifest))
    failed = [(p, e) for p, s, e in results if s == "failed"]
    saved = sum(1 for _, s, _ in results if s == "saved")
    print("images: %d in manifest, %d saved now, %d already there, %d failed" % (
        len(manifest), saved, sum(1 for _, s, _ in results if s == "exists"), len(failed)))
    for p, e in failed:
        print("FAILED", p, e, file=sys.stderr)
    # integrity check
    bad, dims = [], []
    for e in manifest:
        try:
            with Image.open(e["path"]) as im:
                im.verify()
            with Image.open(e["path"]) as im:
                dims.append(im.size)
        except Exception as ex:  # noqa: BLE001
            bad.append((e["path"], str(ex)))
    total = sum(os.path.getsize(e["path"]) for e in manifest if os.path.exists(e["path"]))
    print("integrity: %d unreadable | total %.1f MB | smallest %s | largest %s" % (
        len(bad), total / 1e6, min(dims, key=lambda d: d[0] * d[1]) if dims else None, max(dims, key=lambda d: d[0] * d[1]) if dims else None))
    for p, e in bad:
        print("BAD", p, e, file=sys.stderr)
    return 1 if failed or bad else 0


if __name__ == "__main__":
    sys.exit(main())
