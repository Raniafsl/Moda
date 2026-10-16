"""'About the data' and 'Terms & privacy' pages."""

import streamlit as st

from . import ui
from .contact import EMAIL, GITHUB, NAME

EFFECTIVE = "October 9, 2026"
OWNER = f"{NAME} Faisal"


def _prose(md: str) -> None:
    with st.container(key="moda-prose"):
        st.markdown(md)


def about_page() -> None:
    st.html(ui.section("About the data", "Where Moda's numbers come from",
                       "Sources, method and limits, so every finding can be judged on its own terms."))
    _prose(f"""
### Sources

| Source | What Moda uses | Credit |
|---|---|---|
| **Vogue Runway archive** (1999–2023) | A scraped dataset published on the Internet Archive (`VogueRunway_dataset`): show metadata and precomputed CLIP image embeddings for ~20,000 shows. Moda never downloads these photos; the gallery loads them from Vogue's servers and links each look to its collection. | Photos © Vogue / Condé Nast and the photographers |
| **Wikimedia Commons** (2007–2026) | Openly licensed photos from fashion-week categories, each shown with its photographer and license. | Individual photographers, under each photo's license |
| **Latest season** (Spring 2027) | Looks saved by hand for research and shown as small credited thumbnails. | Photos via Tagwalk; © the houses and photographers |

Moda is an independent student project. It is **not affiliated with or endorsed by** Vogue, Condé Nast, Tagwalk,
Wikimedia, or any fashion house.

### Method

1. **Zero-shot tagging.** A vision–language model compares each look with text prompts ("a runway outfit with a
   floral print") and gives a probability for every label in a group: colour, garment, pattern, silhouette,
   material. No one hand-labels the looks first.
2. **Two models.** The Vogue archive and the Latest season page use **standard CLIP** (ViT-B/32), the model the
   archive's embeddings were made with. The Commons view uses **FashionCLIP**, tuned on fashion product photos.
   Their percentages aren't on the same scale, so Moda never mixes them in one chart.
3. **One vote per show.** A show's looks are averaged first, so a 90-look show and a 30-look show count the same.
4. **Show years.** Collections are dated by when they were shown: Spring 2027 ready-to-wear walked in autumn 2026.

### Limits

- **Model estimates, not facts.** Labels can be wrong; see **Accuracy** for how often each one is right. Some
  (logo prints, tie-dye, metallics) are known to be over-detected.
- **Samples, not the whole runway.** The Vogue dataset ends with Spring 2024 collections; Commons covers some shows
  far better than others; the Latest season page includes only the shows saved so far.
- **Gaps.** No data for Spring 2024–2026 means Moda can say SS27 differs from 2023, not exactly when a change began.

### Removal requests

Photo owners who want an image removed can email **[{EMAIL}](mailto:{EMAIL})** with the page and look.
It will be taken down promptly, normally within 48 hours.

Code: [{GITHUB.removeprefix('https://')}/Moda]({GITHUB}/Moda)
""")


def legal_page() -> None:
    st.html(ui.section("Terms & privacy", "The short version",
                       "Moda is a free, non-commercial student project. It doesn't collect personal data."))
    _prose(f"""
*Effective {EFFECTIVE}. Moda is run by {OWNER} ("I", "me"), a student at the University of Waterloo.
Questions: [{EMAIL}](mailto:{EMAIL}).*

## Privacy policy

**What Moda collects: nothing.** There are no accounts, no sign-ups, no analytics, and no tracking cookies set by
Moda. Streamlit's own usage statistics are switched off.

**The contact form** doesn't send anything to Moda. "Seal & send" opens the visitor's own email app with a pre-filled
message; nothing is sent until it's sent from there, and it then arrives like any other email. Messages are used only to reply.

**Services a visitor's browser talks to.** Like most websites, Moda loads some things from other companies, which see
standard technical data (such as IP address and browser type) under their own privacy policies:

- **Streamlit Community Cloud** (Snowflake Inc.) hosts the app and keeps standard server and security logs, and
  may use cookies needed to run the app.
- **Google Fonts** serves the typefaces.
- **Vogue (Condé Nast)** and **Wikimedia** serve the runway photos shown in galleries.

**Data rights.** Since Moda holds no personal data about visitors, there's nothing to access or delete. Anyone who has
emailed and wants that correspondence deleted can ask, and it will be.

## Terms of use

1. **What Moda is.** An educational, non-commercial project that estimates runway trends with machine-learning
   models. It's provided **as is**, without warranties of any kind.
2. **Estimates, not advice.** Trend figures are model estimates from incomplete samples (see *About the data*).
   Don't rely on them for business, financial or buying decisions.
3. **Photos and trademarks** belong to their owners: Vogue / Condé Nast, the photographers, Tagwalk, Wikimedia
   Commons contributors, and the fashion houses. They're shown for commentary and research, credited and linked to
   their sources, and may not be copied or reused from Moda.
4. **No affiliation.** Moda isn't affiliated with or endorsed by any company or brand named on the site.
5. **Removal requests.** Rights holders can email [{EMAIL}](mailto:{EMAIL}) to have material removed; I'll act
   promptly.
6. **Code.** Moda's own code is on GitHub; using it doesn't grant rights to any third-party photos or data.
7. **Liability.** To the extent the law allows, I'm not liable for any loss arising from using Moda.
8. **Changes.** These terms may change; the effective date above will be updated. These terms are governed by the
   laws of Ontario, Canada.
""")
