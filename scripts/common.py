"""Shared style and the English names of the classes, for the cover and the figures."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

INK, MUTED, LINE, GRID, BG, CARD = "#111111", "#5c5c5c", "#d9dde3", "#e6e8eb", "#fdfdfc", "#ffffff"
BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#7c5cd6"
MONO = "DejaVu Sans Mono"
for fam in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(fam, fallback_to_default=False)
        plt.rcParams["font.family"] = fam
        break
    except ValueError:
        pass

CLASS_EN = {
    "Produto": "Product", "Local": "Place", "Pessoa": "Person", "Música": "Music", "Filme e TV": "Film and TV",
    "Ciência e tecnologia": "Science and technology", "Empresa e marca": "Company and brand", "Saúde": "Health",
    "Esporte": "Sport", "Veículo": "Vehicle", "Política e direito": "Politics and law", "Animal": "Animal",
    "Comida e bebida": "Food and drink", "Planta": "Plant", "Jogo": "Game", "Mídia": "Media",
    "Religião e mitologia": "Religion and mythology", "Cultura e idioma": "Culture and language",
    "Educação": "Education", "Personagem": "Character", "Economia e negócios": "Economy and business",
    "Outro": "Other", "Organização": "Organization", "Evento": "Event", "História e tempo": "History and time",
    "Livro": "Book",
}


def num(n: int, pt: bool) -> str:
    s = f"{n:,}"
    return s.replace(",", ".") if pt else s
