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
ALIASES = {"alaia": {"azzedinealaia"}, "saintlaurent": {"yvessaintlaurent"}, "celine": {"celine"},
           "dior": {"christiandior"}}


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


def personal_history(group: str, kind: str, category: str, before_year: int) -> pd.DataFrame:
    """Earlier seasons you've saved (e.g. Spring 2025 and 2026), shaped like the Vogue rows,
    so they fill the gap between the end of the Vogue archive and the latest season."""
    conn = connect()
    conn.executescript(SCHEMA)
    df = pd.read_sql_query(
        """SELECT l.designer, l.season AS season_name, c.label, AVG(c.score) AS share
           FROM clip_tags c JOIN looks l USING (pageid)
           WHERE l.source = 'personal' AND c.attr_group = ?
           GROUP BY l.designer, l.season, c.label""",
        conn, params=(group,),
    )
    if df.empty:
        return df
    parsed = df.season_name.map(parse_season)
    df = df.assign(season=[p[0] for p in parsed], year=[p[1] for p in parsed], category=[p[2] for p in parsed])
    df = df[(df.season == kind) & (df.category == category) & (df.year < before_year)]
    return df.assign(key=df.designer.map(norm), origin="saved")[["designer", "key", "season", "year", "label", "share", "origin"]]


def _previous(saved: pd.DataFrame, now: pd.Series, label: str, year: int, kind: str, min_houses: int = 3) -> dict | None:
    """Same houses, last year's saved season vs this one - answers 'is this new, or did it start earlier?'"""
    if saved is None or saved.empty:
        return None
    prev = saved[(saved.year == year - 1) & (saved.label == label)].set_index("designer").share
    both = sorted(set(prev.index) & set(now.index))
    if len(both) < min_houses:
        return None
    a, b = prev[both], now[both]
    return {"season": f"{kind} {year - 1}", "houses": both, "prev": float(a.mean()), "now": float(b.mean()),
            "lift": float(b.mean() / a.mean()) if a.mean() > 0 else float("nan"),
            "up": int((b > a * 1.2).sum()), "down": int((b < a * 0.8).sum())}


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
    hist_all = vogue[(vogue.season == kind) & (vogue.year < year)].assign(origin="vogue")
    saved = personal_history(group, kind, category, year)
    if len(saved):
        # A season you saved replaces the archive's copy of the same house-season, if both exist.
        dup = hist_all.set_index(["key", "year"]).index.isin(saved.set_index(["key", "year"]).index)
        hist_all = pd.concat([hist_all[~dup], saved], ignore_index=True)

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
    origin = same.groupby("year").origin.agg(lambda o: "saved" if (o == "saved").any() else "vogue").rename("origin")
    series = per_year[per_year.label == label][["year", "share", "houses"]].merge(origin, left_on="year", right_index=True)

    latest = now.mean()
    # The headline baseline is the archive's last season; saved seasons get their own year-on-year comparison.
    archive = series[series.origin == "vogue"]
    last = archive.iloc[-1] if len(archive) else (series.iloc[-1] if len(series) else None)
    higher = series[series.share >= latest]
    with_hist = houses[houses.seasons > 0]

    # What stands out: every label in the group, latest vs. the same houses' last `recent` seasons.
    recent_years = sorted(per_year.year.unique())[-recent:]
    base_all = per_year[per_year.year.isin(recent_years)].groupby("label").share.mean()
    now_all = shows.groupby("label").share.mean()
    standouts = (now_all / base_all).dropna().sort_values(ascending=False).rename("lift").to_frame()
    standouts = standouts.assign(now=now_all, base=base_all).reset_index()
    standouts = standouts[(standouts.now >= min_share) | (standouts.base >= min_share)]  # ignore near-zero labels

    # Seasons with no usable data between the end of the archive and the latest season.
    vogue_years = series[series.origin == "vogue"].year
    present = set(series.year)
    missing = [y for y in range(int(vogue_years.max()) + 1, year) if y not in present] if len(vogue_years) else []
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
        "saved_years": sorted(saved.year.unique().tolist()) if len(saved) else [],
        "prev": _previous(saved, now, label, year, kind),
        # saved seasons that exist but cover too few of these houses to chart: {year: houses saved}
        "partial": {int(y): int(n) for y, n in same[same.origin == "saved"].groupby("year").key.nunique().items()
                    if y not in set(series.year)},
        # every label, unfiltered - for palettes and other whole-group views
        "now_all": now_all, "base_all": base_all, "recent_years": recent_years,
        "per_house": shows.pivot_table(index="designer", columns="label", values="share"),
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
