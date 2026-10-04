"""Attribute vocabulary for zero-shot tagging.

Each group is scored independently: the model picks a probability distribution
over the group's labels, so labels within a group compete with each other.
Edit freely - re-run `python -m runway.tag --retag` afterwards.
"""

# Used to drop non-runway shots (front row, backstage, venues). Labels whose
# probabilities are summed into `is_runway` are listed in RUNWAY_LABELS.
SCENE = {
    "runway": "a full-length photo of a fashion model walking on a runway",
    "posed look": "a full-length photo of a fashion model posing in a designer outfit",
    "front row": "a photo of guests sitting in the front row at a fashion show",
    "crowd": "a crowd of people at an event",
    "portrait": "a close-up portrait of a person's face",
    "backstage": "backstage hair and makeup before a show",
    "venue": "an empty venue, building or stage",
    "sign": "a logo, poster or sign",
}
RUNWAY_LABELS = ("runway", "posed look")

GROUPS: dict[str, tuple[str, list[str]]] = {
    "colour": (
        "a runway outfit that is mostly {}",
        ["black", "white", "cream and beige", "grey", "red", "pink", "orange", "yellow",
         "green", "blue", "navy", "purple", "brown", "metallic silver or gold", "multicoloured"],
    ),
    "garment": (
        "a runway model wearing {}",
        ["an evening gown", "a mini dress", "a midi dress", "a tailored suit", "an overcoat",
         "a trench coat", "a leather jacket", "a chunky knit sweater", "a shirt and trousers",
         "a skirt and top", "a jumpsuit", "swimwear", "a corset top", "a cape"],
    ),
    "pattern": (
        "a runway outfit with {}",
        ["no pattern, a solid colour", "stripes", "pinstripes", "plaid or tartan", "gingham check",
         "houndstooth", "argyle", "a floral print", "paisley", "polka dots", "an animal print",
         "camouflage print", "tie-dye", "a geometric print", "a logo monogram",
         "sequins and embellishment", "an abstract print"],
    ),
    "silhouette": (
        "a runway outfit with {}",
        ["an oversized, voluminous silhouette", "a tight, body-con fit", "an A-line shape",
         "flowing, draped fabric", "a sharp, structured, boxy shape", "sheer layers",
         "cropped proportions"],
    ),
    "material": (
        "a runway outfit made of {}",
        ["leather", "denim", "lace", "silk satin", "tulle or chiffon", "chunky wool knit",
         "fur or faux fur", "velvet", "tweed", "sheer mesh", "feathers", "cotton"],
    ),
}

# Short display names for labels that are phrased for the model.
DISPLAY = {
    "an evening gown": "evening gown", "a mini dress": "mini dress", "a midi dress": "midi dress",
    "a tailored suit": "tailored suit", "an overcoat": "overcoat", "a trench coat": "trench coat",
    "a leather jacket": "leather jacket", "a chunky knit sweater": "chunky knit",
    "a shirt and trousers": "shirt & trousers", "a skirt and top": "skirt & top",
    "a jumpsuit": "jumpsuit", "a corset top": "corset", "a cape": "cape",
    "no pattern, a solid colour": "solid", "a floral print": "floral", "an animal print": "animal print",
    "a geometric print": "geometric", "a logo monogram": "logo / monogram",
    "sequins and embellishment": "sequins / embellished", "an abstract print": "abstract print",
    "plaid or tartan": "plaid / tartan", "gingham check": "gingham", "camouflage print": "camo",
    "an oversized, voluminous silhouette": "oversized", "a tight, body-con fit": "body-con",
    "an A-line shape": "A-line", "flowing, draped fabric": "draped",
    "a sharp, structured, boxy shape": "structured", "sheer layers": "sheer layers",
    "cropped proportions": "cropped",
    "tulle or chiffon": "tulle / chiffon", "chunky wool knit": "wool knit",
    "fur or faux fur": "fur / faux fur", "cream and beige": "cream / beige",
    "metallic silver or gold": "metallic",
}


def display(label: str) -> str:
    return DISPLAY.get(label, label)
