# convoj

Nástroj na jednoduchú konverziu diagramov do PNG. Zdrojové formáty: **SVG, draw.io, PlantUML, UMLet, Mermaid** (a SVG exporty z Archi).

Jedným príkazom skonvertuje všetky obrázky v adresári (vrátane podadresárov), alebo len konkrétny súbor (`-f`).

Konverzia je inkrementálna — súbor sa konvertuje len ak výstup ešte neexistuje, alebo ak je zdroj novší ako výstup. Prekonvertovanie všetkého sa dá vynútiť prepínačom `-F`.

## Setup

### Docker

Ako prvy potrebujem zbuildovat image a dať ho do dockera, odkiaľ sa bude spúšťať.

Image obsahuje python skripty, ImageMagick a drawio (PlantUML, UMLet a Mermaid zatiaľ nie).

```bash
# build (raz, v adresári convoj)
docker build -t convoj .
```

### Nastavenie prostredia

Aby som vedel ľahko spúšťať convoj odkiaľkoľvek, treba do `~/.local/bin` pridať linku na script

```bash
mkdir -p ~/.local/bin
ln -s /home/vojto/Projects/convoj/convoj_docker.sh ~/.local/bin/convoj
```

```bash
# ln -s /mnt/c/Projects_src/vojto_tools/convoj/convoj_docker.sh ~/.local/bin/convoj   # WSL, ak beží z Windows disku
```

`~/.local/bin` musí byť v PATH. Overenie:

```bash
echo $PATH | tr ':' '\n' | grep "$HOME/.local/bin"
```

Ak nie, treba na koniec `~/.profile` pridať riadok

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Overenie, že linka funguje:

```bash
type convoj        # má vypísať: convoj is /home/vojto/.local/bin/convoj
```

## Použitie

```bash
convoj SRC DST PRÍKAZ
convoj build/logo build/img_png/logo svg   # vstupné svg hľadá v build/logo a výstup ukladá do build/img_png/logo
```

Prepínače: 
  `-f` (len daný súbor/adresár),  
  `-F` (vynúť konverziu aj keď je výstup aktuálny),  
  `-s` (mierka, default 2.0),  
  `-l` (loglevel),  
  `-g` (log do súboru),  
  `-n` / `--dry-run` (len pre `prune`: iba vypíše, čo by zmazal).

Príkazy: `all`, `clean`, `prune`, `svg`, `drawio`, `plantuml`, `umlet`, `mermaid`, `archi`, `copy` (hotové `.png`/`.webp`/`.ico` sa nekonvertujú, len skopírujú do `img_png`).

Skryté súbory (začínajú bodkou, napr. zálohy draw.io `.$name.drawio.bkp`) a súbory v adresároch `old` a `build` sa nekonvertujú.

### Mazanie osirelých výstupov (`prune`)

Inkrementálne generovanie nikdy nič nemaže — keď zdroj zmažeš alebo premenuješ, jeho starý výstup v `DST` ostane (a napr. Antora ho ďalej publikuje). `clean` zmaže všetko a potom treba pomalé plné generovanie. `prune` zmaže **len** výstupy, ku ktorým už neexistuje zdroj, ostatné nechá, takže následné generovanie prekonvertuje len zmenené obrázky.

Odporúčané poradie — najprv `prune`, potom generovanie:

```bash
convoj docs/img build/img-docs prune
convoj docs/img build/img-docs svg
convoj docs/img build/img-docs drawio
```

Ako rozhoduje:

- Výstup je osirelý, keď k nemu neexistuje žiadny zdroj zo žiadneho typu. Nezáleží na tom, aký typ potom generuješ: `name.png` ostane, ak existuje `name.drawio`, `name.svg`, `name.puml`, … alebo `name.png` (typ `copy`).
- Mapovanie zdroj → výstup sa berie z rovnakej tabuľky krokov ako konverzia (`STEPS` v `src/convert.py`), takže nový typ netreba v `prune` dopĺňať.
- Medzivýstupy (`.puml` / `.uxf` → `.svg` → `.png`) sú tiež výstupy: `name.svg` aj `name.png` sa zmažú spolu. `.svg` v `DST` bez zdroja `.puml`/`.uxf` sa teda považuje za osirelé.
- Za zdroj sa nepovažuje nič, čo convoj pri konverzii ignoruje (skryté súbory, `*.bkp`, adresáre `old`/`build`).
- Maže len súbory s príponou, ktorú convoj vytvára (`.png`, `.svg`, `.webp`, `.ico`). Ostatné (napr. `notes.txt`) aj skryté súbory nechá a zaloguje na úrovni `debug`. Symlinky nesleduje ani nemaže.
- Po zmazaní odstráni prázdne podadresáre v `DST`, ku ktorým už neexistuje zdrojový adresár (samotný `DST` nie). Prázdny adresár so zdrojom ostane — konverzia by ho aj tak znovu vytvorila.
- Odmietne bežať (návratový kód 1, nič nezmaže), ak je `DST` rovnaký ako `SRC`, je v ňom vnorený, alebo ak je `SRC` vnorený v `DST`.
- `-f` obmedzí mazanie na daný súbor / adresár (rovnako ako pri konverzii), `-n` iba vypíše, čo by zmazal.

Log: každý zmazaný súbor `remove orphan <cesta>`, adresár `remove empty dir <cesta>`, na konci `pruned N files, M dirs`.

### Testy

```bash
python3 -m unittest discover -s tests -v
```

Testy spúšťajú `convoj.py` ako CLI, externé nástroje nahrádza `tests/fake_tool.py` (cez `CONVOJ_DRAWIO_CMD`, `CONVOJ_MAGICK_CMD`), takže netreba Docker ani drawio.

## Ako to funguje

### Python

Convoj sa skladá z troch python skriptov:

- **`src/convoj.py`** — obslužný program. 
    - Spracuje argumenty z príkazového riadku a nájde koreň projektu podľa adresárovej štruktúry, ktorú používam na projektoch (hľadá smerom nahor markery `.git`, `build`, `docs`, `src_doc`). 
    - Obrázky berie z `docs/img/` alebo `src_doc/img/`, výstup ukladá do `build/img_png/` so zachovaním štruktúry podadresárov.
- **`src/convert.py`** — samotná konverzia. Kroky konverzie sú v tabuľke `STEPS`; pre každý krok prejde stromom zdrojov a pre každý súbor zavolá externý nástroj.
- **`src/prune.py`** — príkaz `prune`, z tabuľky `STEPS` odvodí, ktoré výstupy majú ešte zdroj.

Convoj teda sám nič nekreslí — iba prevoláva externé nástroje:

| Formát | Prípona | Nástroj | Cesta |
|---|---|---|---|
| draw.io | `.drawio` | draw.io CLI | `.drawio` → `.png` |
| SVG (aj Archi export) | `.svg` | ImageMagick (`magick`) | `.svg` → `.png` |
| PlantUML | `.puml` | plantuml.jar (java) | `.puml` → `.svg` → `.png` |
| UMLet | `.uxf` | Umlet | `.uxf` → `.svg` → `.png` |
| Mermaid | `.mmd` | mermaid-cli (`mmdc`) | `.mmd` → `.png` |


### Docker

`convoj` smeruje na `/home/vojto/Projects/convoj/convoj_docker.sh`. Toto je wrapper namountuje projekt a spustí kontajner. 

Bez wrappera by to bolo:

```bash
# alebo priamo bez wrappera
docker run --rm --user $(id -u):$(id -g) -v "$PWD:/work" convoj all
```

Ako to funguje: drawio je Electron aplikácia, v kontajneri beží headless cez `xvfb-run` (wrapper `docker/drawio-wrapper.sh`). Projekt sa mountuje ako `/work`, výstupy pribudnú v `build/img_png/` na disku. 

Iný image nastavíš cez `CONVOJ_IMAGE`. Cesty k nástrojom sa dajú prebiť env premennými (inak default podľa OS): `CONVOJ_DRAWIO_CMD`, `CONVOJ_MAGICK_CMD`, `CONVOJ_UMLET_CMD`, `CONVOJ_MMDC_CMD`, `CONVOJ_PLANTUML_JAR`.

Wrappery: `convoj_docker.sh` (Linux/WSL, spúšťa Docker kontajner), `convoj_linux.sh` (Linux/WSL natívne — nástroje musia byť nainštalované lokálne), `convoj.bat` (Windows natívne, s `CONVOJ_DOCKER=1` cez Docker).

### Koncept

![convoj koncept](convoj_concept.png)

Zdrojový diagram je v `docs/img/convoj_concept.drawio`

## Obmedzenia / TODO

- Docker image zatiaľ nepokrýva PlantUML, UMLet a Mermaid — tie fungujú len natívne (Windows).
