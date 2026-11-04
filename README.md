# Análisis de noticias de la Universidad de Sonora

Scraping del portal de noticias de la Unison (2015–2026) y una historia contada con PLN:
**[Cómo la pandemia cambió la manera de escribir de la Universidad de Sonora](historia/post_medium.md)**.

A partir de 19,813 noticias, la historia muestra que la pandemia hizo las notas menos numerosas pero más largas y
llenas de voces (citas textuales), y que desde el cambio de rectoría de 2025 las voces casi desaparecen: menos citas,
titulares sin nombres, verbos que realzan en lugar de reportar y más lenguaje incluyente, escritos por las mismas personas.

## Archivos principales

| Archivo | Qué contiene |
|---|---|
| [`scraper_unison.py`](scraper_unison.py) | El scraper: descarga las noticias del portal de la Unison. |
| [`historia/post_medium.md`](historia/post_medium.md) | El post de Medium, con sus 8 gráficas en [`historia/graficas/`](historia/graficas). |
| [`01_exploracion.ipynb`](01_exploracion.ipynb) | La exploración: estadísticas generales, nubes de palabras, departamentos, cambios de vocabulario y TF-IDF por año. |
| [`06_historia_medium.ipynb`](06_historia_medium.ipynb) | El análisis del post, sección por sección: calcula cada cifra, genera las 8 gráficas y termina con una tabla de todas las cifras que cita el texto. |

Los notebooks se guardan con sus salidas, así que se pueden leer en GitHub sin ejecutarlos.

## 1. El scraper (`scraper_unison.py`)

Cada noticia está en `https://www.unison.mx/nota/?idnoti=<ID>`, con IDs secuenciales (el más reciente aparece en la
portada). El scraper recorre los IDs con 4 hilos y 0.5 s de pausa por hilo (~3.5 notas por segundo), reintenta ante
errores 429/5xx y es reanudable: si se corta, se vuelve a ejecutar y sigue donde se quedó. De cada noticia guarda
`id`, `url`, `titulo`, `fecha`, `autor`, `texto` (un párrafo por línea), `n_parrafos`, `n_palabras` e `imagen`.

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# archivo completo
.venv\Scripts\python scraper_unison.py

# solo un rango de IDs
.venv\Scripts\python scraper_unison.py --inicio 30000 --fin 39024

# consolidar el JSONL en CSV (solo notas válidas, sin duplicados)
.venv\Scripts\python scraper_unison.py --exportar
```

Salida: `data/raw/noticias_unison.jsonl` (una nota por línea) y `data/raw/noticias_unison.csv`.
**El repositorio no incluye el archivo completo** (~130 MB), solo una muestra en `data/raw/muestra.jsonl`.
Para volver a correr los notebooks hay que generarlo primero con el scraper.

## 2. La historia

- **El post:** [`historia/post_medium.md`](historia/post_medium.md). Para pasarlo a Medium, ver [`historia/README.md`](historia/README.md).
- **Cómo se hizo:** [`06_historia_medium.ipynb`](06_historia_medium.ipynb) mide la producción de noticias, el largo de las
  notas, las citas, los verbos de cita, el estilo con la **Delta de Burrows** (estilometría con las 60 palabras más
  comunes) y compara a cada periodista consigo mismo antes y después del cambio de rectoría.

```bash
.venv\Scripts\jupyter notebook 06_historia_medium.ipynb
```

## Otros notebooks

`02` a `05` son los análisis intermedios que llevaron a la historia: temas por año con lematización (spaCy),
modelado de temas de tecnología y cultura, comparación con Google Trends y la estilometría completa.
