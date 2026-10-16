"""'Get in touch' page: a sealed envelope that opens into a letter.

Sending uses a mailto: link - the visitor's own mail app opens with the note
pre-filled, so there's no backend or third-party form service to run.
"""

import html
from urllib.parse import quote

import streamlit as st

from . import ui

# Edit these.
NAME = "Rania"
EMAIL = "r22faisa@uwaterloo.ca"
LINKEDIN = "https://www.linkedin.com/in/rania-faisal-500b5032b/"
GITHUB = "https://github.com/Raniafsl"

ICONS = {
    "mail": '<path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h15A1.5 1.5 0 0 1 21 6.5v11a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5z"/><path d="m3.5 6 8.5 7 8.5-7"/>',
    "linkedin": '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 10.5V17M8 7.5v.01M12 17v-3.5a2.5 2.5 0 0 1 5 0V17M12 10.5V17"/>',
    "github": '<path d="M9 19c-4 1.3-4-2-6-2.5m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1-.3-3.4 1.3a11.6 11.6 0 0 0-6 0C6.8 2.3 5.8 2.6 5.8 2.6a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4.4 9c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2v3.5"/>',
}

def _icon_css() -> str:
    """st.html sanitises away inline <svg>, so each icon is a CSS mask filled with the brand colour."""
    rules = []
    for name, paths in ICONS.items():
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" '
               f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')
        uri = f"url(\"data:image/svg+xml,{quote(svg)}\")"
        rules.append(f".moda-link .i-{name} {{ -webkit-mask: {uri} center / contain no-repeat; mask: {uri} center / contain no-repeat; }}")
    return "\n".join(rules)


CSS = f"""
<style>
{_icon_css()}
.moda-contact {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(300px, 1fr); gap: 3rem; align-items: center; margin-top: 1rem; }}
@media (max-width: 860px) {{ .moda-contact {{ grid-template-columns: 1fr; gap: 2rem; }} }}

/* ---------- envelope ---------- */
.env-stage {{ position: relative; min-height: 420px; display: grid; place-items: center; perspective: 1400px; }}
.env {{ position: relative; width: min(100%, 460px); aspect-ratio: 1.55; cursor: pointer; transition: transform .7s var(--ease), opacity .6s var(--ease); }}
.env:hover {{ transform: translateY(-6px) rotateX(6deg); }}
.env:focus-visible {{ outline: 2px solid var(--primary); outline-offset: 8px; border-radius: 12px; }}
.env-back {{ position: absolute; inset: 0; background: #E9DFD2; border-radius: 10px; box-shadow: var(--shadow-lift); }}
.env-letter {{ position: absolute; left: 7%; right: 7%; top: 8%; height: 84%; background: #FFFDF8; border-radius: 6px;
  box-shadow: 0 2px 8px rgba(77,0,0,.12); padding: 1.1rem 1.3rem; z-index: 1;
  opacity: 0; transition: opacity .25s .35s, transform 1s var(--ease) .55s; }}  /* hidden until the flap lifts */
.env-letter .lines {{ margin-top: .7rem; display: grid; gap: .55rem; }}
.env-letter .lines span {{ display: block; height: 2px; background: #EFE7DC; border-radius: 2px; }}
.env-letter .salute {{ font-family: {ui.DISPLAY_FONT}; font-style: italic; font-size: 1.35rem; color: var(--primary); }}
.env-pocket {{ position: absolute; inset: 0; z-index: 2; border-radius: 10px; overflow: hidden; pointer-events: none;
  background:
    linear-gradient(to top right, #F3EBE0 49.6%, transparent 50%) left bottom / 50.5% 100% no-repeat,
    linear-gradient(to top left, #F3EBE0 49.6%, transparent 50%) right bottom / 50.5% 100% no-repeat,
    linear-gradient(to top, #EFE6DA 0 46%, transparent 46%); }}
.env-flap {{ position: absolute; left: 0; right: 0; top: 0; height: 58%; z-index: 3; transform-origin: top;
  transition: transform .75s var(--ease), z-index 0s .38s; }}
.env-flap::before {{ content: ""; position: absolute; inset: 0; background: #E4D8C8; clip-path: polygon(0 0, 100% 0, 50% 100%);
  filter: drop-shadow(0 3px 3px rgba(77,0,0,.12)); border-radius: 10px 10px 0 0; }}
.env-seal {{ position: absolute; left: 50%; top: 100%; width: 64px; height: 64px; margin: -40px 0 0 -32px; border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #A83232, var(--primary) 55%, #5E0E0E); color: #F6E9E0; display: grid; place-items: center;
  font-family: {ui.DISPLAY_FONT}; font-size: 1.9rem; font-style: italic; box-shadow: 0 4px 10px rgba(77,0,0,.35), inset 0 -3px 6px rgba(0,0,0,.25);
  transition: transform .4s var(--ease), opacity .3s; }}
.env:hover .env-seal {{ transform: scale(1.07) rotate(-6deg); }}
.env-hint {{ position: absolute; bottom: -2.4rem; left: 0; right: 0; text-align: center; font-size: .72rem; letter-spacing: .2em;
  text-transform: uppercase; color: var(--accent); transition: opacity .3s; }}

.env.open .env-flap {{ transform: rotateX(180deg); z-index: 0; }}
.env.open .env-seal, .env.open .env-hint {{ opacity: 0; }}
.env.open .env-letter {{ opacity: 1; transform: translateY(-48%); }}
.env.open:hover {{ transform: none; }}
.env-stage.reading .env {{ transform: translateY(40px) scale(.92); opacity: 0; pointer-events: none; }}

/* ---------- the letter form ---------- */
.letter {{ position: absolute; inset: 0; margin: auto; width: min(100%, 520px); height: fit-content; background: #FFFDF8;
  border-radius: 14px; padding: 1.7rem 1.8rem 1.5rem; box-shadow: var(--shadow-lift); border: 1px solid var(--line);
  opacity: 0; transform: translateY(30px) scale(.97); pointer-events: none; transition: opacity .6s var(--ease), transform .7s var(--ease); }}
.env-stage.reading .letter {{ opacity: 1; transform: none; pointer-events: auto; position: relative; inset: auto; }}
.env-stage.reading .env {{ position: absolute; }}  /* letter now sets the height, so a long note pushes the page down */
.letter .salute {{ font-family: {ui.DISPLAY_FONT}; font-style: italic; font-size: 1.8rem; color: var(--primary); margin-bottom: .6rem; }}
.letter label {{ display: block; font-size: .68rem; letter-spacing: .16em; text-transform: uppercase; color: var(--accent); font-weight: 600; margin: .8rem 0 .25rem; }}
.letter input, .letter textarea {{ width: 100%; box-sizing: border-box; border: 0; border-bottom: 1px solid #DCCFC2; background: transparent;
  font: 400 .98rem/1.5 {ui.BODY_FONT}; color: var(--text); padding: .35rem 0; outline: none; transition: border-color .25s; resize: vertical; }}
.letter textarea {{ min-height: 120px;
  background-image: repeating-linear-gradient(transparent 0 29px, #EFE7DC 29px 30px); line-height: 30px; }}
.letter input:focus, .letter textarea:focus {{ border-color: var(--primary); }}
.letter ::placeholder {{ color: #B9A9A3; }}
.letter .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
.letter .actions {{ display: flex; justify-content: space-between; align-items: center; margin-top: 1.3rem; gap: 1rem; }}
.letter .sign {{ font-family: {ui.DISPLAY_FONT}; font-style: italic; color: var(--accent); }}
.moda-btn {{ border: 0; border-radius: 999px; padding: .7rem 1.4rem; background: var(--primary); color: #FFF7F2; font: 600 .85rem {ui.BODY_FONT};
  letter-spacing: .06em; white-space: nowrap; cursor: pointer; transition: transform .25s var(--ease), box-shadow .25s, background .25s; box-shadow: 0 6px 16px -8px rgba(132,25,25,.7); }}
.moda-btn:hover {{ transform: translateY(-2px); background: #9A2222; box-shadow: 0 10px 22px -10px rgba(132,25,25,.8); }}
.letter .sent {{ display: none; text-align: center; padding: 2rem 0 1rem; }}
.letter.done form {{ display: none; }}
.letter.done .sent {{ display: block; animation: moda-rise .6s var(--ease) both; }}
.letter .sent b {{ font-family: {ui.DISPLAY_FONT}; font-size: 1.8rem; color: var(--primary); font-weight: 500; display: block; }}
.letter .sent p {{ color: var(--accent); }}
.letter .again {{ background: none; border: 0; color: var(--primary); text-decoration: underline; cursor: pointer; font: inherit; }}

/* ---------- links ---------- */
.moda-links {{ display: grid; gap: .8rem; perspective: 900px; }}
.moda-link {{ display: flex; align-items: center; gap: 1rem; padding: 1rem 1.15rem; border-radius: 16px; background: var(--surface);
  border: 1px solid var(--line); box-shadow: var(--shadow); text-decoration: none !important; color: var(--text) !important; }}
.moda-link .ic i {{ width: 22px; height: 22px; background: var(--primary); display: block; }}
.moda-link .ic {{ width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; background: rgba(132,25,25,.07); transition: background .3s; }}
.moda-link:hover .ic {{ background: rgba(132,25,25,.14); }}
.moda-link .t {{ font-size: .68rem; letter-spacing: .16em; text-transform: uppercase; color: var(--accent); font-weight: 600; }}
.moda-link .v {{ font-size: .95rem; overflow-wrap: anywhere; }}
.moda-link > span:nth-child(2) {{ min-width: 0; }}
.moda-link .go {{ margin-left: auto; color: var(--accent); transition: transform .3s var(--ease); }}
.moda-link:hover .go {{ transform: translateX(4px); }}

@media (prefers-reduced-motion: reduce) {{
  .env, .env-flap, .env-letter, .letter, .env-seal {{ transition: none !important; }}
}}
</style>
"""

JS = """
<script>
(() => {
  if (window.__modaContact) return; window.__modaContact = true;
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const open = env => {
    if (env.classList.contains('open')) return;
    env.classList.add('open');
    setTimeout(() => {
      const stage = env.closest('.env-stage'); stage.classList.add('reading');
      stage.querySelector('input')?.focus({preventScroll: true});
    }, still ? 0 : 1500);
  };
  document.addEventListener('click', e => {
    const env = e.target.closest('.env'); if (env) open(env);
    if (e.target.closest('.again')) {
      const letter = e.target.closest('.letter'); letter.classList.remove('done'); letter.querySelector('form').reset();
    }
  });
  document.addEventListener('keydown', e => {
    const env = e.target.closest?.('.env'); if (env && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); open(env); }
  });
  document.addEventListener('submit', e => {
    const form = e.target.closest('.letter form'); if (!form) return;
    e.preventDefault();
    const f = new FormData(form), name = f.get('name').trim(), from = f.get('email').trim();
    const subject = f.get('subject').trim() || `Hello from ${name || 'a Moda visitor'}`;
    const body = `${f.get('message').trim()}\\n\\n— ${name}${from ? ` (${from})` : ''}`;
    window.location.href = `mailto:${form.dataset.to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    form.closest('.letter').classList.add('done');
  });
})();
</script>
"""


def _link(icon: str, title: str, value: str, href: str, i: int) -> str:
    external = "" if href.startswith("mailto:") else ' target="_blank" rel="noopener"'
    return (
        f'<a class="moda-link moda-tilt moda-in" style="--i:{i + 3}" data-max="7" href="{html.escape(href)}"{external}>'
        f'<span class="ic"><i class="i-{icon}" aria-hidden="true"></i></span>'
        f'<span><div class="t">{title}</div><div class="v">{html.escape(value)}</div></span><span class="go">→</span></a>'
    )


def page():
    st.html(ui.section("Correspondence", "Get in touch",
                       "Collaborations, co-op roles, or a trend Moda is missing: break the seal and write a note."))
    handle = lambda url: url.rstrip("/").split("/")[-1]
    letter_lines = "".join("<span></span>" for _ in range(5))
    st.html(CSS + JS + f"""
    <div class="moda-contact">
      <div class="env-stage">
        <div class="env moda-in" style="--i:1" role="button" tabindex="0" aria-label="Open the envelope to write a message">
          <div class="env-back"></div>
          <div class="env-letter"><div class="salute">Dear {html.escape(NAME)},</div><div class="lines">{letter_lines}</div></div>
          <div class="env-pocket"></div>
          <div class="env-flap"><div class="env-seal">M</div></div>
          <div class="env-hint">Break the seal</div>
        </div>
        <div class="letter">
          <form data-to="{html.escape(EMAIL)}">
            <div class="salute">Dear {html.escape(NAME)},</div>
            <div class="row">
              <div><label for="m-name">Name</label><input id="m-name" name="name" required autocomplete="name"></div>
              <div><label for="m-email">Email</label><input id="m-email" name="email" type="email" autocomplete="email"></div>
            </div>
            <label for="m-subject">Subject</label><input id="m-subject" name="subject" placeholder="Optional">
            <label for="m-msg">Message</label><textarea id="m-msg" name="message" required></textarea>
            <div class="actions"><span class="sign">Opens in a mail app</span><button class="moda-btn" type="submit">Seal &amp; send</button></div>
          </form>
          <div class="sent"><b>The letter's ready to go.</b><p>A mail app has opened with it filled in. Press send there to post it.</p>
            <button class="again" type="button">Write another</button></div>
        </div>
      </div>
      <div class="moda-links">
        {_link("mail", "Email", EMAIL, f"mailto:{EMAIL}", 0)}
        {_link("linkedin", "LinkedIn", f"{NAME} Faisal", LINKEDIN, 1)}
        {_link("github", "GitHub", handle(GITHUB), GITHUB, 2)}
      </div>
    </div>
    """, unsafe_allow_javascript=True)
