"""
API HTTP — consumida por la extensión Chrome.
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from .downloader import Cola, Estado

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


@app.post("/api/result")
async def post_result(payload: ResultadoPayload):
    """La extensión reporta el resultado de un trabajo."""
    if not _cola:
        return {"ok": False, "error": "Cola no inicializada"}
    _map = {"ok": Estado.OK, "sin_documentos": Estado.SIN_DOCUMENTOS}
    estado = _map.get(payload.status, Estado.ERROR)
    _cola.completar(payload.codigo, estado, payload.detail, payload.zip_filename)
    return {"ok": True}


