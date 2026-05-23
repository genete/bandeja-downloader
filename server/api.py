"""
API HTTP — consumida por la extensión Chrome.
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.post("/api/result")
async def post_result(payload: ResultadoPayload):
    """La extensión reporta el resultado de un trabajo."""
    if not _cola:
        return {"ok": False, "error": "Cola no inicializada"}
    estado = Estado.OK if payload.status == "ok" else Estado.ERROR
    _cola.completar(payload.codigo, estado, payload.detail, payload.zip_filename)
    return {"ok": True}


