"""
Punto de entrada — formulario Tkinter para configuración + TUI Textual para progreso.
"""
from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Static

from .config import PENDING_CSV
from .downloader import Cola, Estado, logger as dl_logger
from .gui import mostrar_formulario

ICONOS = {
    Estado.PENDIENTE:      "⏳",
    Estado.EN_CURSO:       "🔄",
    Estado.OK:             "✅",
    Estado.ERROR:          "❌",
    Estado.SIN_DOCUMENTOS: "📭",
}


class BandeJAApp(App):
    """TUI de progreso — monitoriza la cola mientras Playwright descarga en segundo plano."""

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
        Binding("q", "quit",       "Salir"),
        Binding("p", "pausar",     "Pausar/Reanudar"),
        Binding("n", "nuevo_lote", "Nuevo lote"),
    ]

    def __init__(self, config: dict) -> None:
        super().__init__()
        self.config  = config
        self.cola    = Cola()
        self.pausado = False

    # ── Composición ──────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Iniciando…", id="barra-stats")
        yield DataTable(id="tabla", cursor_type="row")
        yield Static("", id="pie")
        yield Footer()

    def on_mount(self) -> None:
        dl_logger.info("=" * 60)
        dl_logger.info("NUEVA SESIÓN")
        dl_logger.info("=" * 60)

        tabla = self.query_one("#tabla", DataTable)
        tabla.add_columns("", "Código", "Estado", "Detalle", "Hora")

        n = self.cola.cargar_csv(self.config["csv"])
        self.notify(f"CSV cargado: {n} trabajos")
        self._refrescar()

        self.set_interval(2, self._refrescar)
        self._iniciar_playwright()

    # ── Acciones ─────────────────────────────────────────────────────────────

    def action_pausar(self) -> None:
        self.pausado = not self.pausado
        self.notify("PAUSADO ⏸" if self.pausado else "ACTIVO ▶")
        self._actualizar_pie()

    def action_nuevo_lote(self) -> None:
        self.exit("nuevo_lote")

    # ── Playwright en hilo separado ──────────────────────────────────────────

    def _iniciar_playwright(self) -> None:
        from .bandeja_client import BandejaClient

        config = self.config

        def run():
            async def _async():
                async with BandejaClient(
                    headless=config["headless"],
                    navegador=config["navegador"],
                ) as cliente:
                    await cliente.login(
                        config["usuario"],
                        config["password"],
                        config.get("puesto", ""),
                    )
                    await cliente.procesar_cola(
                        self.cola,
                        config["destino"],
                        log_fn=dl_logger.info,
                        parar_fn=lambda: self.pausado,
                    )

            asyncio.run(_async())
            self.call_from_thread(
                lambda: self.notify(
                    "✅ Cola completada — [n] nuevo lote  [q] salir", timeout=0
                )
            )

        hilo = threading.Thread(target=run, daemon=True, name="playwright")
        hilo.start()

    # ── Refresco de UI ───────────────────────────────────────────────────────

    def _refrescar(self) -> None:
        tabla = self.query_one("#tabla", DataTable)
        tabla.clear()

        for t in self.cola.trabajos:
            hora    = t.timestamp.strftime("%H:%M:%S") if t.timestamp else ""
            detalle = t.zip_filename if t.zip_filename else t.detalle[:60]
            tabla.add_row(
                ICONOS[t.estado],
                t.codigo,
                t.estado.value,
                detalle,
                hora,
                key=t.codigo,
            )

        s = self.cola.stats
        self.query_one("#barra-stats", Static).update(
            f"Total: {s['total']}  │  "
            f"Pendiente: {s['pendiente']}  │  "
            f"En curso: {s['en_curso']}  │  "
            f"✅ OK: {s['ok']}  │  "
            f"❌ Error: {s['error']}"
        )
        self._actualizar_pie()

    def _actualizar_pie(self) -> None:
        pausa = "  ⏸ PAUSADO" if self.pausado else ""
        self.query_one("#pie", Static).update(f"BandeJA Downloader — Playwright{pausa}")


# ── Entrada principal ────────────────────────────────────────────────────────

def main() -> None:
    while True:
        config = mostrar_formulario()
        if config is None:
            break
        resultado = BandeJAApp(config).run()
        if resultado != "nuevo_lote":
            break


if __name__ == "__main__":
    main()
