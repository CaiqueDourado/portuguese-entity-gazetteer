**Portuguese Entity Gazetteer**: **307,397 entities in Portuguese** with their types: places, people, films, songs, TV shows, products, brands, foods, diseases, laws, animals, plants… Each entity has **one or more of 747 types** (*Salvador* is `Local > Cidade`, *Neymar* is `Pessoa > Jogador de futebol`) and **one of 26 broad classes**. It also comes as a ready-to-use gazetteer for [search-pattern-miner](https://github.com/CaiqueDourado/search-pattern-miner), which turns searches into templates by replacing entities with their type: *hotel barato em salvador* → `[turismo] barat [cidade]`.

It is the entity dictionary the author built and curated by hand to find patterns in millions of Google searches, the patterns behind [SuperNichos.com](https://supernichos.com) and the [google-keywords-dataset](https://www.kaggle.com/datasets/caiquedourado/google-keywords-dataset).

![Portuguese Entity Gazetteer](https://raw.githubusercontent.com/CaiqueDourado/portuguese-entity-gazetteer/main/docs/img/cover.png)

## How a search uses it

![One search in JSON](https://raw.githubusercontent.com/CaiqueDourado/portuguese-entity-gazetteer/main/docs/img/busca-json.png)

The entities of *hotel barato em salvador*, looked up whole-word with the longest key first, and the patterns search-pattern-miner makes from them: one pattern per type, so `Local > Cidade` gives both `[local]` and `[cidade]`.

## Files

- `entidades.parquet` / `entidades.csv` (307,397 rows): one entity per row: `entidade`, lookup keys `chave` (lower case) and `chave_sem_acento`, `tipos` (one or more, separated by ` > `; several types, not a hierarchy), `classe` (one of 26), `tipos_originais` (before cleaning), `num_palavras`, `chave_curta` (key of up to 3 characters).
- `tipos.csv` (747 rows): every type with its class, how many entities have it and the source spellings merged into it.
- `gazetteer-pt.tsv` (307,397 lines): `entidade<TAB>tipos`, the format search-pattern-miner reads.
- `stats.json`: every count of the build.

## The site this comes from

![SuperNichos.com](https://raw.githubusercontent.com/CaiqueDourado/portuguese-entity-gazetteer/main/docs/img/supernichos.com_screenshot.png)

[SuperNichos.com](https://supernichos.com) (2023–) sells access to millions of Google searches grouped into patterns, to find niches for new sites. Three of its algorithms first replace the entities of each search with their type, so *apartamentos para alugar em curitiba* becomes `[imovel] par [local]`; 749,693 of the published patterns carry at least one entity. This dataset is the dictionary they used, cleaned.

## What the data shows

![Entities per class](https://raw.githubusercontent.com/CaiqueDourado/portuguese-entity-gazetteer/main/docs/img/classes.png)

Products, places and people are 60%: 70,400 product names, 63,822 places and 51,921 people (by type, 10,179 cities, 5,094 neighbourhoods, 12,995 artists, 3,527 footballers, 2,896 politicians). `classe` comes from the first type that has one, so most books are class *Produto* (`Produto > Livro`). The source had 775 types mixing English DBpedia names and Portuguese, case and plural variants; now 747.

## How it was made

![How it was made](https://raw.githubusercontent.com/CaiqueDourado/portuguese-entity-gazetteer/main/docs/img/flow.png)

- **Sources**: titles and types of the Portuguese Wikipedia through DBpedia, product titles and department names of Brazilian online stores, and lists typed by the author (foods, diseases, law, religion, brands).
- **Curation**: the author reviewed the entities in an internal tool (keep, change type, *Remover*). This dataset starts from the curated table (412,204 keys).
- **Build** ([scripts/build_entidades.py](https://github.com/CaiqueDourado/portuguese-entity-gazetteer/blob/main/scripts/build_entidades.py)): dropped 99,078 keys marked *Remover*, 4,833 product titles cut after a connector (*Adaptador Hdmi Para*), 421 Wikipedia list pages, 213 never-typed keys, 133 keys of 1–2 characters (the 27 state codes kept), 52 number-only keys (years kept), 28 institutions typed as a person, food or plant, 2 keys without letters; merged 47 case duplicates. Types cleaned (English names translated, case and plural merged) and mapped by hand to 26 classes.

## Limits

- Common words as entities: *brasil* is an `Animal`, *casa* is `Local > Imóvel`, *love* is a `Pessoa`. Check the type before trusting a single-word match.
- Wrong labels remain in the long tail (*bandeira de blumenau* as *Comida*).
- Not only Portuguese: film, song and band names are often in English; places from all over the world.
- No disambiguation: one row per key.
- People come from Wikipedia and DBpedia titles; removal requests are welcome on GitHub.

## License and links

Data: CC BY-SA 4.0 (contains information from Wikipedia and DBpedia, CC BY-SA). Code: MIT. Code, data dictionary, sample and notebook: [github.com/CaiqueDourado/portuguese-entity-gazetteer](https://github.com/CaiqueDourado/portuguese-entity-gazetteer). Related: [search-pattern-miner](https://github.com/CaiqueDourado/search-pattern-miner), [google-keywords-dataset](https://www.kaggle.com/datasets/caiquedourado/google-keywords-dataset), [dicionario-portugues](https://www.kaggle.com/datasets/caiquedourado/dicionario-portugues).
