# Moda

**Moda** — what's rising and fading on the runway, measured across ~20k designer shows (Vogue Runway
archive, 1999–2023) and openly licensed show photography (Wikimedia Commons, through 2026) with CLIP-family vision models.

```
Wikimedia Commons ──► ingest.py ──► SQLite + thumbnails
                                        │
                     FashionCLIP ──► tag.py ──► runway filter · colour · garment
                                        │       pattern · silhouette · material
                                        ▼
                               trends.py ──► app.py (Streamlit dashboard)
```

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export RUNWAY_CONTACT="you@example.com"        # Wikimedia asks scrapers for contact info
.venv/bin/python -m runway.ingest --years 2007-2026 --per-year 200   # ~1h, rate-limited
.venv/bin/python -m runway.tag                 # FashionCLIP on Apple GPU / CUDA / CPU
.venv/bin/streamlit run app.py
```

**Vogue Runway archive (optional, main source):** download two files from the Internet Archive item
`VogueRunway_dataset` into `data/vogue/` (`VogueRunway.parquet`, 99 MB, and `img_emb/VogueRunway_image.npy`, 1.3 GB),
then:

```bash
.venv/bin/python -m runway.vogue check    # embeddings line up with metadata?
.venv/bin/python -m runway.vogue build    # ~1 min: per-show shares for ~20k shows, 1999–2023
```

That dataset was scraped from vogue.com and has no license. Moda scores its CLIP embeddings and metadata and never
downloads the photos. The gallery hotlinks Vogue's own image URLs, credited to Vogue Runway, with each look linked to
its collection. That still displays Condé Nast's photos, so a public deployment carries takedown risk; to switch to
link-out cards only, set `private=1` in `trends.vogue_top_looks`. The data files are git-ignored. Don't redistribute them.

Ingest and tag are both resumable, so re-run them any time to pick up new photos.

## How it works

1. **Ingest.** Commons files every runway photo under `"<year> fashion shows"` category
   trees. The `deepcat:` search pulls each year's tree with its license and photographer,
   so every image in the dashboard is credited.
2. **Filter.** Those categories also contain front-row, backstage and venue shots.
   FashionCLIP scores each photo against scene prompts, and only likely runway looks count.
3. **Tag (zero-shot).** Each look is scored against the text prompts in
   [`runway/vocab.py`](runway/vocab.py). No labelled data or training is needed.
   Image embeddings are saved too, for similarity search later.
4. **Trend.** A label's yearly *share* is its mean probability across that year's looks.
   *Lift* compares the last N years with everything before.

## Limitations (worth saying out loud in interviews)

- **Sampling bias.** Commons only covers shows that volunteers photographed and uploaded.
  It skews toward some weeks and designers, and it's thin for 2020–21.
- **Zero-shot labels are noisy.** Text prompts are only a stand-in for real categories.
  Hand-label ~200 looks and report precision per label to measure that.
- **One "year" mixes seasons.** Spring/Summer and Fall/Winter can be split out of category names.

## Next steps

- [ ] Hand-label an evaluation set and report accuracy per attribute
- [ ] Split by season (SS vs FW) and city
- [ ] Cluster embeddings to find *emerging* aesthetics the vocabulary doesn't name yet
- [ ] "Find similar looks" search over the stored embeddings (pgvector or FAISS)
- [ ] Compare runway trends with retail data (Google Trends, resale listings)
