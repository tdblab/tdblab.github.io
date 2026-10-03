"""Build the in situ atlas from data/atlas.csv.

Run from the website root:  python tools/build_atlas.py

Reads data/atlas.csv (one row per image or video; edit it in Excel or any
spreadsheet), writes data/atlas.js and data/atlas.json for atlas.html, and creates a small
preview for any record that does not have one yet in
assets/images/atlas/thumbs/. Full-resolution files are never modified.

CSV columns
  id            unique short name, letters/digits/dashes (also the preview name)
  file          path to the full-resolution file, relative to the site root
                (or relative to BASE_URL once images live elsewhere)
  kind          image or video
  species, tissue, stage, stage_detail, method
  targets       "gene:color; gene:color"  (color optional, e.g. "optix:green; spalt")
  counterstain  same format, e.g. "DAPI:blue"
  locus         NCBI gene IDs, separated by ";" (e.g. LOC112046662)
  caption       free text shown under the image
  doi           paper DOI if published
  notes         anything still missing; shown to visitors as "details pending"

Needs: pip install pillow   (and ffmpeg on PATH for video previews)
"""
import csv, json, os, subprocess, sys
from datetime import date

BASE_URL = ""          # later, e.g. "https://images.tirthadasbanerjee.com/"
THUMB_DIR = "assets/images/atlas/thumbs"
THUMB_EDGE = 640       # longest side of previews, in pixels

def parse_pairs(text):
    out = []
    for part in [p.strip() for p in (text or "").split(";") if p.strip()]:
        name, _, color = part.partition(":")
        out.append({"name": name.strip(), "color": color.strip().lower() or None})
    return out

def make_thumb(src, dst, kind):
    from PIL import Image
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if kind == "video":
        tmp = dst + ".png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", src,
                        "-frames:v", "1", tmp], check=True)
        src = tmp
    im = Image.open(src).convert("RGB")
    im.thumbnail((THUMB_EDGE, THUMB_EDGE), Image.LANCZOS)
    im.save(dst, "JPEG", quality=82, optimize=True, progressive=True)
    if kind == "video":
        os.remove(src)
    return im.size

def main():
    rows = list(csv.DictReader(open("data/atlas.csv", encoding="utf-8-sig")))
    ids, records = set(), []
    for r in rows:
        rid = r["id"].strip()
        if not rid or rid in ids:
            sys.exit(f"Duplicate or empty id: {rid!r}")
        ids.add(rid)
        thumb = f"{THUMB_DIR}/{rid}.jpg"
        size = None
        if not os.path.exists(thumb):
            if os.path.exists(r["file"]):
                size = make_thumb(r["file"], thumb, r["kind"])
                print("preview", thumb)
            else:
                print("WARNING: file not found, no preview:", r["file"])
        if size is None and os.path.exists(thumb):
            from PIL import Image
            size = Image.open(thumb).size
        records.append({
            "id": rid, "file": r["file"], "kind": r["kind"] or "image",
            "thumb": thumb if os.path.exists(thumb) else None,
            "w": size[0] if size else None, "h": size[1] if size else None,
            "species": r["species"], "tissue": r["tissue"], "stage": r["stage"],
            "stage_detail": r["stage_detail"], "method": r["method"],
            "targets": parse_pairs(r["targets"]),
            "counterstain": parse_pairs(r["counterstain"]),
            "locus": [x.strip() for x in r["locus"].split(";") if x.strip()],
            "caption": r["caption"], "doi": r["doi"], "notes": r["notes"],
        })
    os.makedirs("data", exist_ok=True)
    payload = json.dumps({"generated": date.today().isoformat(), "base_url": BASE_URL,
                          "records": records}, ensure_ascii=False, separators=(",", ":"))
    open("data/atlas.json", "w", encoding="utf-8").write(payload)
    # same data as a script, so atlas.html also works when opened by double-click
    open("data/atlas.js", "w", encoding="utf-8").write("window.ATLAS_DATA=" + payload + ";")
    print(f"data/atlas.json and data/atlas.js: {len(records)} records")

if __name__ == "__main__":
    main()
