"""SQLite storage for looks, attribute scores and image embeddings."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
IMAGE_DIR = DATA_DIR / "images"
DB_PATH = DATA_DIR / "runway.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS looks (
    pageid      INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    year        INTEGER NOT NULL,
    page_url    TEXT NOT NULL,
    thumb_url   TEXT NOT NULL,
    artist      TEXT,
    license     TEXT,
    categories  TEXT,
    local_path  TEXT,
    is_runway   REAL,         -- probability the photo is a runway look (set by tagger)
    tier        TEXT,         -- major / fashion_week / event / excluded (see sources.py)
    show        TEXT,         -- show the look belongs to, e.g. "Paris Fashion Week Autumn Winter 2019"
    source      TEXT DEFAULT 'commons',  -- 'commons' or 'personal' (your own saved looks)
    private     INTEGER DEFAULT 0,       -- 1 = analyse only, never display the image
    designer    TEXT,
    season      TEXT
);

CREATE TABLE IF NOT EXISTS tags (
    pageid      INTEGER NOT NULL REFERENCES looks(pageid),
    attr_group  TEXT NOT NULL,
    label       TEXT NOT NULL,
    score       REAL NOT NULL,  -- softmax probability within the group
    PRIMARY KEY (pageid, attr_group, label)
);

CREATE TABLE IF NOT EXISTS embeddings (
    pageid      INTEGER PRIMARY KEY REFERENCES looks(pageid),
    vec         BLOB NOT NULL   -- float32, L2-normalised
);
"""


# Columns added after the first release; ALTER them onto older databases.
MIGRATIONS = {
    "tier": "TEXT", "show": "TEXT", "source": "TEXT DEFAULT 'commons'",
    "private": "INTEGER DEFAULT 0", "designer": "TEXT", "season": "TEXT",
}


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    IMAGE_DIR.mkdir(exist_ok=True)
    # WAL + a busy timeout let ingest and tag run side by side.
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    have = {row[1] for row in conn.execute("PRAGMA table_info(looks)")}
    for col, decl in MIGRATIONS.items():
        if col not in have:
            conn.execute(f"ALTER TABLE looks ADD COLUMN {col} {decl}")
    backfill_tiers(conn)
    return conn


def backfill_tiers(conn: sqlite3.Connection) -> None:
    """Classify any Commons looks that don't have a tier yet (cheap - pure regex)."""
    from .sources import classify

    rows = conn.execute("SELECT pageid, categories, title FROM looks WHERE tier IS NULL AND source = 'commons'").fetchall()
    if rows:
        conn.executemany("UPDATE looks SET tier = ?, show = ? WHERE pageid = ?",
                         [(*classify(cats, title), pid) for pid, cats, title in rows])
        conn.commit()
