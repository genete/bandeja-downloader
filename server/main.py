"""
Punto de entrada — TUI con Textual + servidor FastAPI embebido.

Uso:
    python -m server.main                      # carga data/pending.csv si existe
    python -m server.main --csv ruta/lista.csv # carga CSV indicado
"""
from __future__ import annotations

import argparse
import threading
from pathlib import Path

import uvicorn
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Label, Static
from textual.containers import Vertical

from .api import app as fastapi_app, inyectar_cola, set_pausado
from .config import PENDING_CSV, SERVER_HOST, SERVER_PORT
from .downloader import Cola, Estado

# ── Colores por estado ───────────────────────────────────────────────────────

COLORES = {
    Estado.PENDIENTE: "white",
    Estado.EN_CURSO:  "yellow",
    Estado.OK:        "green",
    Estado.ERROR:     "red",
}

ICONOS = {
    Estado.PENDIENTE: "⏳",
    Estado.EN_CURSO:  "🔄",
    Estado.OK:        "✅",
    Estado.ERROR:     "❌",
}


# ── Aplicación Textual ───────────────────────────────────────────────────────

class BandeJAApp(App):
    """TUI para BandeJA Downloader."""

    TITLE = "BandeJA Downloader"
    CSS = """
    Screen { background: $surface; }

    #barra-stats {
        height: 3;
        background: $panel;
        padding: 0 2;
        content-align: left middle;
        color: $text;
    }

    DataTable { height: 1fr; }

    #pie {
        height: 1;
        background: $panel-darken-1;
        padding: 0 2;
        color: $text-muted;
        content-align: left middle;
    }
    """

    BINDINGS = [
        Binding("q", "quit",        "Salir"),
        Binding("r", "recargar",    "Recargar CSV"),
        Binding("p", "pausar",      "Pausar/Reanudar"),
    ]

    def __init__(self, csv_path: Path) -> None:
        super().__init__()
        self.csv_path = csv_path
        self.cola = Cola()
        self.pausado = False
        inyectar_cola(self.cola)

    # ── Composición UI ───────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Cargando…", id="barra-stats")
        yield DataTable(id="tabla", cursor_type="row")
        yield Static("", id="pie")
        yield Footer()

    def on_mount(self) -> None:
        # Configurar columnas
        tabla = self.query_one("#tabla", DataTable)
        tabla.add_columns("", "Código", "Estado", "Detalle", "Hora")

        # Cargar CSV inicial
        self._cargar_csv()

        # Arrancar servidor FastAPI en hilo daemon
        self._arrancar_servidor()

        # Actualizar UI cada 2 segundos
        self.set_interval(2, self._refrescar)

    # ── Acciones de teclado ──────────────────────────────────────────────────

    def action_recargar(self) -> None:
        n = self._cargar_csv()
        self.notify(f"CSV recargado: {n} nuevos trabajos añadidos")

    def action_pausar(self) -> None:
        self.pausado = not self.pausado
        set_pausado(self.pausado)           # propaga al API
        estado = "PAUSADO ⏸" if self.pausado else "ACTIVO ▶"
        self.notify(f"Estado: {estado}")
        self._actualizar_pie()

    # ── Lógica interna ───────────────────────────────────────────────────────

    def _cargar_csv(self) -> int:
        if not self.csv_path.exists():
            self.notify(f"CSV no encontrado: {self.csv_path}", severity="warning")
            return 0
        n = self.cola.cargar_csv(self.csv_path)
        self._refrescar()
        return n

    def _arrancar_servidor(self) -> None:
        config = uvicorn.Config(
            fastapi_app,
            host=SERVER_HOST,
            port=SERVER_PORT,
            log_level="error",
        )
        server = uvicorn.Server(config)
        hilo = threading.Thread(target=server.run, daemon=True, name="uvicorn")
        hilo.start()

    def _refrescar(self) -> None:
        """Actualiza tabla y barra de estadísticas."""
        tabla = self.query_one("#tabla", DataTable)
        tabla.clear()

        for t in self.cola.trabajos:
            hora        = t.timestamp.strftime("%H:%M:%S") if t.timestamp else ""
            detalle_txt = t.zip_filename if t.zip_filename else t.detalle[:60]
            tabla.add_row(
                ICONOS[t.estado],
                t.codigo,
                t.estado.value,
                detalle_txt,
                hora,
                key=t.codigo,
            )

        s = self.cola.stats
        stats = self.query_one("#barra-stats", Static)
        stats.update(
            f"Total: {s['total']}  │  "
            f"Pendiente: {s['pendiente']}  │  "
            f"En curso: {s['en_curso']}  │  "
            f"✅ OK: {s['ok']}  │  "
            f"❌ Error: {s['error']}"
        )
        self._actualizar_pie()

    def _actualizar_pie(self) -> None:
        pie = self.query_one("#pie", Static)
        pausado_txt = "  ⏸ PAUSADO" if self.pausado else ""
        pie.update(f"Servidor: http://{SERVER_HOST}:{SERVER_PORT}{pausado_txt}")


# ── Entrada principal ────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="BandeJA Downloader")
    parser.add_argument(
        "--csv",
        type=Path,
        default=PENDING_CSV,
        help=f"Ruta al CSV de códigos (defecto: {PENDING_CSV})",
    )
    args = parser.parse_args()

    app = BandeJAApp(csv_path=args.csv)
    app.run()


if __name__ == "__main__":
    main()
