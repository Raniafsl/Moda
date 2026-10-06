"""Build deploy/: a self-contained copy of Moda for a public host (e.g. Streamlit Community Cloud).

    python -m runway.bundle

deploy/ holds the app code plus only the data the dashboard reads:
  - Vogue: the two derived files (per-show shares + gallery picks), not the 1.3 GB embeddings
  - runway.db, slimmed: no embeddings, no excluded shows; Commons photos load from Wikimedia
  - your saved looks as small thumbnails, credited (they're copies of other people's photos -
    push deploy/ to a PRIVATE repo, never to the public Moda repo)

The app on the host only reads results, so its requirements skip torch/transformers entirely.
Re-run after adding shows; it updates deploy/ in place and keeps deploy/.git.
"""

import shutil
import sqlite3

from PIL import Image

from .db import DATA_DIR, DB_PATH, ROOT
from .personal import PERSONAL_DIR
from .vogue import SHOW_SHARES, TOP_LOOKS

DEPLOY = ROOT / "deploy"
THUMB_WIDTH = 360  # small enough to be a thumbnail, big enough to read a print
CODE = ["app.py", ".streamlit/config.toml"] + [f"runway/{p.name}" for p in (ROOT / "runway").glob("*.py")]
REQUIREMENTS = """\
# Read-only dashboard: no model code runs on the host.
streamlit==1.65.0
pandas==3.0.6
numpy==2.5.3
altair==6.3.0
pyarrow==25.0.1
"""
README = """\
# Moda (deployment bundle)

Built by `python -m runway.bundle` in the main Moda repo. Don't edit here; re-run the bundle instead.

This repo must stay **private**: `data/personal/` holds thumbnails of runway photos saved from Tagwalk,
shown in the app with credit and a link to each collection. The Vogue Runway files are derived
statistics and image links from a scraped dataset; Wikimedia Commons photos load from Wikimedia.
"""


def copy_code() -> None:
    for rel in CODE:
        dest = DEPLOY / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)
    (DEPLOY / "requirements.txt").write_text(REQUIREMENTS)
    (DEPLOY / "README.md").write_text(README)
    (DEPLOY / ".gitignore").write_text("__pycache__/\n.DS_Store\n")


def copy_vogue() -> None:
    out = DEPLOY / "data" / "vogue"
    out.mkdir(parents=True, exist_ok=True)
    for f in (SHOW_SHARES, TOP_LOOKS):
        if f.exists():
            shutil.copy2(f, out / f.name)


def slim_db() -> None:
    dest = DEPLOY / "data" / DB_PATH.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.unlink(missing_ok=True)
    src = sqlite3.connect(DB_PATH)
    out = sqlite3.connect(dest)
    src.backup(out)  # consistent copy even if ingest/tag are running
    src.close()
    out.executescript("""
        PRAGMA journal_mode = DELETE;
        DROP TABLE IF EXISTS embeddings;
        DELETE FROM tags WHERE pageid IN (SELECT pageid FROM looks WHERE tier = 'excluded' OR is_runway IS NULL);
        DELETE FROM looks WHERE tier = 'excluded' OR is_runway IS NULL;
    """)
    out.commit()
    out.execute("VACUUM")
    out.close()


def thumbnails() -> int:
    out = DEPLOY / "data" / PERSONAL_DIR.name
    out.mkdir(parents=True, exist_ok=True)
    keep = set()
    for src in PERSONAL_DIR.glob("*.jpg"):
        dest = out / src.name
        keep.add(dest.name)
        if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
            continue
        with Image.open(src) as im:
            im.thumbnail((THUMB_WIDTH, THUMB_WIDTH * 2))
            im.save(dest, quality=82, optimize=True)
    for stale in out.glob("*.jpg"):  # looks removed with `personal clear`
        if stale.name not in keep:
            stale.unlink()
    return len(keep)


def size(path) -> str:
    files = [path] if path.is_file() else [f for f in path.rglob("*") if f.is_file() and ".git" not in f.parts]
    total = sum(f.stat().st_size for f in files)
    return f"{total / 1e6:.0f} MB"


def main():
    DEPLOY.mkdir(exist_ok=True)
    copy_code()
    copy_vogue()
    slim_db()
    n = thumbnails()
    print(f"deploy/ ready: {size(DEPLOY)}  (db {size(DEPLOY / 'data' / DB_PATH.name)}, "
          f"{n} thumbnails {size(DEPLOY / 'data' / PERSONAL_DIR.name)}, vogue {size(DEPLOY / 'data' / 'vogue')})")
    big = [f for f in DEPLOY.rglob("*") if f.is_file() and ".git" not in f.parts and f.stat().st_size > 95e6]
    if big:
        print("Warning: GitHub rejects files over 100 MB:", ", ".join(str(f.relative_to(DEPLOY)) for f in big))
    if not (DEPLOY / ".git").exists():
        print("Next: push deploy/ to a PRIVATE GitHub repo, then deploy it on share.streamlit.io (main file: app.py).")


if __name__ == "__main__":
    main()
