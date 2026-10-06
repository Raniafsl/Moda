"""Moda's visual layer: palette, global CSS/JS, and HTML building blocks.

Streamlit widgets handle the controls; the editorial pieces (hero, stat cards,
movers, gallery) are plain HTML so they can animate and tilt on hover.
"""

import base64
import html
from functools import lru_cache
from pathlib import Path

# Palette - keep in sync with .streamlit/config.toml.
TEXT, BACKGROUND, PRIMARY, SECONDARY, ACCENT = "#4D0000", "#F2F3ED", "#841919", "#8E7C7C", "#9C5959"
SURFACE, GRID = "#FAFAF6", "#DEDAD0"
RISING = "#5C6B3A"  # olive, so rising/fading isn't red vs red
# Trend lines: the palette's reds first, then muted earth tones so neighbouring lines stay distinguishable.
PALETTE = [PRIMARY, "#C08A3E", "#5C6B3A", "#4F6470", ACCENT, "#6E3B5C", SECONDARY, TEXT]

DISPLAY_FONT = "'Cormorant Garamond', Georgia, serif"
BODY_FONT = "Inter, system-ui, sans-serif"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=Inter:wght@400;500;600&display=swap');

:root {{
  --text: {TEXT}; --bg: {BACKGROUND}; --primary: {PRIMARY}; --secondary: {SECONDARY};
  --accent: {ACCENT}; --surface: {SURFACE}; --rising: {RISING}; --line: #E3DFD6;
  --shadow: 0 1px 2px rgba(77,0,0,.04), 0 8px 24px -12px rgba(77,0,0,.18);
  --shadow-lift: 0 2px 4px rgba(77,0,0,.05), 0 22px 40px -18px rgba(77,0,0,.32);
  --ease: cubic-bezier(.2,.7,.2,1);
}}

html, body {{ font-family: {BODY_FONT}; }}  /* widgets get Inter via theme.font; never override icon fonts */
.block-container {{ padding-top: 2.5rem; max-width: 1180px; }}
[data-testid="stSidebar"] {{ background: var(--surface); border-right: 1px solid var(--line); }}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{ font-size: .78rem; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); }}
[data-testid="stHeader"] {{ background: rgba(242,243,237,.82); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); }}

/* ---------- motion primitives ---------- */
@keyframes moda-rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes moda-rule {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
@keyframes moda-grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
.moda-in {{ opacity: 0; animation: moda-rise .7s var(--ease) forwards; animation-delay: calc(var(--i, 0) * 70ms); }}

/* ---------- hero ---------- */
.moda-hero {{ padding: .5rem 0 1.75rem; }}
.moda-eyebrow {{ font-size: .72rem; font-weight: 600; letter-spacing: .22em; text-transform: uppercase; color: var(--accent); }}
.moda-wordmark {{ font-family: {DISPLAY_FONT}; font-weight: 500; font-size: clamp(4rem, 11vw, 7.5rem);
  line-height: .9; color: var(--text); margin: .35rem 0 .2rem; letter-spacing: -.02em; }}
.moda-wordmark em {{ color: var(--primary); }}
.moda-tagline {{ font-family: {DISPLAY_FONT}; font-style: italic; font-size: 1.45rem; color: var(--accent); max-width: 34rem; }}
.moda-rule {{ height: 1px; background: linear-gradient(90deg, var(--primary), transparent); margin-top: 1.6rem;
  transform-origin: left; animation: moda-rule 1.2s var(--ease) .25s both; }}

/* ---------- section headings ---------- */
.moda-section {{ margin: 2.6rem 0 1rem; }}
.moda-section h2 {{ font-family: {DISPLAY_FONT}; font-weight: 500; font-size: 2.1rem; color: var(--text); margin: .15rem 0 0; padding: 0; }}
.moda-section p {{ color: var(--accent); margin: .25rem 0 0; font-size: .92rem; }}

/* ---------- tilt cards ---------- */
.moda-tilt {{ transform-style: preserve-3d; transition: transform .45s var(--ease), box-shadow .45s var(--ease); will-change: transform; position: relative; }}
.moda-tilt:hover {{ box-shadow: var(--shadow-lift); }}
.moda-tilt::after {{ content: ""; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
  background: radial-gradient(circle at var(--mx, 50%) var(--my, 50%), rgba(255,255,255,.55), transparent 55%);
  opacity: 0; transition: opacity .4s; mix-blend-mode: soft-light; }}
.moda-tilt:hover::after {{ opacity: 1; }}

.moda-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; perspective: 900px; }}
.moda-stat {{ background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 1.3rem 1.4rem 1.2rem; box-shadow: var(--shadow); }}
.moda-stat .num {{ font-family: {DISPLAY_FONT}; font-size: 3.1rem; line-height: 1; color: var(--primary); font-variant-numeric: lining-nums tabular-nums; transform: translateZ(30px); }}
.moda-stat .num small {{ font-size: 1.5rem; color: var(--accent); margin-left: .1rem; }}
.moda-stat .lbl {{ font-size: .74rem; letter-spacing: .14em; text-transform: uppercase; color: var(--accent); margin-top: .55rem; font-weight: 600; }}
.moda-stat .sub {{ font-size: .82rem; color: var(--secondary); margin-top: .2rem; }}

/* ---------- movers ---------- */
.moda-movers {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.4rem; perspective: 1000px; }}
.moda-col h3 {{ font-family: {DISPLAY_FONT}; font-size: 1.5rem; font-weight: 500; margin: 0 0 .6rem; color: var(--text); }}
.moda-col h3 span {{ font-family: {BODY_FONT}; font-size: .7rem; letter-spacing: .16em; text-transform: uppercase; vertical-align: middle; margin-left: .4rem; }}
.moda-mover {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: .85rem 1rem .9rem; margin-bottom: .65rem; box-shadow: var(--shadow); }}
.moda-mover .top {{ display: flex; justify-content: space-between; align-items: baseline; gap: .5rem; }}
.moda-mover .name {{ font-weight: 600; color: var(--text); }}
.moda-chip {{ font-size: .78rem; font-weight: 600; padding: .15rem .55rem; border-radius: 999px; font-variant-numeric: tabular-nums; }}
.moda-chip.up {{ color: var(--rising); background: rgba(92,107,58,.1); }}
.moda-chip.down {{ color: var(--primary); background: rgba(132,25,25,.08); }}
.moda-bars {{ margin-top: .6rem; display: grid; gap: .3rem; }}
.moda-bar {{ display: grid; grid-template-columns: 4.2rem 1fr 3rem; align-items: center; gap: .5rem; font-size: .74rem; color: var(--accent); }}
.moda-bar .track {{ height: 6px; background: #EEEBE3; border-radius: 99px; overflow: hidden; }}
.moda-bar .fill {{ height: 100%; border-radius: 99px; transform-origin: left; animation: moda-grow 1.1s var(--ease) both; animation-delay: calc(var(--i, 0) * 90ms + .2s); }}
.moda-bar .fill.then {{ background: var(--secondary); opacity: .55; }}
.moda-bar .fill.now.up {{ background: var(--rising); }}
.moda-bar .fill.now.down {{ background: var(--primary); }}
.moda-mnote {{ font-size: .72rem; color: var(--secondary); margin-top: .45rem; }}
.moda-bar .v {{ text-align: right; font-variant-numeric: tabular-nums; color: var(--text); }}

.moda-houses {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: .9rem; perspective: 1000px; }}
.moda-houses .moda-mover {{ margin-bottom: 0; }}

/* ---------- comebacks ---------- */
@keyframes moda-bar {{ from {{ transform: scaleY(0); }} to {{ transform: scaleY(1); }} }}
.moda-comebacks {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; perspective: 1000px; }}
.moda-comeback {{ background: var(--surface); border: 1px solid var(--line); border-radius: 14px; padding: .85rem 1rem .8rem; box-shadow: var(--shadow); }}
.moda-comeback .top {{ display: flex; justify-content: space-between; align-items: baseline; gap: .5rem; }}
.moda-comeback .name {{ font-weight: 600; color: var(--text); }}
.moda-comeback .spark {{ display: flex; align-items: flex-end; gap: 2px; height: 64px; margin: .75rem 0 .5rem; }}
.moda-comeback .spark span {{ flex: 1; background: #E4DDD3; border-radius: 2px 2px 0 0; transform-origin: bottom;
  animation: moda-bar .7s var(--ease) both; animation-delay: calc(var(--i, 0) * 80ms + var(--j) * 18ms); }}
.moda-comeback .pk {{ background: var(--secondary) !important; }}
.moda-comeback .tr {{ background: var(--accent) !important; }}
.moda-comeback .rc {{ background: var(--rising) !important; }}
.moda-comeback .legend {{ display: flex; gap: .8rem; font-size: .72rem; color: var(--accent); flex-wrap: wrap; }}
.moda-comeback .legend i {{ display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: .3rem; vertical-align: middle; }}

/* ---------- gallery ---------- */
.moda-gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 1.1rem; perspective: 1100px; }}
.moda-look {{ border-radius: 16px; overflow: hidden; background: var(--surface); box-shadow: var(--shadow); aspect-ratio: 3 / 4; }}
.moda-look img {{ width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .8s var(--ease); }}
.moda-look:hover img {{ transform: scale(1.05); }}
.moda-look .cap {{ position: absolute; left: 0; right: 0; bottom: 0; padding: 2.2rem .85rem .75rem; color: #fff; font-size: .75rem; line-height: 1.35;
  background: linear-gradient(transparent, rgba(40,0,0,.78)); transform: translateY(42%); transition: transform .45s var(--ease); }}
.moda-look:hover .cap {{ transform: none; }}
.moda-look .cap b {{ font-family: {DISPLAY_FONT}; font-size: 1.15rem; font-weight: 600; display: block; }}
.moda-look .cap a {{ color: #fff; text-decoration: underline; text-underline-offset: 2px; }}

.moda-private {{ background: linear-gradient(160deg, #5E0E0E, var(--primary) 55%, var(--accent)); display: grid; place-items: center; }}
.moda-private .who {{ text-align: center; color: #F6E9E0; padding: 1rem 1rem 3rem; }}
.moda-private .who span {{ font-family: {DISPLAY_FONT}; font-size: 1.7rem; line-height: 1.1; display: block; }}
.moda-private .who em {{ font-size: .78rem; letter-spacing: .12em; text-transform: uppercase; opacity: .85; font-style: normal; }}
.moda-private .cap {{ transform: none; }}
.moda-broken img {{ display: none; }}
.moda-note {{ margin-top: 1rem; padding: .8rem 1rem; border-left: 2px solid var(--accent); background: rgba(156,89,89,.06);
  border-radius: 0 10px 10px 0; font-size: .85rem; color: var(--accent); }}

.moda-chart {{ background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 1rem 1.2rem .4rem; box-shadow: var(--shadow); }}
[data-testid="stVegaLiteChart"] {{ animation: moda-rise .8s var(--ease) both; }}

.moda-foot {{ color: var(--secondary); font-size: .8rem; margin-top: .4rem; }}

@media (prefers-reduced-motion: reduce) {{
  .moda-in, .moda-rule, .moda-bar .fill, .moda-comeback .spark span, [data-testid="stVegaLiteChart"] {{ animation: none !important; opacity: 1 !important; transform: none !important; }}
  .moda-tilt, .moda-look img, .moda-look .cap {{ transition: none !important; }}
}}
</style>
"""

# Cursor-following tilt + count-up numbers. Re-scans the page on every Streamlit
# rerun (MutationObserver), and binds each element only once.
JS = """
<script>
(() => {
  if (window.__moda) return; window.__moda = true;
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;

  function tilt(el) {
    if (el.dataset.tilt || still) return; el.dataset.tilt = 1;
    const max = parseFloat(el.dataset.max || 8);
    el.addEventListener('pointermove', e => {
      const r = el.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      el.style.transform = `rotateX(${(.5 - y) * max}deg) rotateY(${(x - .5) * max}deg) translateY(-4px)`;
      el.style.setProperty('--mx', `${x * 100}%`); el.style.setProperty('--my', `${y * 100}%`);
    });
    el.addEventListener('pointerleave', () => { el.style.transform = ''; });
  }

  const io = new IntersectionObserver(entries => entries.forEach(({isIntersecting, target}) => {
    if (!isIntersecting) return; io.unobserve(target);
    const to = parseFloat(target.dataset.to), dec = +(target.dataset.dec || 0), suf = target.dataset.suffix || '';
    const fmt = v => v.toLocaleString(undefined, {minimumFractionDigits: dec, maximumFractionDigits: dec}) + suf;
    if (still) { target.textContent = fmt(to); return; }
    const t0 = performance.now(), dur = 1400;
    const step = now => { const p = Math.min((now - t0) / dur, 1), e = 1 - Math.pow(1 - p, 4);
      target.textContent = fmt(to * e); if (p < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }), {threshold: .4});

  function count(el) { if (el.dataset.counted) return; el.dataset.counted = 1; io.observe(el); }

  const scan = () => {
    document.querySelectorAll('.moda-tilt').forEach(tilt);
    document.querySelectorAll('.moda-count').forEach(count);
  };
  // A hotlinked photo that 404s falls back to a plain designer card instead of a blank box.
  document.addEventListener('error', e => {
    const card = e.target.tagName === 'IMG' && e.target.closest('.moda-look');
    if (card) card.classList.add('moda-private', 'moda-broken');
  }, true);
  new MutationObserver(scan).observe(document.body, {childList: true, subtree: true});
  scan();
})();
</script>
"""

esc = html.escape


def hero(years: str) -> str:
    return f"""
    <div class="moda-hero">
      <div class="moda-eyebrow moda-in" style="--i:0">Runway intelligence · {esc(years)}</div>
      <div class="moda-wordmark moda-in" style="--i:1">Mo<em>d</em>a</div>
      <div class="moda-tagline moda-in" style="--i:2">What's rising and fading on the runway, read from two decades of openly licensed show photography.</div>
      <div class="moda-rule"></div>
    </div>"""


def section(eyebrow: str, title: str, note: str = "") -> str:
    return f"""
    <div class="moda-section moda-in">
      <div class="moda-eyebrow">{esc(eyebrow)}</div>
      <h2>{esc(title)}</h2>
      {f'<p>{esc(note)}</p>' if note else ''}
    </div>"""


def count(value: float, decimals: int = 0, suffix: str = "") -> str:
    shown = f"{value:,.{decimals}f}{suffix}"  # final value doubles as the no-JS fallback
    return f'<span class="moda-count" data-to="{value}" data-dec="{decimals}" data-suffix="{esc(suffix)}">{shown}</span>'


def stat_cards(stats: list[tuple[str, str, str]]) -> str:
    """stats: (number_html, label, sub-line)"""
    cards = "".join(
        f'<div class="moda-stat moda-tilt moda-in" style="--i:{i + 3}" data-max="10">'
        f'<div class="num">{num}</div><div class="lbl">{esc(lbl)}</div><div class="sub">{esc(sub)}</div></div>'
        for i, (num, lbl, sub) in enumerate(stats)
    )
    return f'<div class="moda-stats">{cards}</div>'


def _mover(name: str, then: float, now: float, lift: float, up: bool, scale: float, i: int,
           labels: tuple[str, str] = ("Before", "Recently"), note: str = "") -> str:
    cls = "up" if up else "down"
    arrow = "▲" if up else "▼"
    w_then, w_now = then / scale * 100, now / scale * 100
    return f"""
    <div class="moda-mover moda-tilt moda-in" style="--i:{i}" data-max="6">
      <div class="top"><span class="name">{esc(name)}</span>
        <span class="moda-chip {cls}">{arrow} ×{count(lift, 2)}</span></div>
      <div class="moda-bars">
        <div class="moda-bar"><span>{labels[0]}</span><div class="track"><div class="fill then" style="width:{w_then:.1f}%;--i:{i}"></div></div><span class="v">{then:.1%}</span></div>
        <div class="moda-bar"><span>{labels[1]}</span><div class="track"><div class="fill now {cls}" style="width:{w_now:.1f}%;--i:{i}"></div></div><span class="v">{now:.1%}</span></div>
      </div>{f'<div class="moda-mnote">{esc(note)}</div>' if note else ''}
    </div>"""


def movers(rising: list, fading: list, display) -> str:
    """rising/fading: rows with .label .baseline .recent .lift"""
    def col(title, tag, items, up):
        # Each column gets its own scale so one huge mover doesn't flatten the rest.
        scale = max([max(r.baseline, r.recent) for r in items] + [1e-9])
        cards = "".join(_mover(display(r.label), r.baseline, r.recent, r.lift, up, scale, i) for i, r in enumerate(items))
        return f'<div class="moda-col"><h3>{title}<span class="moda-chip {"up" if up else "down"}">{tag}</span></h3>{cards}</div>'

    return f'<div class="moda-movers">{col("Rising", "gaining", rising, True)}{col("Fading", "cooling", fading, False)}</div>'


def comebacks(rows, share, display, recent_years: int) -> str:
    """Cards for labels that peaked, faded and returned, each with a mini bar history.
    Bars are plain divs - st.html strips inline SVG."""
    cards = []
    for i, r in enumerate(rows):
        series = share[r.label]
        top = series.max() or 1
        recent = set(series.index[-recent_years:])
        bars = "".join(
            f'<span class="{"pk" if y == r.peak_year else "tr" if y == r.trough_year else "rc" if y in recent else ""}" '
            f'style="height:{max(v / top * 100, 4):.0f}%;--j:{j}" title="{y}: {v:.1%}"></span>'
            for j, (y, v) in enumerate(series.items())
        )
        cards.append(f"""
        <div class="moda-comeback moda-tilt moda-in" style="--i:{i}" data-max="6">
          <div class="top"><span class="name">{esc(display(r.label))}</span>
            <span class="moda-chip up">↺ ×{count(r.recovery, 2)}</span></div>
          <div class="spark">{bars}</div>
          <div class="legend"><span><i class="pk"></i>peak {r.peak_year}</span><span><i class="tr"></i>low {r.trough_year}</span>
            <span><i class="rc"></i>now {r.recent:.1%}</span></div>
        </div>""")
    return f'<div class="moda-comebacks">{"".join(cards)}</div>'


def house_cards(houses, season_short: str, kind: str) -> str:
    """Latest season: one card per house, its new show against its own recent average."""
    rows = houses[houses.seasons > 0]
    scale = max([max(r.base, r.now) for r in rows.itertuples()] + [1e-9])
    cards = "".join(
        _mover(r.designer, r.base, r.now, r.lift, r.lift >= 1, scale, i, labels=("Own avg", season_short),
               note=f"avg of {r.seasons} {kind} seasons, {r.first}–{str(r.last)[-2:]}" + (" · old baseline" if r.last < 2020 else ""))
        for i, r in enumerate(rows.itertuples())
    )
    return f'<div class="moda-houses">{cards}</div>'


@lru_cache(maxsize=512)
def _data_uri(path: str) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def coverage_note(personal: int) -> str:
    extra = f" Includes {personal:,} looks from your personal archive (analysed, never displayed)." if personal else ""
    return (f'<div class="moda-note moda-in" style="--i:6">A sample, not the whole runway: professional show photography '
            f'is licensed, so this draws on openly licensed photos, which cover major houses unevenly.{esc(extra)}</div>')


def note(text: str, i: int = 6) -> str:
    return f'<div class="moda-note moda-in" style="--i:{i}">{esc(text)}</div>'


def vogue_note() -> str:
    return ('<div class="moda-note moda-in" style="--i:6">Built from a scraped Vogue Runway dataset: Moda scores its CLIP '
            'embeddings and metadata, and every show counts as one vote. Photos load directly from Vogue Runway and '
            'belong to Vogue and its photographers; each links to its collection.</div>')


def _private_card(l, label: str, i: int) -> str:
    """Personal-archive looks are never shown - just who/when and a link to the original."""
    vogue = "vogue.com" in (l.page_url or "")
    link = (f'<a href="{esc(l.page_url)}" target="_blank" rel="noopener">{"View on Vogue Runway" if vogue else "View collection"} ↗</a>'
            if l.page_url else "Personal archive")
    return (
        f'<figure class="moda-look moda-private moda-tilt moda-in" style="--i:{i};margin:0" data-max="9">'
        f'<div class="who"><span>{esc(l.designer or "")}</span><em>{esc(l.season or "")}</em></div>'
        f'<figcaption class="cap"><b>{l.year}</b>{l.score:.0%} {esc(label)}<br>{link}{"" if vogue else " · not displayed"}</figcaption></figure>'
    )


def _remote_card(l, label: str, i: int) -> str:
    """Vogue looks: hotlinked from Vogue's servers, credited, linked to the collection page."""
    return (
        f'<figure class="moda-look moda-tilt moda-in" style="--i:{i};margin:0" data-max="9">'
        f'<img src="{esc(l.image_url)}" alt="{esc(l.designer)} {esc(l.season)}" loading="lazy" referrerpolicy="no-referrer">'
        f'<figcaption class="cap"><b>{esc(l.designer)}</b>{esc(l.season)} · {l.score:.0%} {esc(label)}<br>'
        f'Photo: <a href="{esc(l.page_url)}" target="_blank" rel="noopener">Vogue Runway ↗</a></figcaption></figure>'
    )


def latest_gallery(looks, root: Path, label: str) -> str:
    """Your saved looks - shown from the local copies in data/personal (never committed to git).
    If a file is missing (e.g. on a deployment without your data), the card falls back to a link."""
    cards = []
    for i, l in enumerate(looks.itertuples()):
        path = root / l.local_path
        link = f'<a href="{esc(l.page_url)}" target="_blank" rel="noopener">Collection ↗</a>' if l.page_url else ""
        if l.artist:
            link = f"Photo: {esc(l.artist)}" + (f" · {link}" if link else "")
        if not path.exists():
            cards.append(_private_card(l, label, i))
            continue
        cards.append(
            f'<figure class="moda-look moda-tilt moda-in" style="--i:{min(i, 12)};margin:0" data-max="9">'
            f'<img src="{_data_uri(str(path))}" alt="{esc(l.designer)} {esc(l.season)}" loading="lazy">'
            f'<figcaption class="cap"><b>{esc(l.designer)}</b>{l.score:.0%} {esc(label)}<br>{link}</figcaption></figure>'
        )
    return f'<div class="moda-gallery">{"".join(cards)}</div>'


def _image_src(l, root: Path) -> str:
    """Local thumbnail if we have it, else Wikimedia's own copy (deployments don't ship the 470 MB of thumbnails)."""
    path = root / l.local_path if l.local_path else None
    return _data_uri(str(path)) if path and path.exists() else esc(getattr(l, "thumb_url", "") or "")


def gallery(looks, root: Path, label: str) -> str:
    cards = []
    for i, l in enumerate(looks.itertuples()):
        if l.private:
            cards.append(_private_card(l, label, i))
            continue
        if getattr(l, "image_url", None):
            cards.append(_remote_card(l, label, i))
            continue
        credit = esc(l.artist or "Unknown")
        cards.append(
            f'<figure class="moda-look moda-tilt moda-in" style="--i:{i};margin:0" data-max="9">'
            f'<img src="{_image_src(l, root)}" alt="{esc(label)} look, {l.year}" loading="lazy">'
            f'<figcaption class="cap"><b>{l.year}</b>{l.score:.0%} {esc(label)}<br>'
            f'<a href="{esc(l.page_url)}" target="_blank" rel="noopener">{credit}</a> · {esc(l.license or "")}</figcaption></figure>'
        )
    return f'<div class="moda-gallery">{"".join(cards)}</div>'
