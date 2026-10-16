"""How accurate are Moda's labels? A small hand-checked evaluation.

The Vogue archive and the Latest season page both use standard CLIP, so that's what we check,
on your saved looks (the only CLIP-scored looks with local images). For each look the
model's top label in a group is shown; you answer yes / no / can't tell. Per-label
precision = yes / (yes + no): "when Moda says floral, how often is it actually floral?"

Labelling only works locally - a deployed copy (deploy/data/DEPLOYED exists) shows results only.
"""

import math
import random

import pandas as pd
import streamlit as st

from . import ui
from .db import DATA_DIR, ROOT, connect
from .vocab import GROUPS, display

DEPLOYED = (DATA_DIR / "DEPLOYED").exists()
MODEL = "clip"
MIN_CHECKS = 8  # fewer checks than this and a label is "not enough checks yet"

SCHEMA = """
CREATE TABLE IF NOT EXISTS eval_labels (
    pageid      INTEGER NOT NULL,
    attr_group  TEXT NOT NULL,
    label       TEXT NOT NULL,   -- the model's top label for this look in this group
    model       TEXT NOT NULL,
    score       REAL,
    verdict     INTEGER,         -- 1 = right, 0 = wrong, NULL = can't tell
    PRIMARY KEY (pageid, attr_group, model)
);
"""

QUESTION = {
    "colour": "Is this outfit mostly <b>{}</b>?",
    "garment": "Is the model wearing <b>{}</b>?",
    "pattern": "Does this outfit have <b>{}</b>?",
    "silhouette": "Does this outfit have a <b>{}</b> silhouette?",
    "material": "Is this outfit made of <b>{}</b>?",
}


def _conn():
    conn = connect()
    conn.executescript(SCHEMA)
    return conn


def top_predictions(group: str) -> pd.DataFrame:
    """The model's top label for every saved look in a group, with the ones already judged marked."""
    return pd.read_sql_query(
        """
        WITH ranked AS (
            SELECT c.pageid, c.label, c.score,
                   ROW_NUMBER() OVER (PARTITION BY c.pageid ORDER BY c.score DESC) AS r
            FROM clip_tags c JOIN looks l USING (pageid)
            WHERE c.attr_group = ? AND l.source = 'personal' AND l.is_runway >= 0.5
        )
        SELECT r.pageid, r.label, r.score, l.local_path, l.designer,
               e.pageid IS NOT NULL AS judged
        FROM ranked r JOIN looks l USING (pageid)
        LEFT JOIN eval_labels e ON e.pageid = r.pageid AND e.attr_group = ? AND e.model = ?
        WHERE r.r = 1
        """,
        _conn(), params=(group, group, MODEL),
    )


def next_item(group: str) -> dict | None:
    """Pick an unjudged look, favouring the label with the fewest checks so every label gets covered."""
    preds = top_predictions(group)
    todo = preds[~preds.judged.astype(bool)]
    if todo.empty:
        return None
    checked = preds[preds.judged.astype(bool)].groupby("label").size()
    counts = todo.label.map(lambda l: checked.get(l, 0))
    label = todo[counts == counts.min()].label.sample(1, random_state=random.randrange(10**6)).iloc[0]
    return todo[todo.label == label].sample(1, random_state=random.randrange(10**6)).iloc[0].to_dict()


def record(pageid: int, group: str, label: str, score: float, verdict: int | None) -> None:
    conn = _conn()
    conn.execute("INSERT OR REPLACE INTO eval_labels VALUES (?, ?, ?, ?, ?, ?)",
                 (pageid, group, label, MODEL, score, verdict))
    conn.commit()


def undo_last() -> None:
    conn = _conn()
    conn.execute("DELETE FROM eval_labels WHERE rowid = (SELECT MAX(rowid) FROM eval_labels)")
    conn.commit()


def wilson_low(yes: int, n: int, z: float = 1.64) -> float:
    """Lower bound of a ~90% confidence interval - keeps 3/3 from looking like a sure thing."""
    if n == 0:
        return 0.0
    p = yes / n
    return (p + z * z / (2 * n) - z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / (1 + z * z / n)


def results() -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT attr_group, label, SUM(verdict = 1) AS yes, SUM(verdict = 0) AS no, SUM(verdict IS NULL) AS unsure "
        "FROM eval_labels WHERE model = ? GROUP BY attr_group, label",
        _conn(), params=(MODEL,),
    )
    if df.empty:
        return df
    df["n"] = df.yes + df.no
    df["precision"] = (df.yes / df.n).where(df.n > 0)
    df["low"] = [wilson_low(int(y), int(n)) for y, n in zip(df.yes, df.n)]
    df["verdict"] = [
        "not enough checks" if n < MIN_CHECKS else "reliable" if p >= .75 else "shaky" if p >= .5 else "unreliable"
        for n, p in zip(df.n, df.precision.fillna(0))
    ]
    return df.sort_values(["attr_group", "precision"], ascending=[True, False])


def reliability(group: str, label: str) -> dict | None:
    """Accuracy record for one label, or None if it hasn't been checked enough."""
    try:
        r = results()
    except Exception:
        return None
    row = r[(r.attr_group == group) & (r.label == label)] if len(r) else r
    if row.empty or int(row.n.iloc[0]) < MIN_CHECKS:
        return None
    return row.iloc[0].to_dict()


# ---------- page ----------

def _labeller() -> None:
    st.html(ui.section("Check the model", "Is Moda right?",
                       "One hand-collected look and the label Moda picked for it. Honest answers matter most - "
                       "‘No’ answers are what make this useful. Keys: the buttons below."))
    group = st.segmented_control("Attribute", list(GROUPS), default="colour", format_func=str.capitalize,
                                 key="eval-group") or "colour"
    key = f"eval-item-{group}"
    if key not in st.session_state or st.session_state[key] is None:
        st.session_state[key] = next_item(group)
    item = st.session_state[key]
    preds = top_predictions(group)
    done = int(preds.judged.sum())
    st.progress(done / max(len(preds), 1), text=f"{done} of {len(preds)} {group} predictions checked")
    if item is None:
        st.success(f"Every {group} prediction has been checked. Pick another attribute above.")
        return

    left, right = st.columns([1, 1.3], vertical_alignment="center")
    with left:
        st.image(str(ROOT / item["local_path"]), use_container_width=True)
    with right:
        st.html(f'<div class="moda-question">{QUESTION[group].format(ui.esc(display(item["label"])))}'
                f'<span>{ui.esc(item["designer"])} · model confidence {item["score"]:.0%}</span></div>')
        a, b, c = st.columns(3)
        answer = None
        if a.button("Yes", type="primary", use_container_width=True, key=f"y-{group}"):
            answer = 1
        if b.button("No", use_container_width=True, key=f"n-{group}"):
            answer = 0
        if c.button("Can't tell", use_container_width=True, key=f"s-{group}"):
            answer = -1
        if answer is not None:
            record(int(item["pageid"]), group, item["label"], float(item["score"]), None if answer == -1 else answer)
            st.session_state[key] = next_item(group)
            st.rerun()
        if st.button("Undo last answer", type="tertiary", key=f"u-{group}"):
            undo_last()
            st.session_state[key] = None
            st.rerun()


def _results() -> None:
    r = results()
    st.html(ui.section("Results", "How often each label is right",
                       f"Precision: when Moda gives a look this label, the share of checked looks where it's correct. "
                       f"Labels need {MIN_CHECKS}+ checks before they're rated. Model: standard CLIP, as used for the "
                       f"Vogue archive and Latest season."))
    if r.empty:
        st.info("No checks yet." + ("" if DEPLOYED else " Answer a few questions above to start."))
        return
    rated = r[r.n >= MIN_CHECKS]
    if len(rated):
        overall = rated.yes.sum() / rated.n.sum()
        st.html(ui.stat_cards([
            (ui.count(overall * 100, 0, "%"), "Overall precision", f"{int(rated.n.sum())} checked predictions"),
            (ui.count((rated.verdict == "reliable").sum()), "Reliable labels", "right at least 75% of the time"),
            (ui.count((rated.verdict == "unreliable").sum()), "Unreliable labels", "right less than half the time"),
        ]))
    st.html(ui.accuracy_table(r, display))


def page() -> None:
    if not DEPLOYED:
        _labeller()
    else:
        st.html(ui.section("Accuracy", "Is Moda right?",
                           "Moda's labels come from a vision model, not people, so we checked them by hand."))
    _results()
