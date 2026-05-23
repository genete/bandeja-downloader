"""
Gestión de la cola de trabajos de descarga.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import threading
from . import notifier
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# Patrón de código BandeJA: EXT/2026/0000000003004075
_CODIGO_RE = re.compile(r'^(EXT|INT)/\d{4}/\d+$')

from .config import BASE_DIR

# Log junto al ejecutable (o en la raíz del proyecto en desarrollo)
_LOG_PATH = BASE_DIR / "bandeja_downloader.log"
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
_TIMEOUT_EN_CURSO_SEG = 2 * 60  # 2 minutos


@dataclass
class Trabajo:
    codigo:         str
    estado:         Estado    = Estado.PENDIENTE
    detalle:        str       = ""
    zip_filename:   str       = ""
    timestamp:      Optional[datetime] = None
    started_at:     Optional[datetime] = None  # momento en que pasó a EN_CURSO
    fila_original:  list      = field(default_factory=list)  # fila completa del CSV


class Cola:
    """Cola de trabajos de descarga. Hilo-segura para lecturas concurrentes."""

    def __init__(self) -> None:
        self.trabajos:       list[Trabajo] = []
        self.cabecera:       list[str]     = []  # fila de cabecera del CSV original
        self._ultimo_export: str           = ""  # snapshot del CSV antes de vaciar

    # ── Carga ────────────────────────────────────────────────────────────────

    def cargar_csv(self, ruta: Path) -> int:
        """Carga códigos desde un fichero CSV (formato simple o exportación BandeJA)."""
        # Intentar UTF-8-BOM primero; si falla, Latin-1 (frecuente en exportaciones Windows)
        for enc in ("utf-8-sig", "latin-1"):
            try:
                with open(ruta, newline="", encoding=enc) as f:
                    return self._cargar_reader(csv.reader(f))
            except UnicodeDecodeError:
                continue
        return 0

    def cargar_texto_csv(self, texto: str) -> int:
        """Carga códigos desde el contenido de un CSV ya leído como texto."""
        self._ultimo_export = ""  # nuevo lote → invalidar snapshot anterior
        reader = csv.reader(io.StringIO(texto))
        return self._cargar_reader(reader)

    def _cargar_reader(self, reader) -> int:
        """
        Extrae códigos de un csv.reader guardando la fila completa para exportación.
        Detecta automáticamente el formato:
          - Exportación BandeJA: 7 columnas, código en col 1
          - Simple: una columna con el código directamente
        """
        codigos_existentes = {t.codigo for t in self.trabajos}
        nuevos   = 0
        col      = None   # índice de columna del código

        for fila in reader:
            if not fila:
                continue

            # Primera fila: detectar columna y si es cabecera guardarla
            if col is None:
                col = self._detectar_columna(fila)
                if not _CODIGO_RE.match(fila[col].strip()):
                    # Es cabecera — guardarla solo si aún no hay una
                    if not self.cabecera:
                        self.cabecera = list(fila)
                    continue

            if col >= len(fila):
                continue

            codigo = fila[col].strip()
            if codigo in codigos_existentes:
                continue
            if _CODIGO_RE.match(codigo):
                self.trabajos.append(Trabajo(codigo=codigo, fila_original=list(fila)))
                codigos_existentes.add(codigo)
                nuevos += 1
            elif codigo:
                # Código inválido: aparece como error en la TUI y en el CSV exportado
                self.trabajos.append(Trabajo(
                    codigo=codigo,
                    estado=Estado.ERROR,
                    detalle="Código no reconocido",
                    fila_original=list(fila),
                ))
                codigos_existentes.add(codigo)

        return nuevos

    @staticmethod
    def _detectar_columna(fila: list[str]) -> int:
        """Devuelve el índice de la columna que contiene el código BandeJA."""
        for i, celda in enumerate(fila):
            if _CODIGO_RE.match(celda.strip()):
                return i
        # Sin coincidencia directa (fila de cabecera): usar col 1 si hay ≥2 columnas, si no col 0
        return 1 if len(fila) > 1 else 0

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
            if self._contar(Estado.PENDIENTE) == 0 and self._contar(Estado.EN_CURSO) == 0:
                self._cola_completada()

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

    def _cola_completada(self) -> None:
        ok      = self._contar(Estado.OK)
        error   = self._contar(Estado.ERROR)
        sin_doc = self._contar(Estado.SIN_DOCUMENTOS)
        total   = len(self.trabajos)
        logger.info(
            "COLA COMPLETADA — Total: %d | OK: %d | Error: %d | Sin documentos: %d",
            total, ok, error, sin_doc
        )
        notifier.notificar(
            "✅ Cola completada",
            f"Total: {total}  ✓{ok}  ✗{error}  📭{sin_doc}\nCargue un nuevo CSV para continuar"
        )
        # Vaciar la cola tras 10s para que la TUI muestre el estado final brevemente
        threading.Timer(10, self._vaciar).start()

    def exportar_csv(self) -> str:
        """
        Devuelve el CSV con resultados.
        Si la cola ya fue vaciada, devuelve el último snapshot guardado.
        """
        if not self.trabajos:
            return self._ultimo_export

        out = io.StringIO()
        writer = csv.writer(out)
        if self.cabecera:
            writer.writerow(self.cabecera + ["Resultado", "Fichero ZIP", "Detalle"])
        else:
            writer.writerow(["Código", "Resultado", "Fichero ZIP", "Detalle"])
        for t in self.trabajos:
            fila = t.fila_original if t.fila_original else [t.codigo]
            writer.writerow(fila + [t.estado.value, t.zip_filename, t.detalle])
        return out.getvalue()

    def _vaciar(self) -> None:
        # Guardar snapshot antes de limpiar para que el export siga disponible
        self._ultimo_export = self.exportar_csv()
        self.trabajos.clear()
        self.cabecera.clear()
        logger.info("Cola vaciada — lista para nuevo CSV")

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
