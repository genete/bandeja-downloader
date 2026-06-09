"""
Punto de entrada — formulario Tkinter persistente + TUI Textual para progreso.

Flujo:
  formulario.mostrar() → oculta ventana → TUI Textual (Playwright en hilo)
  → cola terminada → TUI se cierra → formulario.mostrar() de nuevo
  → usuario cierra el formulario → fin
"""
from __future__ import annotations

import asyncio
import threading

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Static

from .downloader import Cola, Estado, logger as dl_logger
from .gui import FormularioBandeJA

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
        Binding("q", "quit",   "Salir al formulario"),
        Binding("p", "pausar", "Pausar/Reanudar"),
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
            # Cola terminada — cerrar la TUI para volver al formulario
            self.call_from_thread(self.exit)

        threading.Thread(target=run, daemon=True, name="playwright").start()

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
    formulario = FormularioBandeJA()
    while True:
        config = formulario.mostrar()
        if config is None:
            break
        BandeJAApp(config).run()
    formulario.destroy()


if __name__ == "__main__":
    main()
