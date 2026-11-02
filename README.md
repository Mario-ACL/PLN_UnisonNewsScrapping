# Análisis de noticias de la Universidad de Sonora

Actividad de PLN: scraping del portal de noticias de la Unison y análisis del texto.

## 1. Extracción de datos (`scraper_unison.py`)

### Fuente
Cada noticia está en `https://www.unison.mx/nota/?idnoti=<ID>`. Los IDs son
secuenciales: el 1 es del 16-oct-2002 y el más reciente aparece en la portada
(~39,000 a octubre de 2026). Algunos IDs no existen y el sitio devuelve la
plantilla vacía; esos se registran con `estado = "vacia"`.

### Campos extraídos

| campo | descripción |
|---|---|
| `id`, `url` | identificador de la nota |
| `titulo` | `<h1 class="page-entry-title">` |
| `fecha_texto` / `fecha` | fecha tal cual ("29 de octubre de 2026") y en ISO (`2026-10-29`) |
| `autor` | reportero, cuando la nota lo incluye (en general desde ~2018) |
| `texto` | cuerpo de la nota, un párrafo por línea, sin la línea del autor |
| `n_parrafos`, `n_palabras` | tamaño de la nota |
| `imagen` | URL de la foto principal |
| `descargado` | marca de tiempo de la descarga |

### Uso

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt

# archivo completo (reanudable: si se corta, volver a ejecutar)
.venv\Scripts\python scraper_unison.py

# solo un rango de IDs
.venv\Scripts\python scraper_unison.py --inicio 30000 --fin 39024

# consolidar el JSONL en CSV (solo notas válidas, sin duplicados)
.venv\Scripts\python scraper_unison.py --exportar
```

Salida: `data/raw/noticias_unison.jsonl` (crudo, una nota por línea) y
`data/raw/noticias_unison.csv`. Por defecto usa 4 hilos con 0.5 s de pausa por
hilo (~3.5 notas/s) y reintentos con backoff ante errores 429/5xx.

**El repositorio no incluye el archivo completo** (~130 MB entre JSONL y CSV), solo
una muestra en `data/raw/muestra.jsonl` / `muestra.csv`. Para correr los notebooks
hay que generarlo primero con el scraper. Los notebooks se guardan con sus salidas,
así que se pueden leer en GitHub sin ejecutarlos.

## 2. Exploración (`01_exploracion.ipynb`)

Carga del JSONL, estadísticas generales (volumen, tamaño de las notas, meses, autores),
nubes de palabras con y sin stopwords y una por mes, presencia de los departamentos por año
(en porcentaje y en números absolutos), cambios de vocabulario en el tiempo
(pandemia y estructura de la universidad) y palabras características de cada año
(TF-IDF, un documento por año). El notebook se guarda con sus salidas.

```bash
.venv\Scripts\jupyter notebook 01_exploracion.ipynb
```

### Notas sobre la calidad de los datos
- **Codificación mixta:** las notas antiguas (~2002-2010) están en Windows-1252
  dentro de una página UTF-8. El scraper decodifica UTF-8 y cae a cp1252 byte a
  byte, así que los acentos salen correctos.
- **Títulos antiguos con `?`:** en algunas notas viejas el servidor ya envía
  `¿`/`¡` como `?` literal en el título; no es recuperable desde el sitio.
- **Autor:** se detecta con una heurística (línea corta de nombre propio en
  las dos primeras líneas). No reconoce ~350 firmas: `Redacción` (una sola
  palabra), nombres con punto final (`Paula Trespalacios Argain.`) o con una
  palabra en minúscula; esa línea queda al inicio del `texto`. Hay variantes de
  un mismo nombre (`Haydee Gaxiola` / `Haydeé Gaxiola`) que aún no se unifican.
- **Iniciales (2015–2018):** antes de usar el nombre completo, las notas terminaban
  con las iniciales del reportero entre paréntesis (`(JAR)`, `(BE)`): ~85% de las
  notas de 2015–2017 y 48% de 2018. Quedan al final del `texto`; el notebook las
  quita antes de calcular TF-IDF.
