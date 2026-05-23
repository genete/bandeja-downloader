"""
Gestión de la cola de trabajos de descarga.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class Estado(str, Enum):
    PENDIENTE  = "pendiente"
    EN_CURSO   = "en_curso"
    OK         = "ok"
    ERROR      = "error"


@dataclass
class Trabajo:
    codigo:    str
    estado:    Estado    = Estado.PENDIENTE
    detalle:   str       = ""
    timestamp: Optional[datetime] = None


class Cola:
    """Cola de trabajos de descarga. Hilo-segura para lecturas concurrentes."""

    def __init__(self) -> None:
        self.trabajos: list[Trabajo] = []

    # ── Carga ────────────────────────────────────────────────────────────────

    def cargar_csv(self, ruta: Path) -> int:
        """
        Carga códigos desde un CSV (primera columna).
        Ignora duplicados y líneas vacías.
        Devuelve el número de trabajos nuevos añadidos.
        """
        codigos_existentes = {t.codigo for t in self.trabajos}
        nuevos = 0
        with open(ruta, newline="", encoding="utf-8-sig") as f:
            for fila in csv.reader(f):
                if not fila:
                    continue
                codigo = fila[0].strip()
                if codigo and codigo not in codigos_existentes:
                    self.trabajos.append(Trabajo(codigo=codigo))
                    codigos_existentes.add(codigo)
                    nuevos += 1
        return nuevos

    # ── Control de trabajos ──────────────────────────────────────────────────

    def siguiente_pendiente(self) -> Optional[Trabajo]:
        """Devuelve el siguiente trabajo pendiente sin modificar su estado."""
        return next((t for t in self.trabajos if t.estado == Estado.PENDIENTE), None)

    def iniciar(self, codigo: str) -> Optional[Trabajo]:
        """Marca un trabajo como EN_CURSO."""
        trabajo = self._buscar(codigo, Estado.PENDIENTE)
        if trabajo:
            trabajo.estado = Estado.EN_CURSO
        return trabajo

    def completar(self, codigo: str, estado: Estado, detalle: str = "") -> None:
        """Registra el resultado de un trabajo (OK o ERROR)."""
        trabajo = next((t for t in self.trabajos if t.codigo == codigo), None)
        if trabajo:
            trabajo.estado    = estado
            trabajo.detalle   = detalle
            trabajo.timestamp = datetime.now()

    # ── Estadísticas ─────────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            "total":     len(self.trabajos),
            "pendiente": self._contar(Estado.PENDIENTE),
            "en_curso":  self._contar(Estado.EN_CURSO),
            "ok":        self._contar(Estado.OK),
            "error":     self._contar(Estado.ERROR),
        }

    # ── Helpers privados ─────────────────────────────────────────────────────

    def _buscar(self, codigo: str, estado: Estado) -> Optional[Trabajo]:
        return next(
            (t for t in self.trabajos if t.codigo == codigo and t.estado == estado),
            None
        )

    def _contar(self, estado: Estado) -> int:
        return sum(1 for t in self.trabajos if t.estado == estado)
