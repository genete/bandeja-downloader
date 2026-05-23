"""
API HTTP — consumida por la extensión Chrome.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from .downloader import Cola, Estado

logger = logging.getLogger("bandeja")

app = FastAPI(title="BandeJA Downloader API", version="0.1.0")

# CORS amplio: la extensión Chrome accede desde origen chrome-extension://...
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Estado global inyectado desde main.py
_cola: Optional[Cola] = None
_pausado: bool = False
_destino: str = ""

# Ejecutor dedicado para tkinter (debe correr en su propio hilo)
_tk_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tk")


def inyectar_cola(cola: Cola) -> None:
    global _cola
    _cola = cola


def set_pausado(valor: bool) -> None:
    global _pausado
    _pausado = valor


def get_pausado() -> bool:
    return _pausado


# ── Modelos ──────────────────────────────────────────────────────────────────

class ResultadoPayload(BaseModel):
    codigo:       str
    status:       str       # "ok" | "error"
    detail:       str = ""
    zip_filename: str = ""
    timestamp:    Optional[str] = None


class ConfigPayload(BaseModel):
    destino: str = ""


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/next")
async def get_next():
    """La extensión solicita el siguiente trabajo pendiente."""
    if not _cola or _pausado:
        return {}
    trabajo = _cola.siguiente_pendiente()
    if not trabajo:
        return {}
    _cola.iniciar(trabajo.codigo)
    return {"codigo": trabajo.codigo}


@app.get("/api/status")
async def get_status():
    """Estado general de la cola (usado también por el popup de la extensión)."""
    if not _cola:
        return {}
    return {**_cola.stats, "pausado": _pausado}


@app.post("/api/load-csv")
async def load_csv(request: Request):
    """El popup envía el contenido de un CSV de BandeJA para cargar la cola."""
    if not _cola:
        return {"ok": False, "error": "Cola no inicializada"}
    body = await request.body()
    # El popup envía el fichero tal cual; probar UTF-8 y Latin-1
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texto = body.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return {"ok": False, "error": "No se pudo decodificar el CSV"}
    nuevos = _cola.cargar_texto_csv(texto)
    return {"ok": True, "nuevos": nuevos}


@app.get("/api/export-csv")
async def export_csv():
    """Devuelve el CSV con los resultados de la cola actual."""
    if not _cola:
        return Response(content="Cola no inicializada", status_code=503)
    contenido = _cola.exportar_csv()
    return Response(
        content=contenido.encode("utf-8-sig"),  # BOM para que Excel lo abra bien
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resultados_bandeja.csv"},
    )


@app.post("/api/pause-toggle")
async def pause_toggle():
    """Alterna el estado de pausa de la cola."""
    global _pausado
    _pausado = not _pausado
    return {"pausado": _pausado}


@app.get("/api/config")
async def get_config():
    """Devuelve la configuración actual (directorio destino)."""
    return {"destino": _destino}


@app.post("/api/config")
async def post_config(payload: ConfigPayload):
    """Establece el directorio destino para los ZIPs descargados."""
    global _destino
    _destino = payload.destino
    return {"ok": True, "destino": _destino}


@app.post("/api/pick-directory")
async def pick_directory():
    """Abre un diálogo nativo de Windows para elegir el directorio destino."""
    global _destino
    loop = asyncio.get_event_loop()
    ruta = await loop.run_in_executor(_tk_executor, _abrir_dialogo_directorio)
    if ruta:
        _destino = ruta
    return {"destino": _destino}


@app.post("/api/result")
async def post_result(payload: ResultadoPayload):
    """La extensión reporta el resultado de un trabajo."""
    if not _cola:
        return {"ok": False, "error": "Cola no inicializada"}
    _map = {"ok": Estado.OK, "sin_documentos": Estado.SIN_DOCUMENTOS}
    estado = _map.get(payload.status, Estado.ERROR)
    _cola.completar(payload.codigo, estado, payload.detail, payload.zip_filename)

    # Mover el ZIP al directorio destino si está configurado
    if estado == Estado.OK and _destino and payload.zip_filename:
        _mover_zip(payload.zip_filename, _destino)

    return {"ok": True}


# ── Helpers internos ──────────────────────────────────────────────────────────

def _abrir_dialogo_directorio() -> str:
    """Abre el diálogo de selección de carpeta de tkinter (debe correr en hilo propio)."""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    ruta = filedialog.askdirectory(title="Seleccionar carpeta de destino", parent=root)
    root.destroy()
    return ruta or ""


def _mover_zip(zip_path: str, destino: str) -> None:
    """Mueve el ZIP descargado al directorio destino configurado."""
    src = Path(zip_path)
    if not src.exists():
        logger.warning("ZIP no encontrado para mover: %s", zip_path)
        return
    dst_dir = Path(destino)
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    try:
        shutil.move(str(src), str(dst))
        logger.info("ZIP movido: %s → %s", src.name, dst_dir)
    except Exception as exc:
        logger.error("Error al mover ZIP %s: %s", src.name, exc)

