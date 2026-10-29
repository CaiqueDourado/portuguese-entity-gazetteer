"""Checks run in CI on sample/, docs/ and data/stats.json. Run: python scripts/validate.py"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "sample"
BLOCKED = (r"(?i)(^|[^[:alnum:]])(getech|sunglider|herval|incoterm|bel fix|umbro|aurora|pro-bass|r3p|thunderx3|"
           r"aerocool|fortrek|highmed|[eé]dez|mundial records|juspodivm|vendah|push)([^[:alnum:]]|$)")
errors: list[str] = []


def check(ok: bool, msg: str) -> None:
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        errors.append(msg)


def one(sql: str):
    return duckdb.sql(sql).fetchall()[0][0]


st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))
ent, tip = (S / "entidades_sample.csv").as_posix(), (S / "tipos.csv").as_posix()
cols = [r[0] for r in duckdb.sql(f"DESCRIBE SELECT * FROM read_csv_auto('{ent}')").fetchall()]
E = f"read_csv_auto('{ent}', all_varchar=true)"
T = f"read_csv_auto('{tip}', all_varchar=true)"

check(cols == ["id", "entidade", "chave", "chave_sem_acento", "tipos", "classe", "tipos_originais", "num_palavras",
               "chave_curta"], "sample: the 9 columns, in order")
check(one(f"SELECT count(*) - count(DISTINCT chave) FROM {E}") == 0, "sample: one row per key")
check(one(f"SELECT count(*) FROM {E} WHERE chave <> lower(entidade)") == 0, "sample: chave = lower(entidade)")
check(one(f"SELECT count(*) FROM {E} WHERE chave_sem_acento <> strip_accents(chave)") == 0, "sample: chave_sem_acento = chave without accents")
check(one(f"SELECT count(*) FROM {E} WHERE entidade <> trim(entidade) OR entidade LIKE '%  %'") == 0, "sample: no outer or double spaces")
check(one(f"SELECT count(*) FROM {E} WHERE (length(chave) <= 3) <> (chave_curta = 'true')") == 0, "sample: chave_curta = key of up to 3 characters")
check(one(f"SELECT count(*) FROM {E} WHERE length(chave) <= 2") == 0, "sample: no key of 1-2 characters")
check(one(f"SELECT count(*) FROM {E} WHERE regexp_matches(chave, '^(lista|listas) (de|do|da|dos|das) ')") == 0, "sample: no Wikipedia list pages")
check(one(f"SELECT count(*) FROM {E} WHERE regexp_matches(chave, '\\s(de|com|para|em|por|sem)$')") == 0, "sample: no key cut after a connector")
check(one(f"SELECT count(*) FROM {E} WHERE regexp_matches(lower(tipos), '(^|> )(remover|colocar)( >|$)')") == 0, "sample: no Remover/Colocar types")
check(one(f"SELECT count(*) FROM {E} WHERE regexp_matches(chave, '{BLOCKED}')") == 0, "sample: no brands that asked removal, no client names")
check(one(f"SELECT count(*) FROM {E} WHERE classe = 'Pessoa' AND tipos = 'Pessoa'") == 0, "sample: persons only with a subtype (public figures)")
check(one(f"SELECT count(*) FROM {E} e ANTI JOIN {T} t ON e.classe = t.classe") == 0, "sample: every class is in tipos.csv")
atoms = {r[0] for r in duckdb.sql(f"SELECT tipo FROM {T}").fetchall()}
used = {t for r in duckdb.sql(f"SELECT tipos FROM {E}").fetchall() for t in r[0].split(" > ")}
check(used <= atoms, "sample: every type is in tipos.csv")
check(one(f"SELECT count(*) - count(DISTINCT tipo) FROM {T}") == 0, "tipos.csv: one row per type")
check(len({r[0] for r in duckdb.sql(f"SELECT classe FROM {T}").fetchall()}) == len(st["por_classe"]), "tipos.csv: the same classes as stats")

with open(S / "gazetteer-pt-sample.tsv", encoding="utf-8") as f:
    lines = [ln.rstrip("\n") for ln in f if not ln.startswith("#")]
check(all(ln.count("\t") == 1 for ln in lines), "TSV: entidade<TAB>tipos on every line")
check(len(lines) == one(f"SELECT count(*) FROM {E}"), "TSV: the same rows as the CSV sample")

kept = st["removidas_por_motivo"]["(fica)"]
check(sum(st["removidas_por_motivo"].values()) == st["linhas_origem"], "stats: every source row kept or dropped once")
check(kept - st["chaves_unidas_por_caixa"] == st["entidades_final"], "stats: kept rows minus case merges = entities")
check(sum(st["por_classe"].values()) == st["entidades_final"], "stats: classes add up to the entities")
ex = json.loads((ROOT / "docs" / "example-busca.json").read_text(encoding="utf-8"))
check(len(ex["entidades"]) >= 2 and all(e["entidade"]["classe"] in st["por_classe"] for e in ex["entidades"]),
      "docs/example-busca.json: entities with known classes")
with open(ROOT / "docs" / "entidades-exemplo.csv", encoding="utf-8") as f:
    check(all(r["classe"] in st["por_classe"] for r in csv.DictReader(f)), "docs/entidades-exemplo.csv: known classes")

print(f"\n{len(errors)} failure(s)")
sys.exit(1 if errors else 0)
