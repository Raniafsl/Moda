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

That dataset was scraped from vogue.com and has no license. Moda scores its CLIP embeddings and metadata and never
downloads the photos. The gallery hotlinks Vogue's own image URLs, credited to Vogue Runway, with each look linked to
its collection.

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

## Limitations 

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
