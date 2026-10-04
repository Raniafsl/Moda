"""Zero-shot tag every downloaded look with FashionCLIP.

FashionCLIP is CLIP fine-tuned on ~800k fashion product images, so it knows
"trench coat" from "overcoat" better than vanilla CLIP. For each look we:
  1. score it against SCENE prompts to estimate whether it's a runway shot,
  2. score it against each attribute group (colour, garment, ...),
  3. keep the image embedding for later similarity search / clustering.

    python -m runway.tag            # tag anything not yet tagged
    python -m runway.tag --rescore pattern   # after editing vocab.py: re-score from stored embeddings (seconds)
    python -m runway.tag --retag    # re-run the model on every image (slow; only if embeddings are missing)
"""

import argparse

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from .db import ROOT, connect
from .vocab import GROUPS, RUNWAY_LABELS, SCENE

MODEL_ID = "patrickjohncyh/fashion-clip"


def pick_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "cuda" if torch.cuda.is_available() else "cpu"


class Tagger:
    def __init__(self, model_id: str = MODEL_ID):
        self.device = pick_device()
        self.model = CLIPModel.from_pretrained(model_id).to(self.device).eval()
        self.processor = CLIPProcessor.from_pretrained(model_id)
        # Encode every prompt once up front; images are compared against these.
        self.scene_labels = list(SCENE)
        self.scene_text = self._encode_text(list(SCENE.values()))
        self.group_text = {
            group: (labels, self._encode_text([template.format(l) for l in labels]))
            for group, (template, labels) in GROUPS.items()
        }

    @torch.no_grad()
    def _encode_text(self, prompts: list[str]) -> torch.Tensor:
        inputs = self.processor(text=prompts, return_tensors="pt", padding=True).to(self.device)
        feats = self.model.get_text_features(**inputs).pooler_output  # projected embedding (transformers 5)
        return feats / feats.norm(dim=-1, keepdim=True)

    @torch.no_grad()
    def encode_images(self, images: list[Image.Image]) -> torch.Tensor:
        inputs = self.processor(images=images, return_tensors="pt").to(self.device)
        feats = self.model.get_image_features(**inputs).pooler_output
        return feats / feats.norm(dim=-1, keepdim=True)

    @torch.no_grad()
    def _probs(self, img_feats: torch.Tensor, text_feats: torch.Tensor) -> np.ndarray:
        logits = self.model.logit_scale.exp() * img_feats @ text_feats.T
        return logits.softmax(dim=-1).float().cpu().numpy()

    def score(self, img_feats: torch.Tensor):
        """Return (is_runway probs, {group: (labels, probs)}) for a batch."""
        scene = self._probs(img_feats, self.scene_text)
        runway_idx = [self.scene_labels.index(l) for l in RUNWAY_LABELS]
        is_runway = scene[:, runway_idx].sum(axis=1)
        groups = {g: (labels, self._probs(img_feats, t)) for g, (labels, t) in self.group_text.items()}
        return is_runway, groups


def rescore(conn, groups: list[str]) -> None:
    """Re-score attribute groups from the stored image embeddings. Image embeddings don't depend
    on the vocabulary, so after editing vocab.py only the text side needs recomputing."""
    unknown = set(groups) - set(GROUPS)
    if unknown:
        raise SystemExit(f"unknown group(s): {', '.join(unknown)}; choose from {', '.join(GROUPS)}")
    rows = conn.execute("SELECT pageid, vec FROM embeddings").fetchall()
    tagger = Tagger()
    ids = [pid for pid, _ in rows]
    feats = torch.from_numpy(np.stack([np.frombuffer(v, dtype=np.float32) for _, v in rows])).to(tagger.device)
    for group in groups:
        labels, text = tagger.group_text[group]
        probs = tagger._probs(feats, text)
        conn.execute("DELETE FROM tags WHERE attr_group = ?", (group,))
        conn.executemany("INSERT INTO tags VALUES (?, ?, ?, ?)",
                         [(pid, group, label, float(p)) for i, pid in enumerate(ids) for label, p in zip(labels, probs[i])])
        conn.commit()
        print(f"  {group}: re-scored {len(ids):,} looks against {len(labels)} labels", flush=True)


def load(path) -> Image.Image | None:
    try:
        return Image.open(ROOT / path).convert("RGB")
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--retag", action="store_true", help="re-score looks that already have tags")
    ap.add_argument("--rescore", nargs="*", metavar="GROUP",
                    help="re-score these attribute groups (default: all) from stored embeddings - no images needed")
    ap.add_argument("--batch", type=int, default=32)
    args = ap.parse_args()

    conn = connect()
    if args.rescore is not None:
        rescore(conn, args.rescore or list(GROUPS))
        return
    if args.retag:
        conn.execute("DELETE FROM tags")
        conn.execute("UPDATE looks SET is_runway = NULL")
        conn.commit()
    todo = conn.execute(
        "SELECT pageid, local_path FROM looks WHERE is_runway IS NULL AND local_path IS NOT NULL"
    ).fetchall()
    if not todo:
        print("Nothing to tag.")
        return

    tagger = Tagger()
    print(f"Tagging {len(todo)} looks on {tagger.device}...", flush=True)
    for start in range(0, len(todo), args.batch):
        batch = [(pid, img) for pid, path in todo[start:start + args.batch] if (img := load(path))]
        if not batch:
            continue
        ids = [pid for pid, _ in batch]
        feats = tagger.encode_images([img for _, img in batch])
        is_runway, groups = tagger.score(feats)
        vecs = feats.float().cpu().numpy()

        for i, pid in enumerate(ids):
            conn.execute("UPDATE looks SET is_runway = ? WHERE pageid = ?", (float(is_runway[i]), pid))
            conn.execute("INSERT OR REPLACE INTO embeddings VALUES (?, ?)", (pid, vecs[i].astype(np.float32).tobytes()))
            conn.executemany(
                "INSERT OR REPLACE INTO tags VALUES (?, ?, ?, ?)",
                [(pid, g, label, float(p)) for g, (labels, probs) in groups.items() for label, p in zip(labels, probs[i])],
            )
        conn.commit()
        print(f"  {min(start + args.batch, len(todo))}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main()
