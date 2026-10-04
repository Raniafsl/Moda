"""Turn per-look attribute scores into year-over-year trend lines.

A label's *share* in a year is the average probability the model gave it across
that year's runway looks - a "soft" count, so a look that's 60% trench coat and
40% overcoat contributes to both. That's steadier than counting top-1 labels
when a year only has a few hundred photos.
"""

import numpy as np
import pandas as pd

from .db import connect
from .sources import TIER_ORDER


def tiers_upto(tier: str) -> list[str]:
    """'fashion_week' -> ['major', 'fashion_week']: each level includes the stricter ones."""
    return TIER_ORDER[: TIER_ORDER.index(tier) + 1]


def _tier_sql(tiers: list[str]) -> tuple[str, list]:
    # Personal looks are always designer shows, whatever their tier column says.
    return f"(l.source = 'personal' OR l.tier IN ({','.join('?' * len(tiers))}))", list(tiers)


def load_scores(min_runway: float = 0.5, tiers: list[str] = TIER_ORDER) -> pd.DataFrame:
    """One row per (look, group, label) for looks that pass the runway and show-tier filters."""
    where, params = _tier_sql(tiers)
    return pd.read_sql_query(
        f"""
        SELECT l.pageid, l.year, l.show, t.attr_group, t.label, t.score
        FROM tags t JOIN looks l USING (pageid)
        WHERE l.is_runway >= ? AND {where}
        """,
        connect(),
        params=[min_runway, *params],
    )


MIN_SHOW_LOOKS = 3  # fewer photos than this isn't a show we can read - usually a stray celebrity or place category


def yearly_share(scores: pd.DataFrame, group: str, min_looks: int = 25,
                 min_show_looks: int = MIN_SHOW_LOOKS) -> pd.DataFrame:
    """Year x label table of soft shares, one vote per show; drops years with too few looks to trust.

    Each look is weighted 1 / (looks in its show), so a show's weights sum to 1 and a
    heavily photographed show counts the same as a small one. Shows with fewer than
    `min_show_looks` photos are dropped, so a single stray photo can't carry a full vote.
    """
    g = scores[scores.attr_group == group]
    size = g.groupby(["year", "show"]).pageid.transform("nunique")
    g = g[g["show"].notna() & (g["show"] != "unknown") & (size >= min_show_looks)]
    counts = g.groupby("year").pageid.nunique()
    keep = counts[counts >= min_looks].index
    g = g[g.year.isin(keep)]

    # nunique, not count: each look appears once per label.
    n = g.groupby(["year", "show"]).pageid.transform("nunique")
    g = g.assign(w=1 / n, ws=g.score / n)
    sums = g.groupby(["year", "label"])[["ws", "w"]].sum()
    return (sums.ws / sums.w).unstack("label").sort_index()


def movers(share: pd.DataFrame, recent_years: int = 3) -> pd.DataFrame:
    """Compare each label's recent share against its earlier baseline.

    lift  = recent mean / baseline mean (1.5 means 50% more common lately)
    slope = linear trend in percentage points per year across all years
    """
    if len(share) < recent_years + 2:
        return pd.DataFrame(columns=["label", "recent", "baseline", "lift", "slope"])
    recent = share.iloc[-recent_years:].mean()
    baseline = share.iloc[:-recent_years].mean()
    years = share.index.to_numpy(dtype=float)
    slope = share.apply(lambda col: np.polyfit(years, col.to_numpy() * 100, 1)[0])
    out = pd.DataFrame({"recent": recent, "baseline": baseline, "lift": recent / baseline, "slope": slope})
    return out.rename_axis("label").reset_index().sort_values("lift", ascending=False)


def top_looks(group: str, label: str, year: int | None = None, min_runway: float = 0.5,
              tiers: list[str] = TIER_ORDER, n: int = 8) -> pd.DataFrame:
    """Highest-scoring looks for a label, for the example gallery."""
    conn = connect()
    where, tier_params = _tier_sql(tiers)
    sql = f"""
        SELECT l.pageid, l.year, l.title, l.page_url, l.artist, l.license, l.local_path, l.show,
               l.private, l.designer, l.season, t.score
        FROM tags t JOIN looks l USING (pageid)
        WHERE t.attr_group = ? AND t.label = ? AND l.is_runway >= ? AND {where}
    """
    params: list = [group, label, min_runway, *tier_params]
    if year is not None:
        sql += " AND l.year = ?"
        params.append(year)
    sql += " ORDER BY t.score DESC LIMIT ?"
    params.append(n)
    return pd.read_sql_query(sql, conn, params=params)


def summary(min_runway: float = 0.5, tiers: list[str] = TIER_ORDER) -> dict:
    where, params = _tier_sql(tiers)
    looks, shows, personal = connect().execute(
        f"SELECT COUNT(*), COUNT(DISTINCT show), SUM(source = 'personal') FROM looks l WHERE is_runway >= ? AND {where}",
        (min_runway, *params),
    ).fetchone()
    tagged, runway = connect().execute("SELECT COUNT(is_runway), SUM(is_runway >= ?) FROM looks", (min_runway,)).fetchone()
    return {"looks": looks or 0, "shows": shows or 0, "personal": personal or 0,
            "tagged": tagged or 0, "runway": runway or 0}


# ---------- Vogue Runway archive (built by `python -m runway.vogue build`) ----------

def vogue_available() -> bool:
    from .vogue import SHOW_SHARES
    return SHOW_SHARES.exists()


def load_vogue(group: str, categories: list[str]) -> pd.DataFrame:
    """Per-show shares for one attribute group, limited to the chosen collection types."""
    from .vogue import SHOW_SHARES
    df = pd.read_parquet(SHOW_SHARES, filters=[("attr_group", "==", group)])
    return df[df.category.isin(categories)]


def vogue_yearly_share(shows: pd.DataFrame, min_shows: int = 25) -> pd.DataFrame:
    """Year x label: mean of per-show shares, so each show is one vote."""
    counts = shows.groupby("show_year")["show"].nunique()
    keep = counts[counts >= min_shows].index
    share = shows[shows.show_year.isin(keep)].pivot_table(index="show_year", columns="label", values="share", aggfunc="mean")
    return share.rename_axis("year").sort_index()


def vogue_summary(shows: pd.DataFrame) -> dict:
    per_show = shows.drop_duplicates("show")
    return {"looks": int(per_show.n_looks.sum()), "shows": len(per_show), "designers": per_show.designer.nunique()}


def vogue_top_looks(group: str, label: str, year: int | None, categories: list[str], n: int = 8) -> pd.DataFrame:
    """Best-scoring Vogue looks for the gallery; images are hotlinked from Vogue, credited, never stored."""
    from .vogue import TOP_LOOKS
    df = pd.read_parquet(TOP_LOOKS, filters=[("attr_group", "==", group), ("label", "==", label)])
    df = df[df.category.isin(categories)]
    if year is not None:
        df = df[df.show_year == year]
    df = df.sort_values("score", ascending=False).drop_duplicates("show").head(n)  # one look per show
    return df.assign(private=0, year=df.show_year, artist="Vogue Runway", license="© Vogue / the photographer",
                     season=df.season + " " + df.year.astype(str) + " " + df.category)


def comebacks(share: pd.DataFrame, recent_years: int = 3, smooth: int = 3,
              min_drop: float = 0.8, min_recovery: float = 1.2) -> pd.DataFrame:
    """Labels that peaked, faded, and are climbing back - which plain rising/fading misses.

    On a `smooth`-year rolling mean (so one odd year isn't a peak): find the earlier peak,
    the lowest point after it (before the recent window), and compare the recent mean.
    A comeback needs trough <= min_drop * peak and recent >= min_recovery * trough.
    """
    if len(share) < recent_years + smooth + 2:
        return pd.DataFrame()
    rolled = share.rolling(smooth, center=True, min_periods=1).mean()
    history, recent = rolled.iloc[:-recent_years], share.iloc[-recent_years:].mean()
    rows = []
    for label in share.columns:
        col = history[label]
        peak_year = col.idxmax()
        after = col.loc[peak_year:]
        if len(after) < 2:
            continue
        trough_year = after.idxmin()
        peak, trough = col[peak_year], after[trough_year]
        if trough <= min_drop * peak and recent[label] >= min_recovery * trough:
            rows.append({"label": label, "peak": peak, "peak_year": peak_year, "trough": trough,
                         "trough_year": trough_year, "recent": recent[label], "recovery": recent[label] / trough})
    return pd.DataFrame(rows).sort_values("recovery", ascending=False) if rows else pd.DataFrame()
