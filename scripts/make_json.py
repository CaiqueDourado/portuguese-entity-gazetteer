"""The README example (docs/example-busca.json): one search, the entities found in it and the patterns they make.

    python scripts/make_json.py                                   # from docs/entidades-exemplo.csv
    python scripts/make_json.py --data <kaggle folder>            # from the full entidades.parquet

Entities are looked up whole-word, longest first, accents and case ignored (the same rule as search-pattern-miner).
If search-pattern-miner is installed (pip install "search-pattern-miner @ git+https://github.com/CaiqueDourado/
search-pattern-miner#subdirectory=python"), the patterns of its entity algorithms are added.
"""

from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEARCH = "hotel barato em salvador"


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def load(data: Path | None) -> dict[str, dict]:
    if data:
        import duckdb
        f = next(data.rglob("entidades.parquet")).as_posix()
        rows = duckdb.sql(f"SELECT * FROM '{f}'").fetchall()
        cols = [c[0] for c in duckdb.sql(f"DESCRIBE SELECT * FROM '{f}'").fetchall()]
        rows = [dict(zip(cols, r)) for r in rows]
    else:
        with open(ROOT / "docs" / "entidades-exemplo.csv", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    return {fold(r["chave"]): r for r in rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path)
    ap.add_argument("--busca", default=SEARCH)
    a = ap.parse_args()
    ents = load(a.data)
    longest = max(len(k.split()) for k in ents)
    words, found, i = a.busca.split(), [], 0
    while i < len(words):
        for n in range(min(longest, len(words) - i), 0, -1):
            r = ents.get(fold(" ".join(words[i:i + n])))
            if r:
                found.append({
                    "trecho": " ".join(words[i:i + n]),
                    "entidade": {"id": int(r["id"]), "entidade": r["entidade"], "chave_sem_acento": r["chave_sem_acento"],
                                 "tipos": r["tipos"].split(" > "), "classe": r["classe"],
                                 "tipos_originais": r["tipos_originais"], "num_palavras": int(r["num_palavras"])}})
                i += n
                break
        else:
            i += 1
    out = {"busca": a.busca, "entidades": found}
    try:
        from search_pattern_miner import Gazetteer, mine
        gaz = Gazetteer([(f["trecho"].lower(), " > ".join(f["entidade"]["tipos"])) for f in found])
        out["padroes_search_pattern_miner"] = mine(a.busca, gaz, ["entity_prefix", "entity_skipgram"])
    except ImportError:
        print("search-pattern-miner not installed: patterns left out")
    path = ROOT / "docs" / "example-busca.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(found)} entities -> {path}")


if __name__ == "__main__":
    main()
