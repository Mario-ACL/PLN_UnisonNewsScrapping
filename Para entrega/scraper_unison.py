"""
Scraper del portal de noticias de la Universidad de Sonora.

Cada noticia vive en https://www.unison.mx/nota/?idnoti=<ID>, con IDs
secuenciales desde 1 (oct-2002) hasta el más reciente. El scraper recorre un
rango de IDs, extrae los campos de cada nota y los guarda en un JSONL
(una noticia por línea). Es reanudable: si se interrumpe, al volver a
ejecutarlo se saltan los IDs ya descargados.

Uso:
    python scraper_unison.py                         # todo el archivo (1 .. último ID)
    python scraper_unison.py --inicio 38000          # desde un ID hasta el último
    python scraper_unison.py --ids 1 5000 39023      # IDs puntuales (pruebas)
    python scraper_unison.py --exportar              # JSONL -> CSV
"""

from __future__ import annotations

import argparse
import codecs
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.retry import Retry

URL_BASE = "https://www.unison.mx"
URL_NOTA = URL_BASE + "/nota/?idnoti={}"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "PLN-Maestria-scraper/1.0 (proyecto academico)"
)
SALIDA_DEFAULT = Path("data/raw/noticias_unison.jsonl")

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
RE_FECHA = re.compile(r"(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})", re.I)


# --- Codificación -----------------------------------------------------------
# La plantilla del sitio es UTF-8, pero las notas antiguas (~2002-2010) están
# guardadas en Windows-1252. Decodificamos como UTF-8 y, para los bytes que no
# son UTF-8 válido, caemos a cp1252 (latin-1 para los 5 bytes que cp1252 no define).
def _fallback_cp1252(err: UnicodeDecodeError):
    malos = err.object[err.start:err.end]
    texto = "".join(
        bytes([b]).decode("cp1252", errors="ignore") or bytes([b]).decode("latin-1")
        for b in malos
    )
    return texto, err.end


codecs.register_error("cp1252_fallback", _fallback_cp1252)


def decodificar(contenido: bytes) -> str:
    return contenido.decode("utf-8", errors="cp1252_fallback")


# --- HTTP -------------------------------------------------------------------
_local = threading.local()


def sesion() -> requests.Session:
    """Una sesión por hilo, con reintentos y backoff ante errores del servidor."""
    if not hasattr(_local, "s"):
        s = requests.Session()
        s.headers["User-Agent"] = USER_AGENT
        reintentos = Retry(
            total=5, backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
        )
        s.mount("https://", HTTPAdapter(max_retries=reintentos))
        _local.s = s
    return _local.s


def ultimo_id() -> int:
    """El ID más reciente aparece en la portada (bloque de noticias)."""
    html = decodificar(sesion().get(URL_BASE + "/", timeout=30).content)
    ids = [int(x) for x in re.findall(r"idnoti=(\d+)", html)]
    if not ids:
        raise RuntimeError("No se encontraron noticias en la portada")
    return max(ids)


# --- Parseo -----------------------------------------------------------------
def parsear_fecha(texto: str) -> str | None:
    m = RE_FECHA.search(texto or "")
    if not m:
        return None
    dia, mes, anio = m.groups()
    mes_num = MESES.get(mes.lower())
    if not mes_num:
        return None
    try:
        return date(int(anio), mes_num, int(dia)).isoformat()
    except ValueError:
        return None


def parece_autor(linea: str) -> bool:
    """Las notas recientes (~2018+) incluyen el nombre del reportero en su propia
    línea (p.ej. 'Paula Trespalacios Argain'). Heurística: línea corta, sin dígitos
    ni puntuación de oración, y con palabras capitalizadas."""
    palabras = linea.split()
    if not (2 <= len(palabras) <= 6) or len(linea) > 60:
        return False
    if re.search(r"[\d.,;:!?¡¿“”\"()]", linea):
        return False
    conectores = {"de", "del", "la", "las", "los", "y", "e"}
    return all(p[0].isupper() or p.lower() in conectores for p in palabras)


def parsear_nota(id_nota: int, html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    registro = {
        "id": id_nota,
        "url": URL_NOTA.format(id_nota),
        "estado": "ok",
    }

    h1 = soup.select_one("article h1.page-entry-title")
    contenido = soup.select_one("article div.entry-content")
    titulo = h1.get_text(" ", strip=True) if h1 else ""
    if not titulo or contenido is None:
        # El sitio responde 200 con la plantilla vacía para IDs inexistentes.
        registro["estado"] = "vacia"
        return registro

    p_fecha = contenido.find("p")
    fecha_txt = p_fecha.get_text(" ", strip=True) if p_fecha else ""

    cuerpo = contenido.select_one('div[align="justify"]') or contenido
    img = cuerpo.find("img")
    imagen = img.get("src") if img else None
    if imagen and imagen.rstrip("/").endswith("img-gde"):
        imagen = None  # notas sin foto apuntan al directorio vacío

    for br in cuerpo.find_all("br"):
        br.replace_with("\n")
    lineas = [re.sub(r"\s+", " ", l).strip() for l in cuerpo.get_text().split("\n")]
    lineas = [l for l in lineas if l]

    # El autor suele ir en la primera línea, aunque a veces lo precede un sumario.
    autor = None
    for i in range(min(2, len(lineas) - 1)):
        if parece_autor(lineas[i]):
            autor = lineas.pop(i)
            break

    texto = "\n".join(lineas)
    registro.update({
        "titulo": titulo,
        "fecha_texto": fecha_txt,
        "fecha": parsear_fecha(fecha_txt),
        "autor": autor,
        "texto": texto,
        "n_parrafos": len(lineas),
        "n_palabras": len(texto.split()),
        "imagen": imagen,
    })
    return registro


def descargar_nota(id_nota: int, pausa: float) -> dict:
    try:
        r = sesion().get(URL_NOTA.format(id_nota), timeout=60)
        r.raise_for_status()
        registro = parsear_nota(id_nota, decodificar(r.content))
    except Exception as e:  # se registra para reintentar en la siguiente corrida
        registro = {"id": id_nota, "url": URL_NOTA.format(id_nota),
                    "estado": "error", "error": f"{type(e).__name__}: {e}"}
    registro["descargado"] = datetime.now().isoformat(timespec="seconds")
    time.sleep(pausa)
    return registro


# --- Persistencia -----------------------------------------------------------
def leer_jsonl(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def ids_completados(ruta: Path) -> set[int]:
    """IDs ya resueltos (ok o vacía). Los que fallaron se vuelven a intentar."""
    return {r["id"] for r in leer_jsonl(ruta) if r["estado"] in ("ok", "vacia")}


def scrapear(ids: list[int], salida: Path, workers: int, pausa: float) -> None:
    salida.parent.mkdir(parents=True, exist_ok=True)
    hechos = ids_completados(salida)
    pendientes = [i for i in ids if i not in hechos]
    print(f"{len(ids)} IDs en el rango, {len(ids) - len(pendientes)} ya descargados, "
          f"{len(pendientes)} pendientes.")
    if not pendientes:
        return

    conteo = {"ok": 0, "vacia": 0, "error": 0}
    with salida.open("a", encoding="utf-8") as f, \
            ThreadPoolExecutor(max_workers=workers) as pool:
        futuros = [pool.submit(descargar_nota, i, pausa) for i in pendientes]
        barra = tqdm(as_completed(futuros), total=len(futuros), unit="nota")
        for fut in barra:
            reg = fut.result()
            conteo[reg["estado"]] += 1
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
            f.flush()
            barra.set_postfix(conteo)
    print("Terminado:", conteo)


def exportar_csv(entrada: Path) -> Path:
    """Consolida el JSONL (último registro por ID, solo notas 'ok') en un CSV."""
    import pandas as pd

    df = pd.DataFrame(leer_jsonl(entrada))
    df = (df.sort_values("descargado").drop_duplicates("id", keep="last")
            .query("estado == 'ok'").sort_values("id")
            .drop(columns=["estado", "error"], errors="ignore")
            .astype({"n_parrafos": int, "n_palabras": int}))
    ruta_csv = entrada.with_suffix(".csv")
    df.to_csv(ruta_csv, index=False, encoding="utf-8-sig")
    print(f"{len(df)} noticias exportadas a {ruta_csv}")
    return ruta_csv


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inicio", type=int, default=1, help="primer ID (default: 1)")
    ap.add_argument("--fin", type=int, help="último ID (default: el más reciente de la portada)")
    ap.add_argument("--ids", type=int, nargs="+", help="lista explícita de IDs")
    ap.add_argument("--workers", type=int, default=4, help="descargas simultáneas (default: 4)")
    ap.add_argument("--pausa", type=float, default=0.5,
                    help="segundos de espera por hilo entre peticiones (default: 0.5)")
    ap.add_argument("--salida", type=Path, default=SALIDA_DEFAULT)
    ap.add_argument("--exportar", action="store_true", help="solo convertir el JSONL a CSV")
    args = ap.parse_args()

    if args.exportar:
        exportar_csv(args.salida)
        return

    if args.ids:
        ids = sorted(set(args.ids))
    else:
        fin = args.fin or ultimo_id()
        ids = list(range(args.inicio, fin + 1))
    scrapear(ids, args.salida, args.workers, args.pausa)


if __name__ == "__main__":
    main()
