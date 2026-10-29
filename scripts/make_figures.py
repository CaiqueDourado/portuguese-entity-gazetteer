"""Entities per class (docs/img/classes.png and classes.pt-BR.png) from data/stats.json.
Run: python scripts/make_figures.py"""

from __future__ import annotations

import json
from pathlib import Path

from common import BG, BLUE, CLASS_EN, GRID, INK, MUTED, num, plt

ROOT = Path(__file__).resolve().parents[1]
T = {"": ("Entities per class", "{n} entities in 26 classes; one class per entity, from its first type", "Source: portuguese-entity-gazetteer"),
     ".pt-BR": ("Entidades por classe", "{n} entidades em 26 classes; uma classe por entidade, pelo primeiro tipo", "Fonte: portuguese-entity-gazetteer")}


def main() -> None:
    st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))
    items = sorted(st["por_classe"].items(), key=lambda kv: kv[1])
    out = ROOT / "docs" / "img"
    out.mkdir(parents=True, exist_ok=True)
    for suf, (title, sub, src) in T.items():
        pt = bool(suf)
        fig, ax = plt.subplots(figsize=(10, 8.6), dpi=110)
        fig.patch.set_facecolor(BG)
        ax.set_facecolor(BG)
        labels = [k if pt else CLASS_EN[k] for k, _ in items]
        vals = [v for _, v in items]
        ax.barh(labels, vals, color=BLUE, height=0.68)
        for i, v in enumerate(vals):
            ax.text(v + max(vals) * 0.008, i, num(v, pt), va="center", fontsize=8.5, color=MUTED)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=INK, labelsize=9.5, length=0)
        ax.xaxis.set_visible(False)
        ax.set_xlim(0, max(vals) * 1.12)
        fig.text(0.02, 0.965, title, fontsize=16, weight="bold", color=INK)
        fig.text(0.02, 0.937, sub.format(n=num(st["entidades_final"], pt)), fontsize=10, color=MUTED)
        fig.text(0.02, 0.012, src, fontsize=8, color=MUTED)
        fig.subplots_adjust(left=0.24, right=0.97, top=0.91, bottom=0.04)
        fig.savefig(out / f"classes{suf}.png", facecolor=BG)
        plt.close(fig)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
