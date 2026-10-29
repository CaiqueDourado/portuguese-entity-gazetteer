"""Cover image (EN and PT) from data/stats.json and docs/example-busca.json. Run: python scripts/make_cover.py"""

from __future__ import annotations

import json
from pathlib import Path

from matplotlib.patches import FancyBboxPatch

from common import AQUA, BG, BLUE, CARD, CLASS_EN, INK, LINE, MONO, MUTED, ORANGE, num, plt

ROOT = Path(__file__).resolve().parents[1]
TYPE_EN = {"Artista": "Artist", "Música": "Music", "Filme": "Film", "Cidade": "City", "Esporte": "Sport",
           "Empresa": "Company", "Jogo": "Game", "Veículo": "Vehicle", "Livro": "Book", "Bairro": "Neighbourhood"}
T = {
    "": dict(title="Portuguese Entity Gazetteer · Dicionário de Entidades",
             sub="{n} entities in Portuguese → {t} types in {c} classes · places, people, works, products, brands",
             p1="One search", p1s="entities found, then the pattern", p2="Entities per class", p2s="one class per entity",
             p3="Most common types", p3s="an entity can have several types", pat="pattern (search-pattern-miner)",
             foot="portuguese-entity-gazetteer · the entity dictionary behind SuperNichos' search patterns"),
    ".pt-BR": dict(title="Dicionário de Entidades do Português",
                   sub="{n} entidades em português → {t} tipos em {c} classes · lugares, pessoas, obras, produtos, marcas",
                   p1="Uma busca", p1s="entidades encontradas e o padrão", p2="Entidades por classe", p2s="uma classe por entidade",
                   p3="Tipos mais comuns", p3s="uma entidade pode ter vários tipos", pat="padrão (search-pattern-miner)",
                   foot="portuguese-entity-gazetteer · o dicionário de entidades dos padrões de busca do SuperNichos"),
}


def panel(ax, x, w, color, title, sub):
    ax.add_patch(FancyBboxPatch((x, 6), w, 52, boxstyle="round,pad=0,rounding_size=1.4", fc=CARD, ec=LINE, lw=1.1))
    ax.add_patch(FancyBboxPatch((x, 57.2), w, 0.8, boxstyle="square,pad=0", fc=color, ec="none"))
    ax.text(x + 2, 53, title, fontsize=13, weight="bold", color=INK, va="center")
    ax.text(x + 2, 49.2, sub, fontsize=8.6, color=MUTED, va="center")


def bars(ax, x, items, color, pt, scale=20):
    mx = items[0][1]
    for i, (k, v) in enumerate(items):
        y = 43 - i * 5.4
        ax.text(x + 2, y + 1.3, k, fontsize=8.8, color=INK, va="center")
        bw = max(0.6, scale * v / mx)
        ax.add_patch(FancyBboxPatch((x + 2, y - 1.9), bw, 1.7, boxstyle="square,pad=0", fc=color, ec="none"))
        ax.text(x + 2.8 + bw, y - 1.05, num(v, pt), fontsize=8, color=MUTED, va="center")


def main() -> None:
    st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))
    ex = json.loads((ROOT / "docs" / "example-busca.json").read_text(encoding="utf-8"))
    out = ROOT / "docs" / "img"
    out.mkdir(parents=True, exist_ok=True)
    classes = sorted(st["por_classe"].items(), key=lambda kv: -kv[1])
    types = [(k, v) for k, v in st["top_tipos"].items() if k not in ("Produto", "Local", "Pessoa")][:7]
    for suf, t in T.items():
        pt = bool(suf)
        fig = plt.figure(figsize=(12, 6.2), dpi=100)
        fig.patch.set_facecolor(BG)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 74)
        ax.axis("off")
        ax.text(3, 69, t["title"], fontsize=21, weight="bold", color=INK, va="center")
        ax.text(3, 63.6, t["sub"].format(n=num(st["entidades_final"], pt), t=st["tipos_distintos_depois"],
                                         c=len(st["por_classe"])), fontsize=10.5, color=MUTED, va="center")

        x1, w1 = 3, 38
        panel(ax, x1, w1, AQUA, t["p1"], t["p1s"])
        ax.text(x1 + 2, 43, f"“{ex['busca']}”", fontsize=12.5, weight="bold", color=INK, va="center")
        y = 36.5
        for e in ex["entidades"]:
            ax.text(x1 + 2, y, e["trecho"], fontsize=9.4, color=INK, va="center", family=MONO)
            ax.text(x1 + 13, y, "→ " + " > ".join(e["entidade"]["tipos"]), fontsize=9.4, color=BLUE, va="center", family=MONO)
            y -= 4.6
        ax.text(x1 + 2, y - 1.5, t["pat"], fontsize=8.4, color=MUTED, va="center")
        for p in ex["padroes_search_pattern_miner"]["entity_prefix"][-1:] + ex["padroes_search_pattern_miner"]["entity_skipgram"][:1]:
            y -= 4.8
            ax.text(x1 + 2, y - 1.5, p, fontsize=9.6, color=ORANGE, va="center", family=MONO, weight="bold")

        x2, w2 = x1 + w1 + 2.5, 36
        panel(ax, x2, w2, BLUE, t["p2"], t["p2s"])
        bars(ax, x2, [(k if pt else CLASS_EN[k], v) for k, v in classes[:7]], BLUE, pt)

        x3 = x2 + w2 + 2.5
        panel(ax, x3, 117 - x3, ORANGE, t["p3"], t["p3s"])
        bars(ax, x3, [(k if pt else TYPE_EN.get(k, k), v) for k, v in types], ORANGE, pt, scale=19)

        ax.text(3, 2.6, t["foot"], fontsize=8.4, color=MUTED)
        ax.text(117, 2.6, "github.com/CaiqueDourado", fontsize=8.4, color=MUTED, ha="right")
        fig.savefig(out / f"cover{suf}.png", facecolor=BG)
        plt.close(fig)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
