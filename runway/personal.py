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
    python -m runway.personal import-show ~/Downloads/miumiu-ss27 --designer "Miu Miu" --season "Spring 2027 Ready-to-Wear" --credit Tagwalk
    python -m runway.tag                       # tags the new looks
    python -m runway.personal import-downloads   # every '<house> ss27' / 'dior fw26' folder in ~/Downloads
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


def import_show(folder: Path, designer: str, season: str, page_url: str | None, credit: str = "") -> None:
    """One flat folder of looks from a single show."""
    if page_url is None:
        page_url = vogue_url(designer, season)
    added, skipped = import_folder(connect(), folder, designer, season, page_url, credit)
    print(f"{designer} {season}: imported {added} looks ({skipped} already there). Run `python -m runway.tag` next.")


def vogue_url(designer: str, season: str) -> str:
    """Default link-out, e.g. ('Miu Miu', 'Spring 2027 Ready-to-Wear') -> vogue.com/fashion-shows/spring-2027-ready-to-wear/miu-miu"""
    ascii_ = lambda t: unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()  # Hermès -> Hermes
    slug = lambda t: re.sub(r"[^a-z0-9]+", "-", ascii_(t).lower()).strip("-")
    return f"https://www.vogue.com/fashion-shows/{slug(season)}/{slug(designer)}"


def import_folder(conn, folder: Path, designer: str, season: str, page_url: str, credit: str = "") -> tuple[int, int]:
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
        # Same file in the same season counts as already imported, even if it was filed under another house before.
        if conn.execute("SELECT 1 FROM looks WHERE pageid = ? OR (source = 'personal' AND title LIKE ?)",
                        (pid, f"%/{season}/{img_path.name}")).fetchone():
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
               VALUES (?, ?, ?, ?, '', ?, 'personal research copy', ?, ?, 'major', ?, 'personal', 1, ?, ?)""",
            (pid, rel, year, page_url, credit, f"{designer}|{season}", str(dest.relative_to(ROOT)),
             f"{designer} {season}", designer, season),
        )
        added += 1
    conn.commit()
    return added, skipped


# Folder names you might use -> the house's name (matching Vogue Runway where possible).
DESIGNERS = {
    "lv": "Louis Vuitton", "louis vuitton": "Louis Vuitton", "louisvuitton": "Louis Vuitton",
    "armani": "Giorgio Armani", "giorgio armani": "Giorgio Armani", "giorgioarmani": "Giorgio Armani",
    "dior": "Dior", "christian dior": "Dior", "christiandior": "Dior",
    "ysl": "Saint Laurent", "saint laurent": "Saint Laurent", "saintlaurent": "Saint Laurent",
    "miumiu": "Miu Miu", "miu miu": "Miu Miu", "hermes": "Hermès", "hermès": "Hermès",
    "alaia": "Alaïa", "alaïa": "Alaïa", "ellie saab": "Elie Saab", "elie saab": "Elie Saab", "eliesaab": "Elie Saab",
    "zimmerman": "Zimmermann", "zimmermann": "Zimmermann", "v-westwood": "Vivienne Westwood",
    "vivienne westwood": "Vivienne Westwood", "viviennewestwood": "Vivienne Westwood",
    "jpg": "Jean Paul Gaultier", "jean paul gaultier": "Jean Paul Gaultier", "jeanpaulgaultier": "Jean Paul Gaultier",
    "isabel marant": "Isabel Marant", "isabelmarant": "Isabel Marant", "stella mccartney": "Stella McCartney",
    "stellamccartney": "Stella McCartney", "mcqueen": "Alexander McQueen", "alexander mcqueen": "Alexander McQueen",
    "dolce": "Dolce & Gabbana", "d&g": "Dolce & Gabbana", "dolce gabbana": "Dolce & Gabbana",
    "bottega": "Bottega Veneta", "bottega veneta": "Bottega Veneta", "bottegaveneta": "Bottega Veneta",
}
FOLDER_RE = re.compile(r"^(?P<name>.+?)[\s_-]+(?P<couture>couture[\s_-]+)?(?P<kind>ss|fw|aw|resort|prefall|pre-fall|spring|fall)[\s_-]?(?P<yy>\d{4}|\d{2})(?P<rest>.*)$", re.I)
KIND_WORD = {"ss": "Spring", "spring": "Spring", "fw": "Fall", "aw": "Fall", "fall": "Fall",
             "resort": "Resort", "prefall": "Pre-Fall", "pre-fall": "Pre-Fall"}


def designer_name(text: str) -> str:
    key = text.strip().lower()
    return DESIGNERS.get(key) or DESIGNERS.get(re.sub(r"[^a-z]", "", key)) or text.strip().title()


def parse_folder(name: str) -> tuple[str, str] | None:
    """'chanel ss27' -> ('Chanel', 'Spring 2027 Ready-to-Wear'); 'dior couture fw26' -> ('Dior', 'Fall 2026 Couture')."""
    m = FOLDER_RE.match(name.strip())
    if not m:
        return None
    yy = m.group("yy")
    year = int(yy) if len(yy) == 4 else 2000 + int(yy)
    category = "Couture" if m.group("couture") or "couture" in m.group("rest").lower() else "Ready-to-Wear"
    return designer_name(m.group("name")), f"{KIND_WORD[m.group('kind').lower()]} {year} {category}"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower())


def _house_slugs() -> list[tuple[str, str]]:
    """('valentino', 'Valentino'), ('christiandior', 'Dior'), ... longest first, so 'redvalentino' beats 'valentino'."""
    from .sources import HOUSES

    pairs = {_slug(k): v for k, v in DESIGNERS.items()}
    pairs.update({_slug(h): DESIGNERS.get(h.lower(), h) for h in HOUSES})
    pairs.update({_slug(d): d for (d,) in connect().execute("SELECT DISTINCT designer FROM looks WHERE source = 'personal'")})
    return sorted(((k, v) for k, v in pairs.items() if len(k) >= 4), key=lambda kv: -len(kv[0]))


def file_designer(filename: str, slugs: list[tuple[str, str]] | None = None) -> str | None:
    """Tagwalk names files like 'valentinoss27064-....webp': the house is whichever known name the file starts with."""
    name = filename.lower()
    return next((house for slug, house in (slugs or _house_slugs()) if name.startswith(slug)), None)


def import_downloads(root: Path, credit: str = "Tagwalk", dry_run: bool = False) -> None:
    """Import every '<house> <season>' folder in `root` (e.g. ~/Downloads/chanel ss27), routing stray looks to the
    house their file name says they belong to. Safe to re-run: looks already imported are skipped."""
    import tempfile

    conn = connect()
    slugs = _house_slugs()
    total = 0
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        parsed = parse_folder(folder.name)
        if not parsed:
            continue
        house, season = parsed
        by_house: dict[str, list[Path]] = {}
        for f in folder.iterdir():
            if f.suffix.lower() in EXTS:
                by_house.setdefault(file_designer(f.name, slugs) or house, []).append(f)
        for who, files in sorted(by_house.items()):
            moved = "" if who == house else f"  (found in '{folder.name}', filed under {who})"
            if dry_run:
                print(f"  {who:20s} {season:28s} {len(files):3d} looks{moved}")
                continue
            with tempfile.TemporaryDirectory() as tmp:  # links only - your folders are never changed
                for f in files:
                    (Path(tmp) / f.name).symlink_to(f)
                added, skipped = import_folder(conn, Path(tmp), who, season, vogue_url(who, season), credit)
            total += added
            if added or moved:
                print(f"  {who:20s} {season:28s} +{added} new, {skipped} already in{moved}")
    if not dry_run:
        print(f"Imported {total} new looks. Run `python -m runway.tag` next.")


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
    one.add_argument("--credit", default="", help='where the photos came from, shown on each look, e.g. "Tagwalk"')
    dl = sub.add_parser("import-downloads", help="import every '<house> <season>' folder, e.g. ~/Downloads/chanel ss27")
    dl.add_argument("root", type=Path, nargs="?", default=Path.home() / "Downloads")
    dl.add_argument("--credit", default="Tagwalk")
    dl.add_argument("--dry-run", action="store_true", help="show what would be imported, change nothing")
    sub.add_parser("clear", help="remove all personal looks")
    args = ap.parse_args()
    if args.cmd == "import":
        import_archive(args.archive.expanduser())
    elif args.cmd == "import-downloads":
        import_downloads(args.root.expanduser(), args.credit, args.dry_run)
    elif args.cmd == "import-show":
        import_show(args.folder.expanduser(), args.designer, args.season, args.url, args.credit)
    else:
        clear()


if __name__ == "__main__":
    main()
