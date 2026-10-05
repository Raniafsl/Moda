"""Your personal research archive: looks you saved yourself, analysed but never displayed.

Lay your saved looks out as  <archive>/<Designer>/<Season>/<any>.jpg, e.g.

    moda-archive/
      Givenchy/
        Spring 2027 RTW/
          source.txt          <- optional: URL of the collection page, used for link-outs
          look01.jpg
          look02.jpg
      Schiaparelli/
        Fall 2025 Couture/
          ...

    python -m runway.personal import ~/Pictures/moda-archive
    python -m runway.personal import-show ~/Downloads/miumiu-ss27 --designer "Miu Miu" --season "Spring 2027 Ready-to-Wear"
    python -m runway.tag                       # tags the new looks
    python -m runway.personal clear            # remove every personal look again

Copies are resized into data/personal/ (git-ignored). They're marked private, so
the dashboard uses them in charts and stats but only ever shows a link out to
the original page, never the image itself.

Seasons are mapped to the year the show *happened*, to line up with Commons:
Spring/Summer and Resort/Cruise collections are shown the year before their name
("Spring 2027" -> 2026); Fall/Autumn/Winter and Pre-Fall are shown in their own year.
"""

import argparse
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

from PIL import Image

from .db import DATA_DIR, ROOT, connect

PERSONAL_DIR = DATA_DIR / "personal"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
SHOWN_YEAR_BEFORE = re.compile(r"\b(spring|summer|ss|s/s|resort|cruise)\b", re.I)


def show_year(season: str) -> int | None:
    m = re.search(r"\b(19|20)\d{2}\b", season)
    if not m:
        return None
    year = int(m.group(0))
    return year - 1 if SHOWN_YEAR_BEFORE.search(season) else year


def look_id(rel_path: str) -> int:
    """Stable negative id so personal looks can never collide with Commons page ids."""
    return -int(hashlib.sha1(rel_path.encode()).hexdigest()[:12], 16)


def import_archive(archive: Path) -> None:
    """<archive>/<Designer>/<Season>/*.jpg - many shows at once."""
    conn = connect()
    added = skipped = 0
    for season_dir in sorted(p for p in archive.glob("*/*") if p.is_dir()):
        src = season_dir / "source.txt"
        a, s = import_folder(conn, season_dir, season_dir.parent.name, season_dir.name,
                             src.read_text().strip() if src.exists() else "")
        added, skipped = added + a, skipped + s
    print(f"Imported {added} looks ({skipped} already there). Run `python -m runway.tag` next.")


def import_show(folder: Path, designer: str, season: str, page_url: str | None) -> None:
    """One flat folder of looks from a single show."""
    if page_url is None:
        page_url = vogue_url(designer, season)
    added, skipped = import_folder(connect(), folder, designer, season, page_url)
    print(f"{designer} {season}: imported {added} looks ({skipped} already there). Run `python -m runway.tag` next.")


def vogue_url(designer: str, season: str) -> str:
    """Default link-out, e.g. ('Miu Miu', 'Spring 2027 Ready-to-Wear') -> vogue.com/fashion-shows/spring-2027-ready-to-wear/miu-miu"""
    ascii_ = lambda t: unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()  # Hermès -> Hermes
    slug = lambda t: re.sub(r"[^a-z0-9]+", "-", ascii_(t).lower()).strip("-")
    return f"https://www.vogue.com/fashion-shows/{slug(season)}/{slug(designer)}"


def import_folder(conn, folder: Path, designer: str, season: str, page_url: str) -> tuple[int, int]:
    year = show_year(season)
    if year is None:
        print(f"  skip {designer}/{season}: no year in the season name", file=sys.stderr)
        return 0, 0
    PERSONAL_DIR.mkdir(exist_ok=True)
    added = skipped = 0
    for img_path in sorted(folder.iterdir()):
        if img_path.suffix.lower() not in EXTS:
            continue
        rel = f"{designer}/{season}/{img_path.name}"
        pid = look_id(rel)
        if conn.execute("SELECT 1 FROM looks WHERE pageid = ?", (pid,)).fetchone():
            skipped += 1
            continue
        dest = PERSONAL_DIR / f"{-pid}.jpg"
        try:
            with Image.open(img_path) as im:
                im = im.convert("RGB")
                im.thumbnail((500, 750))
                im.save(dest, quality=88)
        except Exception as e:
            print(f"  skip {rel}: {e}", file=sys.stderr)
            continue
        conn.execute(
            """INSERT INTO looks (pageid, title, year, page_url, thumb_url, artist, license, categories,
                                  local_path, tier, show, source, private, designer, season)
               VALUES (?, ?, ?, ?, '', '', 'personal research copy', ?, ?, 'major', ?, 'personal', 1, ?, ?)""",
            (pid, rel, year, page_url, f"{designer}|{season}", str(dest.relative_to(ROOT)),
             f"{designer} {season}", designer, season),
        )
        added += 1
    conn.commit()
    return added, skipped


def clear() -> None:
    conn = connect()
    ids = [r[0] for r in conn.execute("SELECT pageid FROM looks WHERE source = 'personal'")]
    for table in ("tags", "embeddings", "looks"):
        conn.executemany(f"DELETE FROM {table} WHERE pageid = ?", [(i,) for i in ids])
    conn.commit()
    for f in PERSONAL_DIR.glob("*.jpg"):
        f.unlink()
    print(f"Removed {len(ids)} personal looks.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    imp = sub.add_parser("import", help="import an archive folder")
    imp.add_argument("archive", type=Path)
    one = sub.add_parser("import-show", help="import one flat folder of looks from a single show")
    one.add_argument("folder", type=Path)
    one.add_argument("--designer", required=True, help='e.g. "Miu Miu"')
    one.add_argument("--season", required=True, help='e.g. "Spring 2027 Ready-to-Wear"')
    one.add_argument("--url", help="collection page for link-outs (default: its Vogue Runway page)")
    sub.add_parser("clear", help="remove all personal looks")
    args = ap.parse_args()
    if args.cmd == "import":
        import_archive(args.archive.expanduser())
    elif args.cmd == "import-show":
        import_show(args.folder.expanduser(), args.designer, args.season, args.url)
    else:
        clear()


if __name__ == "__main__":
    main()
