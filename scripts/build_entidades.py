"""Build portuguese-entity-gazetteer from the curated entity table already exported to D:\\buscas_raw (B1).

    python build_entidades.py --raw D:\\buscas_raw --out D:\\entidades_out

Reads entidades_normalizado.parquet (nlp.dbo.palavras_replace_normalizado) and writes:

portuguese-entity-gazetteer/data/          (Kaggle)
  entidades.parquet / entidades.csv   one row per entity: id, entidade, chave, chave_sem_acento, tipos, classe,
                                      tipos_originais, num_palavras, chave_curta
  tipos.csv                           every clean type: tipo, classe, num_entidades, grafias_originais
  gazetteer-pt.tsv                    entidade<TAB>tipos, ready for search-pattern-miner (keys of 3+ chars and the UFs)
  stats.json                          counts of every step
portuguese-entity-gazetteer/sample/        (GitHub) 50 entities per class, the same rows as TSV, tipos.csv
portuguese-entity-gazetteer/docs/entidades-exemplo.csv   the entities used in the README example
revisao/                              NOT for publishing: removidas.csv (every dropped key and why), samples per class
stats.json                            counts and review examples (send it to Claude)

Decisions (29/10/2026): curated table only; types cleaned (case, spaces, EN->PT, singular/plural) plus a broad class.
Dropped, first reason wins: types "Remover" (curated out) and "Colocar" (never typed); keys without letters, made of
numbers only (except years typed Ano) or of 1-2 characters (except the 27 UFs); Wikipedia "lista de ..." pages; keys
ending in a connector (ad titles cut mid-way: "Adaptador Hdmi Para"); institution names typed as a person, character,
plant, animal, food, vehicle or game ("universidade paulista" as Pessoa). Keys of up to 3 characters are flagged
chave_curta. Keys that differ only in case are merged, their types united. Needs duckdb. Nothing touches SQL Server.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

UFS = {"ac", "al", "ap", "am", "ba", "ce", "df", "es", "go", "ma", "mt", "ms", "mg", "pa", "pb", "pr", "pe", "pi",
       "rj", "rn", "rs", "ro", "rr", "sc", "sp", "se", "to"}

# lower-case spelling -> canonical type (English DBpedia names into Portuguese, plural/singular and spelling variants)
CANON = {
    "person": "Pessoa", "pessoa": "Pessoa", "artist": "Artista", "soccerplayer": "Jogador de futebol",
    "politician": "Político", "político": "Político", "athlete": "Atleta", "writer": "Escritor", "actor": "Ator",
    "personalidade": "Pessoa", "personagens": "Personagem", "reis": "Rei", "music": "Música", "film": "Filme",
    "televisionshow": "Programa de TV", "company": "Empresa", "city": "Cidade", "river": "Rio", "art": "Arte",
    "sport": "Esporte", "brinquedo": "Brinquedos", "relógios": "Relógio", "instrumento musical": "Instrumentos Musicais",
    "acessórios informática": "Acessórios de Informática", "beleza & perfumaria": "Beleza, Perfumaria e Saúde",
    "beleza perfumaria e saúde": "Beleza, Perfumaria e Saúde", "beleza e saúde": "Beleza, Perfumaria e Saúde",
    "tv e home theater": "TV e Home Theater", "tv/dvd/home theater": "TV e Home Theater", "reptil": "Réptil",
    "maquina industrial": "Máquina industrial", "deuses": "Deus", "guerras": "Guerra", "militares": "Militar",
    "listas": "Lista", "pet": "Pet Shop", "organisation": "Organização", "island": "Ilha",
    "editora/livraria": "Editora", "finanças": "Finanças", "transtornos": "Transtorno", "asteroid": "Asteroide",
    "organizações": "Organização", "bacterias": "Bactéria", "agências": "Agência",
}
NOT_A_TYPE = {"de", "e", "da", "do", "dos", "das"}  # pieces left by a ">" typed inside a name

CLASSES = {
    "Pessoa": "pessoa|artista|jogador de futebol|político|atleta|escritor|ator|rei",
    "Personagem": "personagem",
    "Local": "local|cidade|bairro|rio|praia|ilha|museu|montanha|país|região|aeroporto|estádio|rodovia|estação|"
             "geografia|estado|continente|lago|parque|hospital|estação de metrô|freguesia|shopping|turismo|imóvel|"
             "oceano|floresta|deserto|biomas",
    "Organização": "instituição|organização|clube|escola de samba|assembleia|sindicato|conselho|agência",
    "Empresa e marca": "empresa|marca|editora|site|loja/loja virtual|supermercado|usina|disney",
    "Economia e negócios": "economia|administração|contabilidade|finanças|marketing|gestão|logística|comércio|"
                           "indústria|impostos|moeda|meio de pagamento|dinheiro|banco|profissão|publicidade|petróleo|pesca|"
                           "apicultura",
    "Produto": "produto",
    "Veículo": "veículo|carro|moto|aviação|avião|transporte|caminhão",
    "Filme e TV": "filme|tv|programa de tv|filmes e séries|cinema",
    "Música": "música",
    "Livro": "livro",
    "Jogo": "jogo|loterias",
    "Esporte": "esporte|ginástica|automobilismo|equipes|circuito",
    "Animal": "animal|ave|inseto|cão|réptil|peixe|raça",
    "Planta": "planta|árvore|fungo",
    "Comida e bebida": "comida|bebida",
    "Saúde": "doença|medicamento|anatomia|medicina|saúde|área da saúde|fobia|cirurgia|nutrição|transtorno|"
             "contracepção|oftalmologia|plano de saúde|parte do corpo|odontologia|fisioterapia|psiquiatria|"
             "hormônio|higiene|drogas|sono|radiologia|sexualidade",
    "Ciência e tecnologia": "química|física|matemática|biologia|computação|software|engenharia|mecânica|minerais|"
                            "compostos|unidade|filosofia|psicologia|gramática|astronomia|ecologia|arquitetura|ácidos|"
                            "fisiologia|histologia|sociologia|tecnologia|internet|ética|substância|rocha|geometria|"
                            "estatística|magnetismo|embriologia|eletrônica|proteínas|energia|eletricidade|navegação|"
                            "comunicação|satélite|clima|material|tecidos|madeira|polímeros|metalurgia|óptica|meteorologia|"
                            "geologia|cartografia|radiação|criptografia|tipografia|planeta|asteroide|número|resíduos",
    "Educação": "educação|concursos",
    "Religião e mitologia": "religião|mitologia|deus|igreja",
    "Política e direito": "política|direito|militar|guerra|arma|bandeira|crime|segurança|munição|marinha|lei|tratado",
    "Mídia": "emissora de tv|emissora de rádio|revista|jornal|website",
    "Evento": "evento|premiação",
    "Cultura e idioma": "cultura|idioma|origem|arte|cor|povo|folclore|teatro|pintura|dança|design|humor|lenda|"
                        "escotismo|lgbt|movimento|imigração",
    "História e tempo": "ano|mês|época|ocasião|reino|roma|república|colonialismo",
}
CLASS_OF = {t: c for c, ts in CLASSES.items() for t in ts.split("|")}

INSTITUTION = re.compile(
    r"^(instituto|faculdade|universidade|associa[cç][aã]o|funda[cç][aã]o|minist[eé]rio|secretaria|assembl[eé]ia|"
    r"confedera[cç][aã]o|federa[cç][aã]o|sindicato|conselho|superintend[eê]ncia|procuradoria|defensoria|prefeitura|"
    r"escola (estadual|municipal|superior|t[eé]cnica|militar|nacional)|col[eé]gio|sociedade|congrega[cç][aã]o|"
    r"departamento|ag[eê]ncia|companhia)\s")
# round 1 showed that films, bands, books, products and science terms named like institutions are right
# ("Sociedade dos Poetas Mortos", "Companhia do Calypso", "câmara de ar", "centro de massa"); only these classes are
# certainly wrong for an institution name
INSTITUTION_BAD = {"Pessoa", "Personagem", "Planta", "Animal", "Comida e bebida", "Veículo", "Jogo"}
# a key ending in a connector is a cut ad title ("Ministério Público e a", "Centro de Atividades Play Gym Com")
CONNECTOR_END = r"\s(de|da|do|dos|das|com|para|em|ou|por|no|na|nos|nas|sem|um|uma|ao|aos|pra)$|,$"
# outside products only endings that are never the end of a name ("krishna das", "what i do", "Ano Um" stay)
CONNECTOR_END_ANY = r"\s(de|com|para|em|por|sem|pra|aos)$|,$"
CONNECTOR_END_PRODUCT = r"^\S+\s\S+\s.*\s(a|o|e|as|os)$"


def clean_atom(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    import duckdb

    root = a.out / "portuguese-entity-gazetteer"
    data, rev = root / "data", a.out / "revisao"
    for d in (data, rev):
        d.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    src = (a.raw / "entidades_normalizado.parquet").as_posix()
    con.execute(f"""CREATE TABLE raw AS SELECT id, palavra,
        regexp_replace(regexp_replace(coalesce(palavra,''), '^\\s+|\\s+$', '', 'g'), '\\s+', ' ', 'g') AS entidade,
        coalesce(tipos_normalizado, '') AS tipos_originais FROM read_parquet('{src}')""")
    stats: dict = {"linhas_origem": con.execute("SELECT count(*) FROM raw").fetchone()[0]}

    # ---- types: canonical spelling per lower-case form, then a broad class per raw type string
    raw_types = con.execute("SELECT tipos_originais, count(*) FROM raw GROUP BY 1").fetchall()
    spellings: dict[str, Counter] = defaultdict(Counter)
    for s, n in raw_types:
        for t in s.split(">"):
            t = clean_atom(t)
            if t:
                spellings[t.lower()][t] += n

    def canon(t: str) -> str:
        k = clean_atom(t).lower()
        if k in CANON:
            return CANON[k]
        best = spellings[k].most_common()
        caps = [x for x, _ in best if x[:1].isupper()]
        return caps[0] if caps else best[0][0][:1].upper() + best[0][0][1:]

    merged = {k: sorted(v) for k, v in spellings.items() if len({canon(x) for x in v} | set(v)) > 1}
    rows, outro = [], Counter()
    for s, n in raw_types:
        ts = []
        for t in s.split(">"):
            if clean_atom(t) and clean_atom(t).lower() not in NOT_A_TYPE:
                c = canon(t)
                if c not in ts:
                    ts.append(c)
        remover = any(t.lower() == "remover" for t in ts)
        colocar = any(t.lower() == "colocar" for t in ts)  # "to be typed": never typed
        lista = any(t.lower() == "lista" for t in ts)
        classe = next((CLASS_OF[t.lower()] for t in ts if t.lower() in CLASS_OF), "Outro")
        if classe == "Outro" and not remover:
            for t in ts:
                outro[t] += n
        rows.append((s, " > ".join(ts), classe, remover, colocar, lista))
    con.execute("CREATE TABLE tmap (tipos_originais VARCHAR, tipos VARCHAR, classe VARCHAR, remover BOOLEAN, "
                "colocar BOOLEAN, lista BOOLEAN)")
    con.executemany("INSERT INTO tmap VALUES (?, ?, ?, ?, ?, ?)", rows)

    # ---- reasons to drop, first match wins
    con.execute(f"""CREATE TABLE marcada AS SELECT r.id, r.palavra, r.entidade, r.tipos_originais, m.tipos, m.classe,
        CASE WHEN m.remover THEN 'tipo_remover'
             WHEN m.colocar THEN 'tipo_colocar'
             WHEN r.entidade = '' OR NOT regexp_matches(r.entidade, '[[:alnum:]]') THEN 'sem_letra'
             WHEN regexp_matches(r.entidade, '^[0-9 .,/()°ºª:+-]+$')
                  AND NOT (m.classe = 'História e tempo' AND regexp_matches(r.entidade, '^[12][0-9]{{3}}$')) THEN 'so_numeros'
             WHEN length(r.entidade) <= 2 AND lower(r.entidade) NOT IN ({",".join("'" + u + "'" for u in sorted(UFS))})
                  THEN 'curta_1_2'
             WHEN regexp_matches(lower(r.entidade), '^(lista|listas|anexo:)( de| do| da| dos| das|\\s)')
                  OR m.lista THEN 'lista_de'
             WHEN regexp_matches(lower(r.entidade), '{CONNECTOR_END_ANY}')
                  OR (m.classe = 'Produto' AND (regexp_matches(lower(r.entidade), '{CONNECTOR_END}')
                      OR regexp_matches(lower(r.entidade), '{CONNECTOR_END_PRODUCT}')))
                  THEN 'termina_em_conector'
             WHEN regexp_matches(lower(r.entidade), '{INSTITUTION.pattern.replace("'", "''")}')
                  AND m.classe IN ({",".join("'" + c + "'" for c in sorted(INSTITUTION_BAD))})
                  THEN 'instituicao_rotulo_errado'
        END AS motivo
        FROM raw r JOIN tmap m USING (tipos_originais)""")
    stats["removidas_por_motivo"] = dict(con.execute(
        "SELECT coalesce(motivo,'(fica)'), count(*) FROM marcada GROUP BY 1 ORDER BY 2 DESC").fetchall())
    stats["instituicoes_removidas_por_classe"] = dict(con.execute(
        "SELECT classe, count(*) FROM marcada WHERE motivo='instituicao_rotulo_errado' GROUP BY 1 ORDER BY 2 DESC").fetchall())
    stats["exemplos_por_motivo"] = {m: [x[0] + "  {" + x[1] + "}" for x in con.execute(
        "SELECT entidade, tipos FROM marcada WHERE motivo=? ORDER BY hash(id) LIMIT 40", [m]).fetchall()]
        for (m,) in con.execute("SELECT DISTINCT motivo FROM marcada WHERE motivo IS NOT NULL").fetchall()}
    con.execute(f"COPY (SELECT id, entidade, tipos_originais, tipos, classe, motivo FROM marcada WHERE motivo IS NOT NULL "
                f"ORDER BY motivo, entidade) TO '{(rev / 'removidas.csv').as_posix()}' (HEADER, DELIMITER ',')")

    # ---- keep, merge keys that differ only by case (types united), write
    con.execute("""CREATE TABLE ent AS
        SELECT min(id) AS id, arg_min(entidade, id) AS entidade, lower(entidade) AS chave,
               strip_accents(lower(entidade)) AS chave_sem_acento,
               flatten(list(string_split(tipos, ' > ') ORDER BY id)) AS l,
               arg_min(classe, id) AS classe, arg_min(tipos_originais, id) AS tipos_originais,
               len(string_split(lower(entidade), ' ')) AS num_palavras, length(lower(entidade)) <= 3 AS chave_curta
        FROM marcada WHERE motivo IS NULL GROUP BY lower(entidade)""")
    # united types in first-seen order (list_distinct does not keep order)
    con.execute("""CREATE OR REPLACE TABLE ent AS SELECT id, entidade, chave, chave_sem_acento,
        array_to_string(list_filter(l, (x, i) -> list_position(l, x) = i), ' > ') AS tipos,
        classe, tipos_originais, num_palavras, chave_curta FROM ent""")
    stats["chaves_unidas_por_caixa"] = con.execute(
        "SELECT count(*) FROM marcada WHERE motivo IS NULL").fetchone()[0] - con.execute("SELECT count(*) FROM ent").fetchone()[0]
    order = "ORDER BY classe, chave"
    con.execute(f"COPY (SELECT * FROM ent {order}) TO '{(data / 'entidades.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    con.execute(f"COPY (SELECT * FROM ent {order}) TO '{(data / 'entidades.csv').as_posix()}' (HEADER, DELIMITER ',')")
    con.execute(f"""COPY (SELECT trim(t) AS tipo, any_value(classe) AS classe, count(*) AS num_entidades FROM
        (SELECT unnest(string_split(tipos, ' > ')) t, classe FROM ent) GROUP BY 1 ORDER BY num_entidades DESC)
        TO '{(rev / '_tipos.csv').as_posix()}' (HEADER)""")
    # tipos.csv with the original spellings each type absorbed
    with open(rev / "_tipos.csv", encoding="utf-8") as f, open(data / "tipos.csv", "w", encoding="utf-8", newline="") as g:
        w = csv.writer(g)
        w.writerow(["tipo", "classe", "num_entidades", "grafias_originais"])
        absorbed: dict[str, set] = defaultdict(set)
        for k, v in spellings.items():
            for x in v:
                absorbed[canon(x)].add(x)
        for r in csv.DictReader(f):
            w.writerow([r["tipo"], CLASS_OF.get(r["tipo"].lower(), r["classe"]), r["num_entidades"],
                        " | ".join(sorted(absorbed.get(r["tipo"], set()) - {r["tipo"]}))])
    (rev / "_tipos.csv").unlink()

    with open(data / "gazetteer-pt.tsv", "w", encoding="utf-8", newline="\n") as g:
        g.write("# portuguese-entity-gazetteer: entidade<TAB>tipos (\" > \" separates types; one pattern per type)\n")
        g.write("# CC BY-SA 4.0. Keys of 3+ characters and the 27 UFs. github.com/CaiqueDourado/portuguese-entity-gazetteer\n")
        n_tsv = 0
        for ent, tipos in con.execute(f"""SELECT chave, tipos FROM ent WHERE length(chave) >= 3
                OR chave IN ({",".join("'" + u + "'" for u in sorted(UFS))}) ORDER BY chave""").fetchall():
            if "\t" not in ent:
                g.write(f"{ent}\t{tipos}\n")
                n_tsv += 1

    q = lambda sql: con.execute(sql).fetchall()  # noqa: E731
    stats.update({
        "entidades_final": q("SELECT count(*) FROM ent")[0][0],
        "linhas_gazetteer_tsv": n_tsv,
        "chave_curta": q("SELECT count(*) FROM ent WHERE chave_curta")[0][0],
        "por_classe": dict(q("SELECT classe, count(*) FROM ent GROUP BY 1 ORDER BY 2 DESC")),
        "palavras_por_chave": {str(k): v for k, v in q("SELECT least(num_palavras, 10), count(*) FROM ent GROUP BY 1 ORDER BY 1")},
        "tipos_distintos_antes": len(spellings),
        "tipos_distintos_depois": q("SELECT count(DISTINCT trim(t)) FROM (SELECT unnest(string_split(tipos, ' > ')) t FROM ent)")[0][0],
        "top_tipos": dict(q("""SELECT trim(t), count(*) FROM (SELECT unnest(string_split(tipos, ' > ')) t FROM ent)
                              GROUP BY 1 ORDER BY 2 DESC LIMIT 100""")),
        "tipos_sem_classe_top80": dict(outro.most_common(80)),
        "grafias_unidas": dict(list(merged.items())[:150]),
    })
    (a.out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- review samples (not for publishing)
    random.seed(7)
    with open(rev / "amostras.txt", "w", encoding="utf-8") as f:
        for (c,) in q("SELECT DISTINCT classe FROM ent ORDER BY 1"):
            ex = con.execute("SELECT entidade, tipos FROM ent WHERE classe=? ORDER BY hash(id) LIMIT 25", [c]).fetchall()
            f.write(f"[{c}]\n" + "".join(f"  {e}  {{{t}}}\n" for e, t in ex))
    # ---- publishable: counts only (data/stats.json), GitHub samples and the entities used in the README example
    pub = {k: stats[k] for k in ("linhas_origem", "removidas_por_motivo", "instituicoes_removidas_por_classe",
                                 "chaves_unidas_por_caixa", "entidades_final", "linhas_gazetteer_tsv", "chave_curta",
                                 "por_classe", "palavras_por_chave", "tipos_distintos_antes", "tipos_distintos_depois",
                                 "top_tipos")}
    (data / "stats.json").write_text(json.dumps(pub, ensure_ascii=False, indent=1), encoding="utf-8")
    smp, docs = root / "sample", root / "docs"
    for d in (smp, docs):
        d.mkdir(parents=True, exist_ok=True)
    # never in samples, examples or images: brands that asked to be removed, client names; persons only with a
    # subtype (artist, footballer, politician, writer…), i.e. public figures from Wikipedia/DBpedia
    blocked = ("getech|sunglider|herval|incoterm|bel fix|umbro|aurora|pro-bass|r3p|thunderx3|aerocool|fortrek|"
               "highmed|[eé]dez|mundial records|juspodivm|vendah|disco-tec|push")
    con.execute(f"""CREATE TABLE amostra AS SELECT * FROM (
        SELECT *, row_number() OVER (PARTITION BY classe ORDER BY hash(id)) AS n FROM ent
        WHERE NOT regexp_matches(chave, '(^|[^[:alnum:]])({blocked})([^[:alnum:]]|$)')
          AND NOT (classe = 'Pessoa' AND tipos IN ('Pessoa'))
          AND NOT (classe = 'Produto' AND num_palavras > 8)) WHERE n <= 50""")
    con.execute(f"COPY (SELECT * EXCLUDE (n) FROM amostra ORDER BY classe, chave) TO "
                f"'{(smp / 'entidades_sample.csv').as_posix()}' (HEADER)")
    with open(smp / "gazetteer-pt-sample.tsv", "w", encoding="utf-8", newline="\n") as g:
        g.write("# sample of data/gazetteer-pt.tsv (full file on Kaggle): entidade<TAB>tipos\n")
        for ent, tipos in con.execute("SELECT chave, tipos FROM amostra ORDER BY chave").fetchall():
            g.write(f"{ent}\t{tipos}\n")
    import shutil
    shutil.copy(data / "tipos.csv", smp / "tipos.csv")
    keys = ["pão de queijo", "bolo de cenoura", "curitiba", "salvador", "são paulo", "copacabana", "rio de janeiro",
            "neymar", "pelé", "dengue", "diabetes", "ford fiesta", "minecraft", "samba", "hotel", "cerveja",
            "ipva", "detran", "enem", "carnaval", "corinthians", "flamengo", "iphone", "brasil", "casa", "love"]
    con.execute(f"""COPY (SELECT * FROM ent WHERE chave IN ({",".join("'" + k + "'" for k in keys)}) ORDER BY chave)
        TO '{(docs / 'entidades-exemplo.csv').as_posix()}' (HEADER)""")
    stats["amostra_github"] = q("SELECT count(*) FROM amostra")[0][0]
    print(json.dumps({k: stats[k] for k in ("linhas_origem", "removidas_por_motivo", "entidades_final",
                                             "linhas_gazetteer_tsv", "amostra_github", "por_classe")}, ensure_ascii=False, indent=1))
    print(f"-> {a.out / 'stats.json'}  {rev}")


if __name__ == "__main__":
    main()
