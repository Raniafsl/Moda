"""Vogue Runway archive: trends from precomputed CLIP embeddings, no images.

Uses two files from the Internet Archive item "VogueRunway_dataset" (scraped from
vogue.com, no license given - analysis only, never redistribute):

    data/vogue/VogueRunway.parquet      one row per photo: designer, season, year, city, section, url...
    data/vogue/VogueRunway_image.npy    CLIP ViT-B/32 image embedding per photo, same row order

We never download the photos; the gallery hotlinks Vogue's own image URLs with credit. Each look's embedding is scored against the same
text prompts as the Commons pipeline (vocab.py), but with the matching *OpenAI CLIP*
text encoder - FashionCLIP's text space doesn't line up with these image embeddings.

Scores are averaged per show, so every show gets one vote in the yearly trend
(a 90-look show and a 20-look show count the same).

    python -m runway.vogue build      # ~10-20 min; writes data/vogue/show_shares.parquet + top_looks.parquet
    python -m runway.vogue check      # sanity-check that embeddings line up with the metadata
"""

import argparse
import re
import unicodedata

import numpy as np
import pandas as pd
import torch
from transformers import CLIPModel, CLIPProcessor

from .db import DATA_DIR
from .vocab import GROUPS

VOGUE_DIR = DATA_DIR / "vogue"
META = VOGUE_DIR / "VogueRunway.parquet"
EMB = VOGUE_DIR / "VogueRunway_image.npy"
SHOW_SHARES = VOGUE_DIR / "show_shares.parquet"
TOP_LOOKS = VOGUE_DIR / "top_looks.parquet"
MODEL_ID = "openai/clip-vit-base-patch32"  # the model clip-retrieval used for the image embeddings
CHUNK = 50_000
TOP_PER_LABEL_YEAR = 12


def show_year(season: str, year: int, category: str) -> int:
    """Year the show actually happened. Spring and Resort ready-to-wear/menswear are shown the
    year before their name; couture is shown in its own year (Spring couture in January)."""
    if "couture" in (category or "").lower():
        return year
    return year - 1 if season in ("Spring", "Resort") else year


def collection_url(designer: str, season: str, year: int, category: str | None) -> str:
    """Best-effort link to the collection page on vogue.com (where the photos live)."""
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()).strip("-")
    show = slug(f"{season} {year} {category or 'ready-to-wear'}")
    return f"https://www.vogue.com/fashion-shows/{show}/{slug(designer)}"


def load_meta() -> pd.DataFrame:
    df = pd.read_parquet(META, columns=["key", "designer", "season", "year", "category", "city", "section", "tags", "url"])
    df["row"] = np.arange(len(df))  # embedding row
    df = df[df.section == "Collection"].copy()
    df["category"] = df.category.fillna("Ready-to-Wear")
    df["show_year"] = [show_year(s, y, c) for s, y, c in zip(df.season, df.year, df.category)]
    df["show"] = df.designer + " – " + df.season + " " + df.year.astype(str) + " " + df.category
    return df


def text_features(model, processor, device) -> dict[str, tuple[list[str], np.ndarray]]:
    out = {}
    with torch.no_grad():
        for group, (template, labels) in GROUPS.items():
            inputs = processor(text=[template.format(l) for l in labels], return_tensors="pt", padding=True).to(device)
            t = model.get_text_features(**inputs).pooler_output
            out[group] = (labels, (t / t.norm(dim=-1, keepdim=True)).float().cpu().numpy())
    return out


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max(axis=1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=1, keepdims=True)


def build() -> None:
    meta = load_meta()
    emb = np.load(EMB, mmap_mode="r")
    assert len(emb) == len(pd.read_parquet(META, columns=["key"])), "embeddings and metadata have different lengths"
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = CLIPModel.from_pretrained(MODEL_ID).to(device).eval()
    texts = text_features(model, CLIPProcessor.from_pretrained(MODEL_ID), device)
    scale = float(model.logit_scale.exp())
    print(f"Scoring {len(meta):,} runway looks from {meta['show'].nunique():,} shows...", flush=True)

    show_parts, top_parts = [], []
    for start in range(0, len(meta), CHUNK):
        part = meta.iloc[start:start + CHUNK]
        vecs = np.asarray(emb[part.row.to_numpy()], dtype=np.float32)
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        for group, (labels, t) in texts.items():
            probs = softmax(scale * vecs @ t.T)
            scores = pd.DataFrame(probs, columns=labels, index=part.index)
            scores["show"] = part["show"].values
            # Sum + count per show, so chunks that split a show still combine correctly.
            agg = scores.groupby("show")[labels].agg(["sum", "count"])
            show_parts.append((group, agg))
            # Keep each chunk's best looks per label/year for the gallery.
            long = scores[labels].assign(show_year=part.show_year.values, row=part.row.values).melt(
                ["show_year", "row"], var_name="label", value_name="score")
            top = long.sort_values("score", ascending=False).groupby(["label", "show_year"]).head(TOP_PER_LABEL_YEAR)
            top_parts.append(top.assign(attr_group=group))
        print(f"  {min(start + CHUNK, len(meta)):,}/{len(meta):,}", flush=True)

    # ---- per-show shares ----
    shows = meta.groupby("show").agg(designer=("designer", "first"), season=("season", "first"),
                                     year=("year", "first"), category=("category", "first"),
                                     city=("city", "first"), show_year=("show_year", "first"))
    rows = []
    for group in GROUPS:
        aggs = [a for g, a in show_parts if g == group]
        total = pd.concat(aggs).groupby(level=0).sum()
        labels = GROUPS[group][1]
        n = total[(labels[0], "count")]
        for label in labels:
            rows.append(pd.DataFrame({"show": total.index, "attr_group": group, "label": label,
                                      "share": total[(label, "sum")] / n, "n_looks": n}).reset_index(drop=True))
    out = pd.concat(rows).merge(shows, left_on="show", right_index=True)
    out.to_parquet(SHOW_SHARES, index=False)

    # ---- gallery candidates ----
    top = pd.concat(top_parts).sort_values("score", ascending=False)
    top = top.groupby(["attr_group", "label", "show_year"]).head(TOP_PER_LABEL_YEAR)
    top = top.merge(meta[["row", "designer", "season", "year", "category", "show", "url"]], on="row")
    top = top.rename(columns={"url": "image_url"})  # Vogue's own image URL - hotlinked by the gallery, never downloaded
    top["page_url"] = [collection_url(d, s, y, c) for d, s, y, c in zip(top.designer, top.season, top.year, top.category)]
    top.to_parquet(TOP_LOOKS, index=False)
    print(f"Wrote {SHOW_SHARES.name} ({out['show'].nunique():,} shows) and {TOP_LOOKS.name}.")


def check(n: int = 3000) -> None:
    """Embeddings and metadata must be in the same row order. Vogue's own tags give a check:
    looks tagged 'Evening Dress' should score far higher on 'evening gown' than other looks."""
    df = pd.read_parquet(META, columns=["section", "tags"])
    emb = np.load(EMB, mmap_mode="r")
    print("rows:", len(df), "embeddings:", emb.shape, emb.dtype)
    rng = np.random.default_rng(0)
    idx = np.sort(rng.choice(np.flatnonzero(df.section.to_numpy() == "Collection"), n, replace=False))
    tagged = np.array(["Evening Dress" in list(t if t is not None else []) for t in df.tags.iloc[idx]])
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = CLIPModel.from_pretrained(MODEL_ID).to(device).eval()
    labels, t = text_features(model, CLIPProcessor.from_pretrained(MODEL_ID), device)["garment"]
    v = np.asarray(emb[idx], dtype=np.float32)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    gown = softmax(float(model.logit_scale.exp()) * v @ t.T)[:, labels.index("an evening gown")]
    print(f"'evening gown' score: tagged Evening Dress {gown[tagged].mean():.2f} (n={tagged.sum()}) "
          f"vs others {gown[~tagged].mean():.2f}  -> {'aligned ✓' if gown[tagged].mean() > 2 * gown[~tagged].mean() else 'MISALIGNED ✗'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "check"])
    args = ap.parse_args()
    build() if args.cmd == "build" else check()


if __name__ == "__main__":
    main()
