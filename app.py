"""Moda - runway trend dashboard.

    streamlit run app.py
"""

import altair as alt
import pandas as pd
import streamlit as st

from runway import about, accuracy, contact, latest, trends, ui
from runway.sources import TIERS
from runway.db import ROOT
from runway.vocab import GROUPS, display

st.set_page_config(page_title="Moda", page_icon="🧵", layout="wide")
st.html(ui.CSS + ui.JS, unsafe_allow_javascript=True)

# Real swatches for the colour group so the chart reads at a glance.
SWATCH = {
    "black": "#2B2522", "white": "#CFC6B8", "cream and beige": "#D8C3A0", "grey": "#9A948E",
    "red": "#B8322A", "pink": "#E59AAE", "orange": "#E07A33", "yellow": "#E3B92E",
    "green": "#5E8B5A", "blue": "#3E78B8", "navy": "#26375E", "purple": "#7D5A9C",
    "brown": "#7A5236", "metallic silver or gold": "#B89B4A", "multicoloured": "#C77DB0",
}
# Palette bars can show "multicoloured" as what it is.
PALETTE_SWATCH = {**SWATCH, "multicoloured": "linear-gradient(90deg,#B8322A,#E3B92E,#5E8B5A,#3E78B8,#7D5A9C)"}


@st.cache_data(ttl=300)  # data keeps arriving while ingest/tag run
def cached_scores(min_runway: float, tier: str) -> pd.DataFrame:
    return trends.load_scores(min_runway, trends.tiers_upto(tier))


def trend_chart(share: pd.DataFrame, chosen: list[str], group: str, height: int = 400) -> alt.Chart:
    long = share[chosen].reset_index().melt("year", var_name="label", value_name="share")
    long["name"] = long.label.map(display)
    names = [display(l) for l in chosen]
    colours = [SWATCH.get(l, "#888") for l in chosen] if group == "colour" else ui.PALETTE[: len(chosen)]
    colour = alt.Color("name:N", title=None, scale=alt.Scale(domain=names, range=colours), legend=alt.Legend(orient="top"))

    # Hovering near a line highlights it and fades the rest.
    hover = alt.selection_point(fields=["name"], on="pointerover", nearest=True, clear="pointerout")
    base = alt.Chart(long).encode(
        x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("share:Q", title=None, axis=alt.Axis(format="%", tickCount=5)),
        color=colour,
    )
    lines = base.mark_line(interpolate="monotone").encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0.15)),
        strokeWidth=alt.condition(hover, alt.value(3), alt.value(2)),
    )
    points = base.mark_circle(size=70).encode(
        opacity=alt.condition(hover, alt.value(1), alt.value(0.1)),
        tooltip=[alt.Tooltip("name:N", title=group), alt.Tooltip("year:O"), alt.Tooltip("share:Q", format=".1%")],
    ).add_params(hover)
    return (
        (lines + points)
        .properties(height=height)
        .configure(background="transparent", font="Inter")
        .configure_view(strokeWidth=0)
        .configure_legend(labelColor=ui.TEXT, labelFontSize=12, symbolStrokeWidth=3)
        .configure_axis(gridColor=ui.GRID, domainColor=ui.SECONDARY, tickColor=ui.SECONDARY,
                        labelColor=ui.ACCENT, labelFontSize=12, gridDash=[2, 4])
        .configure_axisX(grid=False)
    )


VOGUE, COMMONS = "Vogue Runway archive", "Open photos (Commons)"
COLLECTIONS = ["Ready-to-Wear", "Couture", "Menswear"]


@st.cache_data(ttl=3600, show_spinner="Opening the Vogue Runway archive…")
def cached_vogue(group: str, categories: tuple[str, ...]) -> pd.DataFrame:
    return trends.load_vogue(group, list(categories))


def trends_page():
    has_vogue = trends.vogue_available()
    with st.sidebar:
        source = st.radio("Source", [VOGUE, COMMONS] if has_vogue else [COMMONS],
                          help="Vogue: ~25k designer shows 1988–2024, scored from CLIP embeddings (photos never shown). "
                               "Commons: openly licensed photos incl. 2025–26, scored with FashionCLIP.")
        if source == VOGUE:
            categories = st.multiselect("Collections", COLLECTIONS, default=["Ready-to-Wear", "Couture"])
        else:
            tier = st.radio("Shows", list(TIERS), index=1, format_func=TIERS.get,
                            help="Major = Paris/Milan/London/NY fashion weeks, haute couture and known houses. "
                                 "College, charity and cosplay shows are always left out.")
        group = st.radio("Attribute", list(GROUPS), format_func=str.capitalize)
        if source == COMMONS:
            min_runway = st.slider("Runway-photo confidence", 0.3, 0.9, 0.5, 0.05,
                                   help="Drops front-row, backstage and venue shots the model doesn't think are runway looks.")
            min_n = st.slider("Min looks per year", 10, 100, 25, 5,
                              help="Years with fewer runway looks than this are left off the chart.")
        else:
            min_n = st.slider("Min shows per year", 10, 300, 100, 10,
                              help="Early years have only a handful of shows on Vogue Runway; they're left off below this.")
        recent = st.slider("“Recent” window (years)", 2, 5, 3)
        if st.button("Reload data", use_container_width=True):
            st.cache_data.clear()

    # ---------- per-source data ----------
    if source == VOGUE:
        if not categories:
            st.info("Pick at least one collection type.")
            return
        shows = cached_vogue(group, tuple(categories))
        share = trends.vogue_yearly_share(shows, min_n)
        span = f"{share.index.min()}–{share.index.max()}" if len(share) else "1988–2024"
        v = trends.vogue_summary(shows[shows.show_year.isin(share.index)])
        cards = [(ui.count(v["looks"]), "Runway looks", "scored by CLIP"),
                 (ui.count(v["shows"]), "Shows", f"{v['designers']:,} designers"),
                 (ui.count(len(share)), "Years with enough data", span)]
        note = ui.vogue_note()
        unit = "shows"
        get_looks = lambda label, year: trends.vogue_top_looks(group, label, year, categories, n=8)
        evidence = "The looks the model is most confident about, one per show. Photos via Vogue Runway."
    else:
        tiers = trends.tiers_upto(tier)
        scores = cached_scores(min_runway, tier)
        if scores.empty:
            st.html(ui.hero("2007–2026"))
            st.info("No tagged looks yet. Run `python -m runway.ingest` then `python -m runway.tag`.")
            return
        share = trends.yearly_share(scores, group, min_n)
        span = f"{share.index.min()}–{share.index.max()}" if len(share) else "2007–2026"
        stats = trends.summary(min_runway, tiers)
        cards = [(ui.count(stats["looks"]), "Runway looks", "read by FashionCLIP"),
                 (ui.count(stats["shows"]), "Shows", {"major": "major houses & couture", "fashion_week": "major + fashion weeks",
                                                      "event": "all runway events"}[tier]),
                 (ui.count(len(share)), "Years with enough data", span)]
        note = ui.coverage_note(stats["personal"])
        unit = "looks"
        get_looks = lambda label, year: trends.top_looks(group, label, year, min_runway, tiers, n=8)
        evidence = "The photos the model is most confident about."

    st.html(ui.hero(span))
    st.html(ui.stat_cards(cards))
    st.html(note)
    moves = trends.movers(share, recent)

    # ---------- chart ----------
    st.html(ui.section(f"{group} · share of {unit}", f"{group.capitalize()} over time", "Hover a line to isolate it."))
    labels = list(share.columns)
    default = (list(moves.label.head(3)) + list(moves.label.tail(2))) if len(moves) else labels[:5]
    chosen = st.multiselect("Show", labels, default=default, format_func=display, label_visibility="collapsed")
    if chosen and len(share):
        st.altair_chart(trend_chart(share, chosen, group), use_container_width=True)

    # ---------- movers ----------
    if len(moves):
        st.html(ui.section("The shift", "What's moving",
                           f"Last {recent} years against everything before, among years with ≥{min_n} {unit}."))
        rising = moves[moves.lift > 1].head(4)
        fading = moves[moves.lift < 1].tail(4).iloc[::-1]
        st.html(ui.movers(list(rising.itertuples()), list(fading.itertuples()), display))

    # ---------- comebacks ----------
    back = trends.comebacks(share, recent)
    if len(back):
        st.html(ui.section("Second act", "Comebacks",
                           "Peaked, faded, and climbing again: recent share against its low point (3-year smoothing)."))
        smoothed = share.rolling(3, center=True, min_periods=1).mean()  # same smoothing the detector uses
        st.html(ui.comebacks(list(back.head(4).itertuples()), smoothed, display, recent))

    # ---------- gallery ----------
    st.html(ui.section("The evidence", "See the looks", evidence))
    g1, g2 = st.columns([2, 1])
    pick = g1.selectbox("Label", labels, index=labels.index(default[0]) if default else 0, format_func=display)
    year = g2.selectbox("Year", ["All years"] + [int(y) for y in share.index[::-1]])
    looks = get_looks(pick, None if year == "All years" else year)
    st.html(ui.gallery(looks, ROOT, display(pick)))

    with st.expander("How this works & caveats"):
        st.markdown(
            """
- **Data:** openly licensed photos from Wikimedia Commons, sorted into show tiers by their category names
  (`runway/sources.py`). Professional runway photography is owned by agencies, so major shows are thinly
  covered and some years are missing - read this as a *sample* of the runway, not the whole of it.
- **Vogue Runway archive:** a scraped dataset from the Internet Archive (no license given), scored from
  its metadata and precomputed CLIP image embeddings. Gallery photos load directly from Vogue's servers (never
  stored here), are credited, and link to their collection. Scores are averaged per show, so every show is one vote.
- **Hand-collected looks:** recent shows collected by hand count toward the charts
  but are never displayed; the gallery links out to the original collection instead.
- **Tagging:** [FashionCLIP](https://huggingface.co/patrickjohncyh/fashion-clip) scores each photo against text
  prompts (zero-shot, no training). Labels within an attribute compete, so shares in a year sum to 100%.
- **Share** = average model probability across a year's looks; **lift** = recent share ÷ earlier share.
- Edit `runway/vocab.py` to add labels, then `python -m runway.tag --retag`.
            """
        )


@st.cache_data(ttl=300, show_spinner="Comparing the latest season with history…")
def cached_compare(group: str, label: str) -> dict | None:
    return latest.compare(group, label)


def season_chart(r: dict, height: int = 320) -> alt.Chart:
    kind, year = r["kind"], r["year"]
    hist = r["series"].assign(season=lambda d: kind + " " + d.year.astype(str),
                              which=lambda d: d.origin.map({"vogue": "history", "saved": "saved"}))
    now = pd.DataFrame({"year": [year], "share": [r["latest"]], "houses": [r["n_shows"]],
                        "season": [f"{kind} {year}"], "which": ["latest"]})
    # Empty slots for seasons with no data, so the gap before the latest season is visible.
    gap = pd.DataFrame({"year": r["missing_years"], "share": None, "houses": None,
                        "season": [f"{kind} {y}" for y in r["missing_years"]], "which": "history"})
    df = pd.concat([hist, gap, now], ignore_index=True)
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("season:N", sort=list(df.season), title=None, axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("share:Q", title=None, axis=alt.Axis(format="%", tickCount=5)),
            color=alt.Color("which:N", scale=alt.Scale(domain=["history", "saved", "latest"],
                                                       range=["#DCD3C8", "#C99A92", ui.PRIMARY]), legend=None),
            tooltip=[alt.Tooltip("season:N"), alt.Tooltip("share:Q", format=".1%"), alt.Tooltip("houses:Q", title="houses")],
        )
        .properties(height=height)
        .configure(background="transparent", font="Inter")
        .configure_view(strokeWidth=0)
        .configure_axis(gridColor=ui.GRID, domainColor=ui.SECONDARY, tickColor=ui.SECONDARY,
                        labelColor=ui.ACCENT, labelFontSize=11, gridDash=[2, 4])
        .configure_axisX(grid=False)
    )


def latest_page():
    if not trends.vogue_available():
        st.info("The Latest season page compares hand-collected shows with the Vogue Runway archive - build it first "
                "(`python -m runway.vogue build`).")
        return
    a, b = st.columns([3, 2], vertical_alignment="bottom")
    with a:
        group = st.segmented_control("Attribute", list(GROUPS), default="pattern", format_func=str.capitalize) or "pattern"
    labels = GROUPS[group][1]
    probe = cached_compare(group, labels[0])
    if probe is None:
        st.html(ui.section("Latest season", "Nothing saved yet"))
        st.info("Save a show's looks into a folder, then run `python -m runway.personal import-show <folder> "
                "--designer \"Miu Miu\" --season \"Spring 2027 Ready-to-Wear\"` and `python -m runway.tag`.")
        return

    top = probe["standouts"]
    default = "a floral print" if "a floral print" in labels else (top.label.iloc[0] if len(top) else labels[0])
    with b:
        pick = st.selectbox("Label", labels, index=labels.index(default), format_func=display, key=f"label-{group}")
    r = cached_compare(group, pick)
    kind, year = r["kind"], r["year"]
    short = f"{ {'Spring': 'SS', 'Fall': 'FW'}.get(kind, kind + ' ') }{str(year)[-2:]}"
    name = display(pick)

    st.html(ui.section(f"Latest season · {r['n_shows']} shows", f"{r['season']} vs. history",
                       f"A hand-collected sample of the season's shows, scored with standard CLIP like the Vogue archive, against the same "
                       f"houses' own past {kind} seasons."))
    ratio = r["latest"] / r["last_share"] if r["last_share"] else None
    st.html(ui.stat_cards([
        (ui.count(r["latest"] * 100, 1, "%"), f"{name} in {short}", f"mean of {r['n_shows']} shows, one vote each"),
        (("×" + ui.count(ratio, 2)) if ratio else "–", f"vs {kind} {r['last_year']}", "same houses, last season on record"),
        (f"{ui.count(r['n_up'])}<small>/{r['n_hist']}</small>", "Houses up ≥20%", f"{r['n_down']} down, against their own average"),
    ] + ([(("×" + ui.count(p["lift"], 2)), f"vs {p['season']}", f"same {len(p['houses'])} houses, hand-collected")]
         if (p := r.get("prev")) else [])))
    bits = []
    if r["highest_since"]:
        bits.append(f"Highest {kind} level of {name} for these houses since {kind} {r['highest_since']}.")
    elif r["last_year"]:
        bits.append(f"Higher than any {kind} season on record for these houses.")
    partial = r.get("partial", {})
    if m := [y for y in r["missing_years"] if y not in partial]:
        bits.append(f"No data for {kind} {m[0]}{'–' + str(m[-1]) if len(m) > 1 else ''}: the Vogue archive ends there.")
    for y, n in partial.items():
        bits.append(f"{kind} {y} covers only {n} of these {r['n_shows']} houses so far, too few to chart.")
    if p := r.get("prev"):
        above_archive = r["latest"] > (r["last_share"] or 0) * 1.2
        change = ("a new move this season" if p["lift"] >= 1.5
                  else "down since last season" if p["lift"] < 0.8
                  else "a rise that began before this season" if above_archive
                  else "little change since last season")
        bits.append(f"Same {len(p['houses'])} houses year on year: {p['prev']:.1%} in {p['season']} → {p['now']:.1%} now "
                    f"(×{p['lift']:.2f}, {p['up']} up, {p['down']} down) - {change}.")
    bits.append(f"Based on a hand-collected sample of {r['n_shows']} shows; more will be added as the season is collected.")
    st.html(ui.note(" ".join(bits)))

    if (acc := accuracy.reliability(group, pick)) and acc["precision"] < 0.75:
        st.html(ui.note(f"Accuracy check: when Moda labels a look ‘{name}’, it was right {acc['precision']:.0%} of the "
                        f"time ({int(acc['yes'])} of {int(acc['n'])} checked). Treat this label's numbers with caution."))

    saved_note = (f" Rose bars ({', '.join(f'{kind} {y}' for y in r['saved_years'])}) are hand-collected seasons; "
                  "grey bars come from the Vogue archive." if r.get("saved_years") else "")
    st.html(ui.section(f"Same houses, every {kind}", f"{name} across {kind} seasons",
                       "Each bar averages the houses that showed that season (at least half of them)." + saved_note))
    st.altair_chart(season_chart(r), use_container_width=True)

    st.html(ui.section("House by house", "Against their own history",
                       f"Each new show vs the average of that house's last five {kind} seasons on record."))
    st.html(ui.house_cards(r["houses"], short, kind))

    # ---------- colour story (always shown, whatever attribute is picked) ----------
    c = cached_compare("colour", "black")
    yrs = c["recent_years"]
    span = f"{kind} {yrs[0]}–{str(yrs[-1])[-2:]}" if len(yrs) else f"Earlier {kind}"
    st.html(ui.section("Colour story", f"The {short} palette",
                       f"Each bar is a palette: colour shares across the season's looks. Top: the same houses' "
                       f"{kind} average for {span}. Below, house by house. Hover a band for its share."))
    st.html(ui.colour_story(c["base_all"], c["now_all"], c["per_house"], PALETTE_SWATCH, display,
                            f"{span} avg", f"{short} · {c['n_shows']} shows"))
    if group != "colour":  # with Colour picked, "What stands out" below already lists these
        cs = c["standouts"].rename(columns={"now": "recent", "base": "baseline"})
        st.html(ui.movers(list(cs[cs.lift > 1].head(4).itertuples()), list(cs[cs.lift < 1].tail(4).iloc[::-1].itertuples()), display))

    st.html(ui.section("The looks", f"{short} on the runway", f"The season's looks, ranked by how {name} the model finds them."))
    houses = sorted(r["houses"].designer)
    view = st.selectbox("Show", [f"Most {name}"] + houses, label_visibility="collapsed")
    looks = latest.latest_looks(group, pick, None if view.startswith("Most ") else view)
    st.html(ui.latest_gallery(looks, ROOT, name))
    if not view.startswith("Most "):
        st.caption(f"All {len(looks)} looks from {view}, most {name} first.")

    s = r["standouts"].rename(columns={"now": "recent", "base": "baseline"})
    st.html(ui.section("What stands out", f"{group.capitalize()} in {short}",
                       f"Every label, this season vs the same houses' last five {kind} seasons."))
    st.html(ui.movers(list(s[s.lift > 1].head(4).itertuples()), list(s[s.lift < 1].tail(4).iloc[::-1].itertuples()), display))


FEATURED_COMEBACK = ("garment", "a corset top")


def findings_page():
    st.html(ui.hero("1999–2027"))
    archive = trends.vogue_summary(cached_vogue("colour", ("Ready-to-Wear", "Couture")))
    sample = cached_compare("colour", "black")
    st.html(ui.stat_cards([
        (ui.count(archive["shows"]), "Designer shows", f"{archive['designers']:,} houses in the Vogue Runway archive"),
        (ui.count(archive["looks"]), "Runway looks", "each one scored by a vision model"),
    ] + ([(ui.count(sample["n_shows"]), f"{sample['kind']} {sample['year']} shows", "hand-collected for the latest season")]
         if sample else [])))
    st.html(ui.section("Findings", "What the runway is saying",
                       "Headlines computed from the data - each one opens into the full view."))

    # ---- 1. florals in the latest season ----
    fl = cached_compare("pattern", "a floral print")
    # ---- 2. the latest season's standout colour ----
    col0 = cached_compare("colour", "black")
    rising = col0["standouts"][col0["standouts"].lift > 1] if col0 else None
    top_col = rising.label.iloc[0] if rising is not None and len(rising) else None
    col = cached_compare("colour", top_col) if top_col else None

    base = fl or col0
    if not base:
        st.info("Findings appear once a recent season has been collected.")
        return
    short = f"SS{str(base['year'])[-2:]}" if base["kind"] == "Spring" else f"{base['kind']} {base['year']}"

    a, b = st.columns(2, gap="medium")
    if fl:
        ratio = fl["latest"] / fl["last_share"] if fl["last_share"] else None
        h = fl["houses"]
        leaders = h[(h.lift >= 1.2) & (h.base < 0.05)].head(3)
        lead_txt = ", ".join(f"{d} ×{x:.1f}" for d, x in zip(leaders.designer, leaders.lift))
        with a.container(key="finding-florals"):
            verb = "back" if ratio and ratio >= 1.2 else "steady" if ratio and ratio > 0.8 else "fading"
            st.html(ui.finding(f"{short} · patterns", f"Florals are {verb}: ×{ratio:.1f} on {fl['kind']} {fl['last_year']}",
                               (f"Led by houses that rarely do florals: {lead_txt}." if lead_txt else
                                f"{fl['n_up']} of {fl['n_hist']} houses are up on their own history.")
                               + (f" Already up in {pv['season']}: ×{pv['lift']:.2f} since, same {len(pv['houses'])} houses."
                                  if (pv := fl.get("prev")) and pv["lift"] < 1.5 else
                                  f" ×{pv['lift']:.1f} on {pv['season']} alone." if pv else "")
                               + f" {fl['n_shows']} shows, one vote each."))
            st.altair_chart(season_chart(fl, height=200), use_container_width=True)
            st.page_link(PAGES["latest"], label="Explore the latest season →")
    if col:
        name = display(top_col)
        c_ratio = col["latest"] / col["last_share"] if col["last_share"] else None
        with b.container(key="finding-colour"):
            st.html(ui.finding(f"{short} · colour", f"{name.capitalize()} is the season's rising colour",
                               f"{col['latest']:.1%} of looks, ×{c_ratio:.1f} on {col['kind']} {col['last_year']} for the same houses."
                               + (f" It {'doubled' if 1.9 <= pv['lift'] < 2.5 else 'jumped ×' + format(pv['lift'], '.1f')} since "
                                  f"{pv['season']} for the {len(pv['houses'])} houses in both seasons."
                                  if (pv := col.get("prev")) and pv["lift"] >= 1.5 else "")))
            yrs = col0["recent_years"]
            st.html(ui.colour_story(col0["base_all"], col0["now_all"], col0["per_house"].iloc[:0], PALETTE_SWATCH, display,
                                    f"{col0['kind']} {yrs[0]}–{str(yrs[-1])[-2:]}", short))
            st.page_link(PAGES["latest"], label="See the full colour story →")

    c, d = st.columns(2, gap="medium")
    # ---- 3. a comeback from the archive ----
    g, label = FEATURED_COMEBACK
    share = trends.vogue_yearly_share(cached_vogue(g, ("Ready-to-Wear", "Couture")), 100)
    back = trends.comebacks(share, 3)
    if len(back):
        pick_row = back[back.label == label] if label in set(back.label) else back
        row = next(pick_row.head(1).itertuples())
        with c.container(key="finding-comeback"):
            st.html(ui.finding("Archive · comebacks", f"The {display(row.label)} comeback",
                               f"Peaked {row.peak_year}, bottomed out {row.trough_year}, and is back ×{row.recovery:.1f} since."))
            st.html(ui.comebacks([row], share.rolling(3, center=True, min_periods=1).mean(), display, 3))
            st.page_link(PAGES["trends"], label="Find more comebacks →")
    # ---- 4. two decades of silhouette ----
    sil = trends.vogue_yearly_share(cached_vogue("silhouette", ("Ready-to-Wear", "Couture")), 100)
    mv = trends.movers(sil, 3)
    if len(mv):
        up, down = mv.label.iloc[0], mv.label.iloc[-1]
        with d.container(key="finding-silhouette"):
            st.html(ui.finding(f"Archive · {sil.index.min()}–{sil.index.max()}",
                               f"{display(up).capitalize()} in, {display(down)} out",
                               f"Across ~20,000 shows: {display(up)} ×{mv.lift.iloc[0]:.1f} lately, "
                               f"{display(down)} ×{mv.lift.iloc[-1]:.2f}."))
            st.altair_chart(trend_chart(sil, [up, down], "silhouette", height=200), use_container_width=True)
            st.page_link(PAGES["trends"], label="Explore 25 years of trends →")


PAGES = {
    "findings": st.Page(findings_page, title="Findings", icon=":material/auto_awesome:", default=True),
    "trends": st.Page(trends_page, title="Trends", icon=":material/trending_up:", url_path="trends"),
    "latest": st.Page(latest_page, title="Latest season", icon=":material/new_releases:", url_path="latest"),
    "accuracy": st.Page(accuracy.page, title="Accuracy", icon=":material/fact_check:", url_path="accuracy"),
    "about": st.Page(about.about_page, title="About the data", icon=":material/menu_book:", url_path="about"),
    "terms": st.Page(about.legal_page, title="Terms & privacy", icon=":material/gavel:", url_path="terms"),
    "contact": st.Page(contact.page, title="Get in touch", icon=":material/mail:", url_path="contact"),
}
nav = st.navigation({
    "": [PAGES["findings"]],
    "Explore": [PAGES["trends"], PAGES["latest"], PAGES["accuracy"]],
    "Moda": [PAGES["about"], PAGES["terms"], PAGES["contact"]],
})
nav.run()
def data_updated() -> str:
    """Build date stamped by `python -m runway.bundle` (deployed copies only)."""
    import re
    from datetime import date
    marker = ROOT / "data" / "DEPLOYED"
    m = re.search(r"built (\d{4}-\d{2}-\d{2})", marker.read_text()) if marker.exists() else None
    return f"{date.fromisoformat(m.group(1)):%B %-d, %Y}" if m else ""


st.html(ui.footer(contact.EMAIL, contact.GITHUB + "/Moda", data_updated()))
