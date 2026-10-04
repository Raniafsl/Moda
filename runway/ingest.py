"""Download freely licensed runway photos from Wikimedia Commons.

Commons groups photos into "<year> fashion shows" category trees, so we use the
`deepcat:` search keyword to pull every bitmap under a year's tree, along with
the license and photographer so the dashboard can credit them.

    python -m runway.ingest                       # major + fashion-week shows, 2007-2026
    python -m runway.ingest --tiers major         # designer & couture shows only
"""

import argparse
import html
import os
import re
import time

import requests

from .db import IMAGE_DIR, ROOT, connect
from .sources import classify

API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia asks bots to include contact info; set RUNWAY_CONTACT to your email or repo URL.
HEADERS = {"User-Agent": f"moda/0.1 ({os.environ.get('RUNWAY_CONTACT', 'student research project')})"}
PAUSE = 1.0  # seconds between image downloads - Commons rate-limits thumbnails hard
THUMB_WIDTH = 500  # one of Wikimedia's standard thumbnail sizes
BATCH = 50


def strip_html(s: str | None) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def credit(s: str | None) -> str:
    """First line of the Artist field - some uploaders paste whole notices in there."""
    first = strip_html(s).splitlines()[0] if strip_html(s) else ""
    return first[:80]


def api_get(params: dict, retries: int = 4) -> dict:
    params = {"format": "json", "maxlag": 5, **params}
    for attempt in range(retries):
        try:
            r = requests.get(API, params=params, headers=HEADERS, timeout=30)
        except requests.RequestException as e:  # dropped Wi-Fi, DNS hiccup: wait and retry
            print(f"  network error ({type(e).__name__}), retrying in {10 * (attempt + 1)}s", flush=True)
            time.sleep(10 * (attempt + 1))
            continue
        if r.ok and r.text.startswith("{"):
            data = r.json()
            if data.get("error", {}).get("code") != "maxlag":
                return data
        time.sleep(2 ** attempt)
    raise RuntimeError(f"Commons API kept failing for {params.get('gsrsearch') or params}")


def search_year(year: int, limit: int):
    """Yield file metadata for up to `limit` images in the year's fashion-show tree."""
    for look in search(f'deepcat:"{year} fashion shows"', limit):
        yield {**look, "year": year}


def search(query: str, limit: int):
    """Yield file metadata (no year) for up to `limit` bitmaps matching a Commons search."""
    offset = 0
    while offset < limit:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"{query} filetype:bitmap",
            "gsrnamespace": 6,
            "gsrlimit": min(BATCH, limit - offset),
            "gsroffset": offset,
            "prop": "imageinfo|categories",
            "iiprop": "url|extmetadata|mime",
            "iiurlwidth": THUMB_WIDTH,
            "cllimit": "max",
            "clshow": "!hidden",
        }
        # deepcat can time out on big category trees and silently return a partial
        # result with only a warning - retry until it completes.
        for attempt in range(5):
            data = api_get(params)
            if "timed out" not in str(data.get("warnings", "")):
                break
            print(f"  {query}: category search timed out, retrying", flush=True)
            time.sleep(5 * (attempt + 1))
        else:
            print(f"  {query}: category search still timing out - results may be incomplete", flush=True)
        pages = data.get("query", {}).get("pages", {})
        for p in sorted(pages.values(), key=lambda p: p.get("index", 0)):
            info = (p.get("imageinfo") or [{}])[0]
            if info.get("mime") not in ("image/jpeg", "image/png"):
                continue
            meta = info.get("extmetadata", {})
            yield {
                "pageid": p["pageid"],
                "title": p["title"],
                "page_url": info.get("descriptionurl", ""),
                "thumb_url": info.get("thumburl", ""),
                "artist": credit(meta.get("Artist", {}).get("value")),
                "license": strip_html(meta.get("LicenseShortName", {}).get("value")),
                "categories": "|".join(c["title"].removeprefix("Category:") for c in p.get("categories", [])),
            }
        if "continue" not in data:
            return
        offset = data["continue"]["gsroffset"]
        time.sleep(0.5)


def download(url: str, dest) -> bool:
    for attempt in range(5):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
        except requests.RequestException:
            time.sleep(5)
            continue
        if r.ok:
            dest.write_bytes(r.content)
            return True
        if r.status_code == 429:
            wait = min(int(r.headers.get("retry-after", 60)), 300)
            print(f"  rate-limited, waiting {wait}s", flush=True)
            time.sleep(wait)
            continue
        return False
    return False


def parse_years(spec: str) -> list[int]:
    if "-" in spec:
        a, b = spec.split("-")
        return list(range(int(a), int(b) + 1))
    return [int(y) for y in spec.split(",")]


# Designer-show trees that aren't always filed under "<year> fashion shows".
EXTRA_TREES = ["Paris Fashion Week", "Milan Fashion Week", "New York Fashion Week", "London Fashion Week",
               "Haute couture", "Fashion shows by designer"]
YEAR_RE = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")


def year_of(look: dict) -> int | None:
    """Year from the show name (or title) for looks found outside the per-year trees."""
    _, show = classify(look["categories"], look["title"])
    m = YEAR_RE.search(show) or YEAR_RE.search(look["title"])
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--years", default="2007-2026", help="e.g. 2007-2025 or 2010,2015,2020")
    ap.add_argument("--per-year", type=int, default=600, help="max new looks per year (after tier filtering)")
    ap.add_argument("--tiers", default="major,fashion_week",
                    help="which show tiers to download: major, fashion_week, event (see sources.py)")
    ap.add_argument("--no-extra", action="store_true", help="skip the designer / fashion-week category trees")
    ap.add_argument("--trees", help="only these extra trees, comma-separated (skips the per-year search)")
    args = ap.parse_args()
    years, tiers = set(parse_years(args.years)), set(args.tiers.split(","))

    conn = connect()
    added: dict[int, int] = {}

    def save(look: dict) -> bool:
        if look["year"] not in years or added.get(look["year"], 0) >= args.per_year:
            return False
        if classify(look["categories"], look["title"])[0] not in tiers:
            return False  # e.g. college or charity shows - not worth the download
        if conn.execute("SELECT 1 FROM looks WHERE pageid = ?", (look["pageid"],)).fetchone():
            return False
        dest = IMAGE_DIR / f"{look['pageid']}.jpg"
        if not look["thumb_url"] or not download(look["thumb_url"], dest):
            return False
        look["local_path"] = str(dest.relative_to(ROOT))
        conn.execute(
            "INSERT INTO looks (pageid, title, year, page_url, thumb_url, artist, license, categories, local_path) "
            "VALUES (:pageid, :title, :year, :page_url, :thumb_url, :artist, :license, :categories, :local_path)",
            look,
        )
        conn.commit()  # commit per look so the tagger never waits on a long write lock
        added[look["year"]] = added.get(look["year"], 0) + 1
        time.sleep(PAUSE)
        return True

    if not args.trees:
        for year in sorted(years):
            n = sum(save(look) for look in search_year(year, 5000))
            print(f"{year}: +{n} looks", flush=True)

    if not args.no_extra:
        for tree in (args.trees.split(",") if args.trees else EXTRA_TREES):
            n = sum(save({**look, "year": y}) for look in search(f'deepcat:"{tree}"', 5000) if (y := year_of(look)))
            print(f"{tree}: +{n} looks", flush=True)


if __name__ == "__main__":
    main()
