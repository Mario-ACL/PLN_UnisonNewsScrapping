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

## 3. Temas por año (`02_temas_por_anio.ipynb`)

Profundiza en los cambios de vocabulario para construir la historia:

- **Limpieza:** quita firmas (iniciales o nombres al inicio y al final), enlaces y correos.
- **Normalización:** lematización con spaCy (`es_core_news_sm`), separando *temas*
  (sustantivos y adjetivos) de *nombres* (nombres propios), con bigramas.
- **Etapas:** similitud coseno entre años, términos característicos de cada etapa
  (2015–2019, 2020–2022, 2023–2026) y lo que sube y baja entre la primera y la última.
- **Cuatro historias de cambio:** la reorganización de 2023, los rectores, el lenguaje
  incluyente y los temas nuevos (pandemia, inteligencia artificial, semiconductores).

La lematización tarda ~10 minutos la primera vez; el resultado se guarda en
`data/processed/noticias_lemas.jsonl` (ignorado por git). Si se vuelve a correr el
scraper, hay que borrar ese archivo para que se recalcule.

## 4. Tecnología, cultura y vida universitaria (`03_tecnologia_y_cultura.ipynb`)

Primer paso de la historia: *¿las noticias de la Unison reflejan el progreso
tecnológico y cultural de Sonora?* Usa los lemas del notebook 02 (hay que correrlo antes).

- **Modelado de temas** con TF-IDF + NMF (scikit-learn): 45 temas generales, agrupados
  en tecnología, cultura y vida universitaria, y un segundo modelo dentro de tecnología
  y de cultura para temas más específicos (IA, litio, energía solar; teatro, ópera y
  FAOT, artes plásticas...).
- **Tema destacado de cada año** y una **lista corta** de temas concretos
  (semiconductores, IA, litio, nearshoring, FAOT, sindicatos...) para compararla después
  con Google Trends y con otros medios.
- **Vida universitaria:** cómo presenta el portal los conflictos con los sindicatos.

## 5. Noticias vs. Google Trends (`04_google_trends.ipynb`)

Paso 2 de la historia: compara la lista corta del notebook 03 con el interés de
búsqueda en Google (México y Sonora, mensual, 2015–2026).

- **Datos:** se descargan con `pytrends` (librería no oficial) y se guardan en
  `data/raw/google_trends.csv` (descargado el 1 de noviembre de 2026; sí va en el
  repositorio). Si el archivo existe, el notebook solo lo lee.
- **Año por año:** curvas escaladas a su máximo, correlación y si la Unison va al mismo
  tiempo, se adelanta o va atrás del interés del público.
- **Mes por mes:** el FAOT (cada enero) y las búsquedas del sindicato STAUS contra las
  notas del portal que lo mencionan.

## 6. Cómo se hacen las noticias (`05_como_se_hacen_las_noticias.ipynb`)

Estilometría de las noticias en cuatro etapas: antes (2015–2019), pandemia (2020–2021),
después (2022–2024) y nueva etapa (2025–2026).

- **Producción:** notas por año y por día, fin de semana, firmas (iniciales antes de
  2018, nombres después) y concentración del equipo.
- **Forma:** largo, párrafos, oraciones y legibilidad (índice INFLESZ de Szigriszt-Pazos).
- **Voces:** texto entre comillas, a quién citan los titulares y verbos de cita.
- **Huella de estilo:** Delta de Burrows con las 60 palabras funcionales más frecuentes.
- **Equipo o línea editorial:** cada reportero comparado consigo mismo, y el cambio mes por
  mes alrededor del cambio de rectora (junio de 2025).

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
