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

/* ---------- colour story ---------- */
.moda-colours {{ background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 1.2rem 1.3rem; box-shadow: var(--shadow); }}
.moda-colours .row {{ display: grid; grid-template-columns: 9.5rem 1fr; align-items: center; gap: .9rem; margin: .35rem 0; }}
.moda-colours .row.big {{ margin: .55rem 0; }}
.moda-colours .who {{ font-size: .8rem; color: var(--accent); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.moda-colours .who b {{ color: var(--primary); font-weight: 600; }}
.moda-colours .houses {{ margin-top: 1rem; padding-top: .8rem; border-top: 1px solid var(--line); }}
.moda-palette {{ display: flex; height: 34px; border-radius: 9px; overflow: hidden; gap: 2px; }}
.moda-palette.thin {{ height: 14px; border-radius: 5px; gap: 1px; }}
.moda-palette span {{ transform-origin: left; animation: moda-grow .9s var(--ease) both; animation-delay: calc(var(--j, 0) * 35ms + .15s);
  transition: filter .2s, transform .2s; }}
.moda-palette span:hover {{ filter: brightness(1.12) saturate(1.1); transform: scaleY(1.12); }}
.moda-legend {{ display: flex; flex-wrap: wrap; gap: .4rem 1rem; margin: .4rem 0 0 10.4rem; font-size: .78rem; color: var(--text); }}
.moda-legend i {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: .35rem; vertical-align: -1px; }}
@media (max-width: 640px) {{
  .moda-colours .row {{ grid-template-columns: 1fr; gap: .25rem; }}
  .moda-legend {{ margin-left: 0; }}
}}

/* ---------- findings ---------- */
.moda-finding h3 {{ font-family: {DISPLAY_FONT}; font-weight: 500; font-size: 1.75rem; line-height: 1.15; color: var(--text); margin: .35rem 0 .3rem; padding: 0; }}
.moda-finding p {{ color: var(--accent); font-size: .9rem; margin: 0; }}
[class*="st-key-finding-"] {{ background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 1.2rem 1.3rem 1rem;
  box-shadow: var(--shadow); transition: transform .45s var(--ease), box-shadow .45s var(--ease); }}
[class*="st-key-finding-"]:hover {{ transform: translateY(-4px); box-shadow: var(--shadow-lift); }}

/* ---------- long text (about / terms) ---------- */
.st-key-moda-prose {{ background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 1.4rem 1.8rem; box-shadow: var(--shadow); max-width: 860px; }}
.st-key-moda-prose h2, .st-key-moda-prose h3 {{ font-family: {DISPLAY_FONT}; font-weight: 500; color: var(--primary); }}
.st-key-moda-prose p, .st-key-moda-prose li, .st-key-moda-prose td {{ font-size: .93rem; line-height: 1.6; }}
.st-key-moda-prose table {{ font-size: .85rem; }}

/* ---------- accuracy ---------- */
.moda-question {{ font-family: {DISPLAY_FONT}; font-size: 1.9rem; line-height: 1.2; color: var(--text); margin-bottom: .6rem; }}
.moda-question b {{ color: var(--primary); font-weight: 600; }}
.moda-question span {{ display: block; font-family: {BODY_FONT}; font-size: .8rem; color: var(--accent); margin-top: .5rem; }}
.moda-acc {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 1rem; }}
.acc-group {{ background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: .9rem 1.1rem; box-shadow: var(--shadow); }}
.acc-group h3 {{ font-family: {DISPLAY_FONT}; font-weight: 500; font-size: 1.35rem; margin: 0 0 .5rem; padding: 0; color: var(--text); }}
.acc-row {{ display: grid; grid-template-columns: 7.5rem 1fr 2.6rem 2.6rem 7.6rem; align-items: center; gap: .5rem; font-size: .78rem; margin: .3rem 0; }}
.acc-row .lbl {{ color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.acc-row .track {{ height: 6px; background: #EEEBE3; border-radius: 99px; overflow: hidden; }}
.acc-row .fill {{ height: 100%; border-radius: 99px; transform-origin: left; animation: moda-grow 1s var(--ease) both; animation-delay: calc(var(--i) * 50ms); }}
.acc-row .fill.up {{ background: var(--rising); }} .acc-row .fill.mid {{ background: #C08A3E; }}
.acc-row .fill.down {{ background: var(--primary); }} .acc-row .fill.na {{ background: var(--secondary); opacity: .5; }}
.acc-row .v {{ text-align: right; font-variant-numeric: tabular-nums; }} .acc-row .n {{ color: var(--secondary); font-variant-numeric: tabular-nums; }}
.acc-row .moda-chip {{ justify-self: start; font-size: .68rem; }}
.moda-chip.mid {{ color: #8A5A16; background: rgba(192,138,62,.14); }}
.moda-chip.na {{ color: var(--secondary); background: rgba(142,124,124,.12); }}

/* ---------- envelope footer ---------- */
.moda-footer {{ margin: 4.5rem 0 1rem; perspective: 1400px; }}
.foot-env {{ position: relative; border-radius: 14px; background: #F3EBE0; box-shadow: var(--shadow-lift); overflow: hidden;
  transition: transform .6s var(--ease); }}
.foot-env:hover {{ transform: rotateX(4deg) translateY(-3px); }}
.foot-flap {{ position: absolute; inset: 0 0 auto 0; height: 78px; background: #E4D8C8; clip-path: polygon(0 0, 100% 0, 50% 100%);
  filter: drop-shadow(0 2px 2px rgba(77,0,0,.10)); transform-origin: top; transition: transform .7s var(--ease); }}
.foot-env:hover .foot-flap {{ transform: rotateX(28deg); }}
.foot-seal {{ position: absolute; left: 50%; top: 78px; width: 52px; height: 52px; margin: -32px 0 0 -26px; border-radius: 50%; z-index: 2;
  background: radial-gradient(circle at 35% 30%, #A83232, var(--primary) 55%, #5E0E0E); color: #F6E9E0 !important; display: grid; place-items: center;
  font-family: {DISPLAY_FONT}; font-style: italic; font-size: 1.55rem; text-decoration: none !important;
  box-shadow: 0 4px 10px rgba(77,0,0,.35), inset 0 -3px 6px rgba(0,0,0,.25); transition: transform .4s var(--ease); }}
.foot-seal:hover {{ transform: scale(1.1) rotate(-8deg); }}
.foot-paper {{ display: grid; grid-template-columns: 1fr auto; gap: 1.5rem; padding: 6.2rem 2rem 1.6rem;
  background: linear-gradient(to top right, #EFE6DA 49.8%, transparent 50%) left bottom / 50.5% 46% no-repeat,
              linear-gradient(to top left, #EFE6DA 49.8%, transparent 50%) right bottom / 50.5% 46% no-repeat; }}
.foot-addr {{ position: relative; z-index: 1; }}
.foot-addr .to {{ font-family: {DISPLAY_FONT}; font-size: 1.15rem; color: var(--accent); margin-bottom: .6rem; }}
.foot-addr .to em {{ color: var(--primary); }}
.foot-addr nav {{ display: flex; flex-wrap: wrap; gap: .3rem 1.4rem; font-family: {DISPLAY_FONT}; font-size: 1.3rem; }}
.foot-addr nav a {{ color: var(--text) !important; text-decoration: none !important; border-bottom: 1px solid transparent; transition: border-color .25s, color .25s; }}
.foot-addr nav a:hover {{ color: var(--primary) !important; border-bottom-color: var(--primary); }}
.foot-addr .fine {{ margin-top: .9rem; font-size: .74rem; color: var(--secondary); max-width: 46rem; line-height: 1.5; }}
.foot-addr .fine a {{ color: var(--accent) !important; }}
.foot-addr .sig {{ margin-top: .5rem; font-family: {DISPLAY_FONT}; font-style: italic; color: var(--accent); }}
.foot-stamp {{ align-self: start; width: 86px; height: 104px; display: grid; place-content: center; text-align: center; transform: rotate(4deg);
  background: var(--primary); color: #F6E9E0; font-family: {DISPLAY_FONT}; position: relative; z-index: 1;
  border: 5px dotted #F3EBE0;  /* paper-coloured dots read as perforations */
  box-shadow: 0 0 0 2px var(--primary), inset 0 0 0 4px var(--primary), inset 0 0 0 5px rgba(246,233,224,.55), 2px 4px 8px rgba(77,0,0,.18); }}
.foot-stamp span {{ font-size: 1.5rem; font-style: italic; }}
.foot-stamp small {{ font-family: {BODY_FONT}; font-size: .6rem; letter-spacing: .2em; opacity: .85; }}
@media (max-width: 640px) {{
  .foot-paper {{ grid-template-columns: 1fr; padding: 7rem 1.2rem 1.3rem; }}
  .foot-stamp {{ position: absolute; right: 1rem; top: 6.6rem; width: 62px; height: 76px; }}
  .foot-stamp span {{ font-size: 1.1rem; }}
  .foot-addr .to {{ padding-right: 4.5rem; }}
}}

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
  .moda-in, .moda-rule, .moda-bar .fill, .moda-comeback .spark span, .moda-palette span, .acc-row .fill, [data-testid="stVegaLiteChart"] {{ animation: none !important; opacity: 1 !important; transform: none !important; }}
  .moda-tilt, .moda-look img, .moda-look .cap, .foot-env, .foot-flap, [class*="st-key-finding-"] {{ transition: none !important; }}
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


def _segments(shares, swatch: dict, display, delay: int = 0) -> str:
    total = float(shares.sum()) or 1.0
    return "".join(
        f'<span style="flex:{v / total:.4f};background:{swatch.get(label, "#bbb")};--j:{delay + j}" '
        f'title="{esc(display(label))} {v / total:.0%}"></span>'
        for j, (label, v) in enumerate(shares.sort_values(ascending=False).items()) if v / total >= 0.005
    )


def colour_story(before, now, per_house, swatch: dict, display, before_label: str, now_label: str) -> str:
    """Palettes as real swatches: the same houses' recent average vs. the new season, then house by house."""
    legend = "".join(
        f'<span><i style="background:{swatch.get(l, "#bbb")}"></i>{esc(display(l))} {v / now.sum():.0%}</span>'
        for l, v in now.sort_values(ascending=False).head(6).items()
    )
    rows = "".join(
        f'<div class="row"><span class="who">{esc(d)}</span><div class="moda-palette thin">{_segments(r, swatch, display, i * 3)}</div></div>'
        for i, (d, r) in enumerate(per_house.iterrows())
    )
    return f"""
    <div class="moda-colours moda-in" style="--i:2">
      <div class="row big"><span class="who">{esc(before_label)}</span><div class="moda-palette">{_segments(before, swatch, display)}</div></div>
      <div class="row big"><span class="who"><b>{esc(now_label)}</b></span><div class="moda-palette">{_segments(now, swatch, display, 4)}</div></div>
      <div class="moda-legend">{legend}</div>
      {f'<div class="houses">{rows}</div>' if rows else ''}
    </div>"""


def accuracy_table(r, display) -> str:
    """Per-label precision, grouped by attribute, as bar rows with a verdict chip."""
    chip = {"reliable": "up", "shaky": "mid", "unreliable": "down", "not enough checks": "na"}
    blocks = []
    for group, g in r.groupby("attr_group", sort=False):
        rows = "".join(
            f'<div class="acc-row"><span class="lbl">{esc(display(x.label))}</span>'
            f'<div class="track"><div class="fill {chip[x.verdict]}" style="width:{(x.precision or 0) * 100:.0f}%;--i:{i}"></div></div>'
            f'<span class="v">{"–" if x.n == 0 else f"{x.precision:.0%}"}</span>'
            f'<span class="n">{int(x.yes)}/{int(x.n)}</span>'
            f'<span class="moda-chip {chip[x.verdict]}">{esc(x.verdict)}</span></div>'
            for i, x in enumerate(g.itertuples())
        )
        blocks.append(f'<div class="acc-group moda-in"><h3>{esc(group.capitalize())}</h3>{rows}</div>')
    return f'<div class="moda-acc">{"".join(blocks)}</div>'


def finding(eyebrow: str, headline: str, sub: str) -> str:
    return (f'<div class="moda-finding"><div class="moda-eyebrow">{esc(eyebrow)}</div>'
            f'<h3>{esc(headline)}</h3><p>{esc(sub)}</p></div>')


def footer(email: str, github: str) -> str:
    """The site footer as the back of an envelope - same paper, flap and wax seal as the contact page."""
    links = [("About the data", "/about"), ("Accuracy", "/accuracy"), ("Terms & privacy", "/terms"),
             ("GitHub", github), ("Get in touch", "/contact")]
    target = lambda h: 'target="_self"' if h.startswith("/") else 'target="_blank" rel="noopener"'
    nav = "".join(f'<a href="{esc(h)}" {target(h)}>{esc(t)}</a>' for t, h in links)
    return f"""
    <footer class="moda-footer">
      <div class="foot-env">
        <div class="foot-flap"></div>
        <a class="foot-seal" href="/contact" target="_self" title="Write to me">M</a>
        <div class="foot-paper">
          <div class="foot-addr">
            <div class="to">To: <em>everyone who reads a runway closely</em></div>
            <nav>{nav}</nav>
            <div class="fine">Photos belong to their owners: Vogue / Condé Nast and photographers, Tagwalk,
              and Wikimedia Commons contributors. Trend figures are model estimates. Not affiliated with any brand.
              Removal requests: <a href="mailto:{esc(email)}">{esc(email)}</a></div>
            <div class="sig">© 2026 Rania Faisal · Moda</div>
          </div>
          <div class="foot-stamp"><span>Moda</span><small>SS27</small></div>
        </div>
      </div>
    </footer>"""


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
