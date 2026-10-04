"""Sort Commons photos into show tiers using their category names.

    major         Paris / Milan / London / New York fashion weeks, haute couture, known houses
    fashion_week  other real, named fashion weeks (Lakmé, São Paulo, Seoul, Vancouver...)
    event         everything else that's runway-ish but not a designer show
    excluded      college, charity, cosplay, retail launches, awards - not trend signal

The first category that matches a tier decides it, checked strictest first, so a
photo tagged both "Paris Fashion Week ..." and "Female models from Romania" is major.
"""

import re

HOUSES = [
    "Chanel", "Dior", "Louis Vuitton", "Gucci", "Prada", "Alexander McQueen", "Givenchy", "Valentino",
    "Balenciaga", "Saint Laurent", "Yves Saint Laurent", "Versace", "Fendi", "Hermès", "Burberry",
    "Armani", "Dolce & Gabbana", "Marc Jacobs", "Oscar de la Renta", "Ralph Lauren", "Michael Kors",
    "Carolina Herrera", "Tom Ford", "Moschino", "Miu Miu", "Loewe", "Jacquemus", "Schiaparelli",
    "Elie Saab", "Zuhair Murad", "Vivienne Westwood", "Jean Paul Gaultier", "Lanvin", "Chloé", "Celine",
    "Rick Owens", "Comme des Garçons", "Yohji Yamamoto", "Issey Miyake", "Tommy Hilfiger", "Calvin Klein",
    "Diane von Furstenberg", "Anna Sui", "Jason Wu", "Christian Siriano", "Vera Wang", "Badgley Mischka",
    "Monique Lhuillier", "Reem Acra", "Marchesa", "Off-White", "Thom Browne", "Simone Rocha", "Erdem",
    "Roksanda", "JW Anderson", "Mugler", "Rabanne", "Kenzo", "Balmain", "Ferragamo", "Missoni", "Etro",
    "Max Mara", "Bottega Veneta", "Iris van Herpen", "Guo Pei", "Ralph & Russo", "Dany Atrache",
    "Georges Chakra", "Basil Soda", "Sybilla", "Khaled el Masri", "Stéphane Rolland", "Viktor & Rolf",
]

MAJOR = [
    r"\b(paris|milan|milano|london|new york) fashion week\b",
    r"\bhaute couture\b",
    r"\bcouture (spring|autumn|fall)",
    r"\bfashion show of .+ (louvre|paris)\b",
] + [rf"\b{re.escape(h)}\b" for h in HOUSES]

FASHION_WEEK = [
    r"\bfashion week\b",
    r"\bfashion festival\b",
    r"\bfashion rio\b",
    r"\bmercedes-benz fashion\b",
]

EXCLUDED = [
    r"\bcollege\b", r"\buniversity\b", r"\bschool\b", r"\bacademy\b", r"\bstudents?\b",
    r"\bheart truth\b", r"\bred dress\b", r"\bcharity\b", r"\bbenefit\b",
    r"\bcomic", r"\bgeek\b", r"\bcosplay\b", r"\bsuperhel",
    r"& sale\b", r"\blaunch\b", r"\baward", r"\bpageant\b", r"\bmiss\b",
    r"\bgirls ?award\b", r"\bgirls collection\b", r"\bidol\b",
]

# Category tags that describe the photo rather than name the show - never use as a show name.
DESCRIPTIVE = re.compile(
    r"^(female|male|women|men|models?|standing|black|white|\d{4}s |\d{4} (fashion shows|events)|"
    r"catwalks|fashion (shows|events) in|clothing|décolleté|\d{2}st-century|interior of)",
    re.I,
)


def _first(cats: list[str], patterns: list[str]) -> str | None:
    for cat in cats:
        for p in patterns:
            if re.search(p, cat, re.I):
                return cat
    return None


AT_EVENT = re.compile(r"^.+? at (the )?(?P<event>.*(fashion week|fashion show|festival|couture).*)$", re.I)


def _event(cat: str) -> str:
    """'Kangana Ranaut at Lakme Fashion Week' -> 'Lakme Fashion Week': a person's category is part of the show."""
    m = AT_EVENT.match(cat)
    return m.group("event") if m else cat


def classify(categories: str, title: str = "") -> tuple[str, str]:
    """Return (tier, show_name) for a look's '|'-joined categories."""
    cats = [_event(c) for c in (categories or "").split("|") if c]
    if show := _first(cats, EXCLUDED):
        return "excluded", show
    if show := _first(cats, MAJOR):
        return "major", show
    if show := _first(cats, FASHION_WEEK):
        return "fashion_week", show
    # Titles often carry the designer when categories don't ("Alexander McQueen Fall Winter 2018 (…).jpg").
    if _first([title], [rf"\b{re.escape(h)}\b" for h in HOUSES]):
        return "major", title.removeprefix("File:").split(" (")[0].rsplit(".", 1)[0]
    named = [c for c in cats if not DESCRIPTIVE.search(c)]
    return "event", named[0] if named else "unknown"


TIERS = {
    "major": "Major designer & couture shows",
    "fashion_week": "+ other fashion weeks",
    "event": "Everything (incl. local events)",
}
TIER_ORDER = ["major", "fashion_week", "event"]  # each option includes the tiers before it
