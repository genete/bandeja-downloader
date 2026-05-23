"""
Gestión de la cola de trabajos de descarga.
"""
from __future__ import annotations

import csv
import logging
from . import notifier
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# Log en la raíz del proyecto (D:/BANDEJADL/bandeja_downloader.log)
_LOG_PATH = Path(__file__).parent.parent / "bandeja_downloader.log"
_handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logger = logging.getLogger("bandeja")
logger.setLevel(logging.INFO)
logger.addHandler(_handler)
logger.propagate = False


class Estado(str, Enum):
    PENDIENTE      = "pendiente"
    EN_CURSO       = "en_curso"
    OK             = "ok"
    ERROR          = "error"
    SIN_DOCUMENTOS = "sin_documentos"


# Tiempo máximo que un trabajo puede estar EN_CURSO antes de considerarse atascado
_TIMEOUT_EN_CURSO_SEG = 5 * 60  # 5 minutos


@dataclass
class Trabajo:
    codigo:       str
    estado:       Estado    = Estado.PENDIENTE
    detalle:      str       = ""
    zip_filename: str       = ""
    timestamp:    Optional[datetime] = None
    started_at:   Optional[datetime] = None  # momento en que pasó a EN_CURSO


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
        """
        Devuelve el siguiente trabajo pendiente sin modificar su estado.
        Antes resetea los trabajos EN_CURSO atascados (service worker reiniciado
        a mitad de trabajo) para que puedan reintentarse.
        """
        self._resetear_atascados()
        return next((t for t in self.trabajos if t.estado == Estado.PENDIENTE), None)

    def iniciar(self, codigo: str) -> Optional[Trabajo]:
        """Marca un trabajo como EN_CURSO y registra el momento de inicio."""
        trabajo = self._buscar(codigo, Estado.PENDIENTE)
        if trabajo:
            trabajo.estado     = Estado.EN_CURSO
            trabajo.started_at = datetime.now()
        return trabajo

    def completar(self, codigo: str, estado: Estado, detalle: str = "", zip_filename: str = "") -> None:
        """Registra el resultado de un trabajo (OK o ERROR) y lo vuelca al log."""
        trabajo = next((t for t in self.trabajos if t.codigo == codigo), None)
        if trabajo:
            trabajo.estado       = estado
            trabajo.detalle      = detalle
            trabajo.zip_filename = zip_filename
            trabajo.timestamp    = datetime.now()
            logger.info("%s | %s | %s | %s", codigo, estado.value, zip_filename, detalle)
            self._notificar(codigo, estado, detalle)

    def _notificar(self, codigo: str, estado: Estado, detalle: str) -> None:
        pendientes = self._contar(Estado.PENDIENTE)
        en_curso   = self._contar(Estado.EN_CURSO)
        restantes  = pendientes + en_curso

        if estado == Estado.OK:
            titulo  = f"✓ Descargado"
            mensaje = f"{codigo}\nQuedan {restantes}"
        elif estado == Estado.SIN_DOCUMENTOS:
            titulo  = f"— Sin documentos"
            mensaje = f"{codigo}\nQuedan {restantes}"
        else:
            titulo  = f"✗ Error"
            mensaje = f"{codigo}\n{detalle[:80] if detalle else ''}"

        notifier.notificar(titulo, mensaje)

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

    def _resetear_atascados(self) -> None:
        """Devuelve a PENDIENTE los trabajos EN_CURSO que superan el timeout."""
        ahora = datetime.now()
        for t in self.trabajos:
            if t.estado == Estado.EN_CURSO and t.started_at:
                segundos = (ahora - t.started_at).total_seconds()
                if segundos > _TIMEOUT_EN_CURSO_SEG:
                    logger.info("%s | reset_atascado | llevaba %.0fs EN_CURSO", t.codigo, segundos)
                    t.estado     = Estado.PENDIENTE
                    t.started_at = None

    def _buscar(self, codigo: str, estado: Estado) -> Optional[Trabajo]:
        return next(
            (t for t in self.trabajos if t.codigo == codigo and t.estado == estado),
            None
        )

    def _contar(self, estado: Estado) -> int:
        return sum(1 for t in self.trabajos if t.estado == estado)
