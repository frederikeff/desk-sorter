#!/usr/bin/env python3
"""Make a sort sheet: thumbnails and a list of every image and video under the given folders.

  python3 make_sheet.py <sheet-name> <folder> [<folder> ...] [--skip <folder> ...] [--buckets "Work,Personal,Delete?"]

Writes data/<sheet-name>/items.json and data/<sheet-name>/thumbs/. Reads only; moves nothing.
Files that live only in iCloud get no thumbnail (making one would download them).
--buckets sets the first buckets of a new sheet (the page can add more later).
"""
import hashlib, json, os, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor

IMG = (".png", ".jpg", ".jpeg", ".webp", ".heic", ".gif", ".tif", ".tiff", ".bmp", ".svg")
VID = (".mov", ".mp4", ".m4v", ".avi", ".webm", ".mkv")
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__)
    name, rest = args[0], args[1:]
    roots, skip, buckets = [], [], None
    i = 0
    while i < len(rest):
        if rest[i] in ("--skip", "--buckets") and i + 1 < len(rest):
            if rest[i] == "--skip":
                skip.append(os.path.abspath(os.path.expanduser(rest[i + 1])))
            else:
                buckets = [b.strip() for b in rest[i + 1].split(",") if b.strip()]
            i += 2
            continue
        roots.append(os.path.abspath(os.path.expanduser(rest[i])))
        i += 1
    for root in roots:
        if not os.path.isdir(root):
            sys.exit(f"Not a folder: {root}")
    skip.append(HERE)  # the tool's own folder (its thumbnails) when it sits inside a folder being sorted
    out = os.path.join(HERE, "data", name)
    thumbs = os.path.join(out, "thumbs")
    os.makedirs(thumbs, exist_ok=True)
    choices = os.path.join(out, "choices.json")
    if buckets and not os.path.exists(choices):  # never overwrites sorting already done
        with open(choices, "w", encoding="utf-8") as fh:
            json.dump({"_buckets": buckets}, fh, ensure_ascii=False)

    items = []
    for root in roots:
        for r, ds, fs in os.walk(root):
            ds[:] = sorted(d for d in ds if not d.startswith(".") and not d.endswith((".app", ".photoslibrary"))
                           and os.path.join(r, d) not in skip and d != "node_modules")
            for f in sorted(fs):
                low = f.lower()
                kind = "image" if low.endswith(IMG) else "video" if low.endswith(VID) else None
                if not kind:
                    continue
                p = os.path.join(r, f)
                st = os.stat(p)
                items.append({
                    "id": hashlib.sha1(p.encode()).hexdigest()[:16],
                    "path": p,
                    "name": f,
                    "folder": os.path.relpath(r, os.path.dirname(root)),
                    "kind": kind,
                    "size": st.st_size,
                    "mtime": int(st.st_mtime),
                    "icloud_only": st.st_size > 0 and st.st_blocks == 0,
                })

    def thumb(it):
        dst = os.path.join(thumbs, it["id"] + ".jpg")
        if os.path.exists(dst) or it["icloud_only"]:
            return
        p, low = it["path"], it["name"].lower()
        try:
            if it["kind"] == "image" and not low.endswith(".svg"):
                subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "70", "-Z", "320", p, "--out", dst],
                               capture_output=True, timeout=60)
            if not os.path.exists(dst):  # videos, svg, and what sips could not read
                with tempfile.TemporaryDirectory() as td:
                    subprocess.run(["qlmanage", "-t", "-s", "320", "-o", td, p], capture_output=True, timeout=60)
                    made = [x for x in os.listdir(td) if x.endswith(".png")]
                    if made:
                        subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "70",
                                        os.path.join(td, made[0]), "--out", dst], capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            pass

    t0 = time.time()
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(thumb, items))
    for it in items:
        it["thumb"] = os.path.exists(os.path.join(thumbs, it["id"] + ".jpg"))
    with open(os.path.join(out, "items.json"), "w", encoding="utf-8") as fh:
        json.dump({"sheet": name, "made": time.strftime("%Y-%m-%d %H:%M"), "roots": roots, "items": items}, fh)
    n_img = sum(i["kind"] == "image" for i in items)
    print(f"{name}: {n_img} images, {len(items) - n_img} videos, "
          f"{sum(i['thumb'] for i in items)} thumbnails, {sum(i['icloud_only'] for i in items)} only in iCloud, "
          f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
