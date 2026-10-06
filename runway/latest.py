"""Latest season: your newest saved shows against each house's own history on Vogue Runway.

Your saved looks are scored a second time with standard CLIP, the model behind the Vogue
archive's embeddings, so "Spring 2027 vs. Spring 2015-2023" is like for like. (The FashionCLIP
scores used on the Trends page aren't on the same scale.)

    python -m runway.latest      # score any new personal looks (python -m runway.tag runs this for you)
"""

import re
import unicodedata

import numpy as np
import pandas as pd

from .db import ROOT, connect

SCHEMA = """
CREATE TABLE IF NOT EXISTS clip_tags (
    pageid      INTEGER NOT NULL,
    attr_group  TEXT NOT NULL,
    label       TEXT NOT NULL,
    score       REAL NOT NULL,   -- standard-CLIP softmax probability, comparable with the Vogue archive
    PRIMARY KEY (pageid, attr_group, label)
);
"""
SEASON_RE = re.compile(r"(pre-fall|resort|cruise|spring|summer|fall|autumn)\D*((?:19|20)\d{2})", re.I)
KIND = {"cruise": "Resort", "summer": "Spring", "autumn": "Fall", "pre-fall": "Pre-Fall"}
# Vogue sometimes files a house under another name.
ALIASES = {"alaia": {"azzedinealaia"}, "saintlaurent": {"yvessaintlaurent"}, "celine": {"celine"}}


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower())


def parse_season(season: str) -> tuple[str, int, str]:
    """'Spring 2027 Ready-to-Wear' -> ('Spring', 2027, 'Ready-to-Wear')"""
    m = SEASON_RE.search(season)
    if not m:
        raise ValueError(f"can't read a season from {season!r}")
    word = m.group(1).lower()
    kind = KIND.get(word, word.title())
    category = "Couture" if "couture" in season.lower() else "Menswear" if "menswear" in season.lower() else "Ready-to-Wear"
    return kind, int(m.group(2)), category


# ---------- scoring ----------

def score_personal(conn=None, batch: int = 32) -> int:
    """Score personal looks that don't have standard-CLIP tags yet. Returns how many were scored."""
    conn = conn or connect()
    conn.executescript(SCHEMA)
    todo = conn.execute(
        "SELECT pageid, local_path FROM looks WHERE source = 'personal' "
        "AND pageid NOT IN (SELECT DISTINCT pageid FROM clip_tags)"
    ).fetchall()
    if not todo:
        return 0
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor

    from .vogue import MODEL_ID, softmax, text_features

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = CLIPModel.from_pretrained(MODEL_ID).to(device).eval()
    processor = CLIPProcessor.from_pretrained(MODEL_ID)
    texts, scale = text_features(model, processor, device), float(model.logit_scale.exp())
    for start in range(0, len(todo), batch):
        part = todo[start:start + batch]
        with torch.no_grad():
            images = [Image.open(ROOT / path).convert("RGB") for _, path in part]
            v = model.get_image_features(**processor(images=images, return_tensors="pt").to(device)).pooler_output
        v = (v / v.norm(dim=-1, keepdim=True)).float().cpu().numpy()
        rows = []
        for group, (labels, t) in texts.items():
            probs = softmax(scale * v @ t.T)
            rows += [(pid, group, label, float(p)) for k, (pid, _) in enumerate(part) for label, p in zip(labels, probs[k])]
        conn.executemany("INSERT OR REPLACE INTO clip_tags VALUES (?, ?, ?, ?)", rows)
        conn.commit()
    return len(todo)


# ---------- comparison ----------

def latest_shows(group: str) -> pd.DataFrame:
    """Per-show mean standard-CLIP share for the most recent personal season."""
    conn = connect()
    conn.executescript(SCHEMA)
    df = pd.read_sql_query(
        """SELECT l.designer, l.season, l.year AS show_year, c.label, AVG(c.score) AS share, COUNT(*) AS n_looks
           FROM clip_tags c JOIN looks l USING (pageid)
           WHERE l.source = 'personal' AND c.attr_group = ?
           GROUP BY l.designer, l.season, c.label""",
        conn, params=(group,),
    )
    if df.empty:
        return df
    # The latest season = the one shown most recently; ties go to the season with the most shows.
    newest = df[df.show_year == df.show_year.max()]
    season = newest.groupby("season").designer.nunique().idxmax()
    return df[df.season == season]


def compare(group: str, label: str, recent: int = 5, min_share: float = 0.02) -> dict | None:
    """Latest saved season vs. the same houses' history for one label."""
    from .trends import load_vogue

    shows = latest_shows(group)
    if shows.empty:
        return None
    season = shows.season.iloc[0]
    kind, year, category = parse_season(season)
    vogue = load_vogue(group, [category])
    vogue = vogue.assign(key=vogue.designer.map(norm))
    hist_all = vogue[(vogue.season == kind) & (vogue.year < year)]

    def history_of(designer: str) -> pd.DataFrame:
        keys = {norm(designer)} | ALIASES.get(norm(designer), set())
        return hist_all[hist_all.key.isin(keys)]

    now = shows[shows.label == label].set_index("designer").share
    houses = []
    for designer, value in now.items():
        h = history_of(designer)
        h = h[h.label == label].sort_values("year").tail(recent)
        base = h.share.mean() if len(h) else np.nan
        houses.append({"designer": designer, "now": value, "base": base, "seasons": len(h),
                       "first": int(h.year.min()) if len(h) else None, "last": int(h.year.max()) if len(h) else None,
                       "lift": value / base if len(h) and base > 0 else np.nan})
    houses = pd.DataFrame(houses).sort_values("lift", ascending=False, na_position="last")

    # Same houses, season by season - only seasons where at least half of them showed.
    keys = set().union(*({norm(d)} | ALIASES.get(norm(d), set()) for d in now.index))
    same = hist_all[hist_all.key.isin(keys)]
    per_year = same.groupby(["year", "label"]).agg(share=("share", "mean"), houses=("key", "nunique")).reset_index()
    per_year = per_year[per_year.houses >= max(2, len(now) // 2)]
    series = per_year[per_year.label == label][["year", "share", "houses"]]

    latest = now.mean()
    last = series.iloc[-1] if len(series) else None
    higher = series[series.share >= latest]
    with_hist = houses[houses.seasons > 0]

    # What stands out: every label in the group, latest vs. the same houses' last `recent` seasons.
    recent_years = sorted(per_year.year.unique())[-recent:]
    base_all = per_year[per_year.year.isin(recent_years)].groupby("label").share.mean()
    now_all = shows.groupby("label").share.mean()
    standouts = (now_all / base_all).dropna().sort_values(ascending=False).rename("lift").to_frame()
    standouts = standouts.assign(now=now_all, base=base_all).reset_index()
    standouts = standouts[(standouts.now >= min_share) | (standouts.base >= min_share)]  # ignore near-zero labels

    missing = [y for y in range(int(last.year) + 1, year) if last is not None] if last is not None else []
    return {
        "season": season, "kind": kind, "year": year, "category": category,
        "n_shows": len(now), "n_looks": int(shows[shows.label == label].n_looks.sum()),
        "latest": latest, "houses": houses, "series": series,
        "last_year": int(last.year) if last is not None else None,
        "last_share": float(last.share) if last is not None else None,
        "highest_since": int(higher.year.max()) if len(higher) else None,
        "n_up": int((with_hist.lift >= 1.2).sum()), "n_down": int((with_hist.lift <= 0.8).sum()),
        "n_hist": len(with_hist), "no_history": list(houses[houses.seasons == 0].designer),
        "missing_years": missing, "standouts": standouts,
    }


if __name__ == "__main__":
    print(f"Scored {score_personal()} personal looks with standard CLIP.")


def latest_looks(group: str, label: str, designer: str | None = None, n: int = 12, per_show: int = 3) -> pd.DataFrame:
    """Looks from the latest saved season, highest-scoring for `label` first.
    With `designer`, that house's whole lineup; otherwise at most `per_show` per house, for variety."""
    shows = latest_shows(group)
    if shows.empty:
        return pd.DataFrame()
    season = shows.season.iloc[0]
    df = pd.read_sql_query(
        """SELECT l.pageid, l.designer, l.season, l.year, l.page_url, l.local_path, l.artist, c.score
           FROM clip_tags c JOIN looks l USING (pageid)
           WHERE l.source = 'personal' AND l.season = ? AND c.attr_group = ? AND c.label = ?
           ORDER BY c.score DESC""",
        connect(), params=(season, group, label),
    )
    if designer:
        return df[df.designer == designer]
    return df.groupby("designer").head(per_show).head(n)
