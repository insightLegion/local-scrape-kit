"""local-scrape-kit, part 2: unpack the files that the browser scripts downloaded, and make a CSV for the CISCE locator.

Double-click kit.exe (or run `python kit.py`). It reads the *-NNNN-NNNN.json files from your Downloads folder and from its own
folder, and writes kit-output\\<target>\\pages\\..., kit-output\\<target>\\urls.csv, the PDFs and other files of list runs
(kit-output\\<target>\\files\\), and for the CISCE locator kit-output\\cisce-locator\\cisce_schools.csv.
It lists missing pages and missing files. Send the JSON files and the PDFs to trideep (README).

    options: --out DIR   --in DIR (more folders with downloaded files; more than one is OK)
"""
import argparse
import csv
import html
import json
import re
import shutil
import sys
import traceback
from pathlib import Path

BUNDLE = re.compile(r"^(?P<prefix>[a-z0-9-]+)-(?P<from>\d{4})-(?P<to>\d{4})(?: \(\d+\))?\.json$")
KEY = re.compile(r"^(page|url)-\d{4}\.html$")

# --- parser: the same as crawl.py in github.com/s1d-labs/cisce-scraper (pure, tested) -----------------------------------------
CARD = re.compile(r'<div class="school-card">(.*?)(?=<div class="school-card">|</tbody>)', re.S)
HEAD = re.compile(r'<h6[^>]*>\s*([A-Z]{2,4}\d+)\s*-\s*(.*?)</h6>', re.S)
BODY = re.compile(r'<p class="mb-1">(.*?)</p>', re.S)
BADGE = re.compile(r'class="badge badge-outline-(red|blue|green)[^"]*">\s*(.*?)\s*</span>', re.S)
SITE_LINK = re.compile(r'<a href="([^"]*)"\s+class="[^"]*visit-btn')
LOCATIONS = re.compile(r'const locations = (\{.*?\});\s*$', re.M)
TOTAL = re.compile(r'Showing\s+(\d+)\s+to\s+(\d+)\s+of\s+(\d+)\s+entries')
PIN = re.compile(r"^\d[\d \-]{2,9}$")
FIELDS = ["code", "name", "principal", "address", "locality", "district", "state", "pin", "country", "gender", "residence", "asisc",
          "icse", "isc", "cve", "website", "lat", "lng", "listed_total", "file"]


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def is_challenge(page):
    return bool(re.search(r"<title>\s*(Just a moment|Attention Required)", page)) or "challenge-platform" in page and "school-card" not in page


def listed_total(page):
    m = TOTAL.search(page)
    return int(m.group(3)) if m else None


def split_address(lines):
    parts = [p.strip(" .-") for p in ", ".join(lines).split(",") if p.strip(" .-")]
    out = {"country": "", "pin": "", "state": "", "district": "", "locality": ""}
    if parts and not PIN.match(parts[-1]):
        out["country"] = parts.pop()
    if parts and PIN.match(parts[-1]):
        out["pin"] = parts.pop().replace(" ", "")
    if parts:
        out["state"] = parts.pop()
    if parts:
        out["district"] = parts.pop()
    out["locality"] = ", ".join(parts)
    return out


def parse(page):
    coords = {}
    m = LOCATIONS.search(page)
    if m:
        for s in json.loads(m.group(1)).get("schools", []):
            coords[s["name"].split(" - ", 1)[0].strip()] = (s.get("lat"), s.get("lng"))
    total, out = listed_total(page), []
    for card in CARD.findall(page):
        h = HEAD.search(card)
        if not h:
            continue
        code, name = h.group(1), text(h.group(2))
        body = BODY.search(card)
        principal, address_lines = "", []
        if body:
            first, _, rest = body.group(1).partition("<br>")
            principal = text(first)
            address_lines = [text(x) for x in rest.split("\n") if text(x)]
        badges = [(c, text(t)) for c, t in BADGE.findall(card)]
        blue = [t for c, t in badges if c == "blue"]
        green = {t for c, t in badges if c == "green"}
        link = SITE_LINK.search(card)
        lat, lng = coords.get(code, (None, None))
        out.append((code, {
            "code": code, "name": name, "principal": principal,
            "address": ", ".join(a.rstrip(",") for a in address_lines), **split_address(address_lines),
            "gender": next((t for c, t in badges if c == "red"), ""),
            "residence": next((t for t in blue if t != "ASISC"), ""),
            "asisc": "ASISC" in blue, "icse": "ICSE" in green, "isc": "ISC" in green, "cve": "CVE" in green,
            "website": html.unescape(link.group(1)).strip() if link else "",
            "lat": lat, "lng": lng, "listed_total": total,
        }))
    return out
# ------------------------------------------------------------------------------------------------------------------------------


def write_csv(target_dir):
    """cisce_schools.csv from target_dir/pages (CISCE locator pages, also pages saved by hand). Returns the number of schools."""
    pages = target_dir / "pages"
    schools, numbers = {}, set()
    for f in sorted(pages.glob("*.htm*")):
        try:
            rows = parse(f.read_text(encoding="utf-8", errors="replace"))
        except (ValueError, KeyError) as e:                    # one broken page must not stop the CSV
            print(f"{f.name}: cannot read ({type(e).__name__}), skipped")
            continue
        for code, d in rows:
            schools[code] = {**d, "file": f.name}
        if rows and (m := re.fullmatch(r"page-(\d{4})\.html", f.name)):
            numbers.add(int(m.group(1)))
    path = target_dir / "cisce_schools.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:          # utf-8-sig: Excel opens it correctly
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(schools[c] for c in sorted(schools))
    totals = {d["listed_total"] for d in schools.values() if d["listed_total"]}
    print(f"\n{len(schools)} schools in {path}  (the site says: {', '.join(map(str, sorted(totals))) or 'unknown'})")
    missing = sorted(set(range(1, max(numbers) + 1)) - numbers) if numbers else []
    if missing:
        print(f"Missing pages ({len(missing)}): {', '.join(map(str, missing[:40]))}{' ...' if len(missing) > 40 else ''}"
              "\nRun the script again and type the first missing page as the start page.")
    return len(schools)


def unpack(out_dir, folders):
    """Unpack every bundle (oldest first, so a newer download wins) into out_dir/<target>/. Returns {target: n_pages}."""
    folders = list(dict.fromkeys(Path(f).resolve() for f in folders if Path(f).is_dir()))
    bundles = {b.resolve() for folder in folders for b in folder.glob("*.json") if BUNDLE.match(b.name)}
    done, links = {}, {}
    for bundle in sorted(bundles, key=lambda f: f.stat().st_mtime):
        try:
            data = json.loads(bundle.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:                     # a broken or half-downloaded file: skip it, keep the others
            print(f"{bundle.name}: cannot read ({e}), skipped")
            continue
        if not isinstance(data, dict):
            continue
        meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
        target = re.sub(r"[^a-z0-9-]", "", str(meta.get("target") or "cisce-locator"))   # saver.js files have no _meta
        tdir = out_dir / target
        (tdir / "pages").mkdir(parents=True, exist_ok=True)
        for name, content in data.items():
            if KEY.match(name) and isinstance(content, str):  # the names come from a file: no paths
                if content:
                    (tdir / "pages" / name).write_text(content, encoding="utf-8")
                done[target] = done.get(target, 0) + 1
                info = (meta.get("urls") or {}).get(name) or {}
                links.setdefault(target, {})[name] = {"key": name, "url": info.get("url", ""), "file": info.get("file", ""),
                                                      "status": info.get("status", 200), "bundle": bundle.name}
                if info.get("file"):                          # a PDF or other file of a list run, downloaded next to the bundle
                    src = next((f / info["file"] for f in folders if (f / info["file"]).exists()), None)
                    if src:
                        (tdir / "files").mkdir(exist_ok=True)
                        shutil.copy2(src, tdir / "files" / info["file"])
                    else:
                        print(f"missing file: {info['file']} ({info.get('url', '')})")
        print(f"{bundle.name}: unpacked ({target})")
    for target, rows in links.items():
        with open(out_dir / target / "urls.csv", "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=["key", "url", "file", "status", "bundle"])
            w.writeheader()
            w.writerows(rows[k] for k in sorted(rows))
    if not bundles:
        print("No downloaded files (*-NNNN-NNNN.json) in:\n  " + "\n  ".join(map(str, folders)) + "\nRun a script in your browser first (README).")
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    ap.add_argument("--out", default=str(here / "kit-output"))
    ap.add_argument("--in", dest="inputs", action="append", default=[], help="folder with downloaded files (more than one is OK)")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {out_dir}")
    done = unpack(out_dir, [*args.inputs, here, Path.home() / "Downloads"])
    for target, n in sorted(done.items()):
        print(f"{target}: {n} pages or URLs")
    if (out_dir / "cisce-locator" / "pages").is_dir():
        write_csv(out_dir / "cisce-locator")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    code = 0
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception:
        traceback.print_exc()
        code = 1
    if getattr(sys, "frozen", False):            # keep the console window open after a double-click
        try:
            input("\nPress Enter to close ...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(code)
