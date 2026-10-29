"""Get the Kaggle folder ready to upload: dataset-metadata.json with the description and every file's columns.

    python scripts/prepare_kaggle.py --kaggle D:\\entidades_out\\portuguese-entity-gazetteer\\data
    kaggle datasets create -p D:\\entidades_out\\portuguese-entity-gazetteer\\data           # first time
    kaggle datasets version -p D:\\entidades_out\\portuguese-entity-gazetteer\\data -m "…"    # later versions
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S, I, B = "string", "integer", "boolean"
ENT = [("id", I, "Id of the entity in the source table (nlp.dbo.palavras_replace_normalizado)"),
       ("entidade", S, "The entity as written in the source, outer and double spaces removed"),
       ("chave", S, "Lookup key: the entity in lower case"),
       ("chave_sem_acento", S, "The key without accents"),
       ("tipos", S, "One or more types separated by ' > ' (several types, not a hierarchy): 'Local > Cidade'"),
       ("classe", S, "One of 26 broad classes, from the first type that has one (Pessoa, Local, Produto…)"),
       ("tipos_originais", S, "The types as they were in the source, before cleaning (English DBpedia names, case variants)"),
       ("num_palavras", I, "Number of words in the key"),
       ("chave_curta", B, "Key of up to 3 characters (acronyms, short names): match these whole-word and case-sensitive")]
FILES = {
    "entidades.parquet": ("All 307,397 entities, one per row.", ENT),
    "entidades.csv": ("The same table as CSV.", ENT),
    "tipos.csv": ("Every clean type with its class, how many entities have it and the spellings it absorbed.", [
        ("tipo", S, "Clean type"), ("classe", S, "Broad class of the type"),
        ("num_entidades", I, "Entities with this type"),
        ("grafias_originais", S, "Source spellings merged into this type, ' | ' separated (Person | person)")]),
    "gazetteer-pt.tsv": ("The gazetteer in the format search-pattern-miner reads: entidade<TAB>tipos, lower case, "
                         "lines starting with # are comments.", None),
    "stats.json": ("Counts of every build step (rows dropped by reason, classes, types).", None),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, required=True)
    a = ap.parse_args()
    k = a.kaggle
    resources = []
    for name, (desc, fields) in FILES.items():
        if not (k / name).exists():
            raise SystemExit(f"missing {k / name}: run build_entidades.py first")
        r = {"path": name, "description": desc}
        if fields:
            r["schema"] = {"fields": [{"name": n, "type": t, "description": d} for n, t, d in fields]}
        resources.append(r)
    meta = {
        "title": "Dicionário de Entidades do Português: 307 mil",
        "subtitle": "Portuguese gazetteer: places, people, works and products with their types",
        "id": "caiquedourado/portuguese-entity-gazetteer",
        "licenses": [{"name": "Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)"}],
        "keywords": ["languages", "nlp", "text", "brazil"],
        "description": (ROOT / "docs" / "kaggle-description.md").read_text(encoding="utf-8"),
        "isPrivate": False,
        "resources": resources,
    }
    (k / "dataset-metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    copy = ROOT / "kaggle" / "dataset-metadata.json"
    copy.parent.mkdir(exist_ok=True)
    copy.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")  # the repo keeps a copy
    print(f"{len(resources)} files described -> {k / 'dataset-metadata.json'}")
    print(f"title {len(meta['title'])} chars · subtitle {len(meta['subtitle'])} chars")


if __name__ == "__main__":
    main()
