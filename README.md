# convoj

Nástroj na jednoduchú konverziu diagramov do PNG. Zdrojové formáty: **SVG, draw.io, PlantUML, UMLet, Mermaid** (a SVG exporty z Archi).

Jedným príkazom skonvertuje všetky obrázky v adresári (vrátane podadresárov), alebo len konkrétny súbor (`-f`).

## Ako to funguje

Convoj sa skladá z dvoch python skriptov:

- **`src/convoj.py`** — obslužný program. 
    - Spracuje argumenty z príkazového riadku a nájde koreň projektu podľa adresárovej štruktúry, ktorú používam na projektoch (hľadá smerom nahor markery `.git`, `build`, `docs`, `src_doc`). 
    - Obrázky berie z `docs/img/` alebo `src_doc/img/`, výstup ukladá do `build/img_png/` so zachovaním štruktúry podadresárov.
- **`src/convert.py`** — samotná konverzia. Prejde stromom zdrojov a pre každý súbor zavolá externý nástroj.

Convoj teda sám nič nekreslí — iba prevoláva externé nástroje:

| Formát | Prípona | Nástroj | Cesta |
|---|---|---|---|
| draw.io | `.drawio` | draw.io CLI | `.drawio` → `.png` |
| SVG (aj Archi export) | `.svg` | ImageMagick (`magick`) | `.svg` → `.png` |
| PlantUML | `.puml` | plantuml.jar (java) | `.puml` → `.svg` → `.png` |
| UMLet | `.uxf` | Umlet | `.uxf` → `.svg` → `.png` |
| Mermaid | `.mmd` | mermaid-cli (`mmdc`) | `.mmd` → `.png` |

## Použitie

```bash
./convoj.sh all                  # skonvertuj všetko
./convoj.sh drawio               # len drawio súbory
./convoj.sh clean                # zmaž build/ (generované súbory)
./convoj.sh all -f Business/ciel # len konkrétny súbor / adresár
./convoj.sh all -s 4             # väčšia mierka (postery)
```

Príkazy: `all`, `clean`, `svg`, `drawio`, `plantuml`, `umlet`, `mermaid`, `archi`.
Prepínače: `-f` (len daný súbor/adresár), `-s` (mierka, default 2.0), `-l` (loglevel), `-g` (log do súboru).

Na Windows je wrapper `convoj.bat`, na Linux/WSL `convoj.sh`.

## Koncept

![convoj koncept](convoj_concept.png)

Zdrojový diagram: `docs/img/convoj_concept.drawio` (PNG si vygeneruješ samotným convoj-om).

## Obmedzenia / TODO

- Cesty k externým nástrojom sú zatiaľ natvrdo v `convert.py` (Windows cesty) — cieľ je presunúť convoj do **Dockeru**, aby sa dal rovnako spúšťať aj na Ubuntu.
