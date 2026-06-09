"""
Cliente Playwright para BandeJA — automatiza login y descarga masiva desde una cola.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    Download,
    Page,
    async_playwright,
)

from .config import BANDEJA_URL
from .downloader import Cola, Estado

# Tiempo máximo esperando que el ZIP se compile y descargue (segundos → ms)
_TIMEOUT_DESCARGA_MS = 180_000


class BandejaClient:
    """Sesión Playwright contra BandeJA. Usar como context manager async."""

    def __init__(self, headless: bool = False, navegador: str = "chromium") -> None:
        self._headless   = headless
        self._navegador  = navegador   # "chromium" o "msedge"
        self._pw         = None
        self._browser:   Optional[Browser]        = None
        self._context:   Optional[BrowserContext] = None
        self.page:       Optional[Page]           = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_):
        await self.close()

    async def start(self) -> None:
        self._pw = await async_playwright().start()
        launcher = self._pw.chromium  # chromium soporta tanto Chromium como Edge
        kwargs = {"headless": self._headless}
        if self._navegador == "msedge":
            kwargs["channel"] = "msedge"
        self._browser = await launcher.launch(**kwargs)
        self._context = await self._browser.new_context(accept_downloads=True)
        self.page = await self._context.new_page()

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    # ── Login ────────────────────────────────────────────────────────────────

    async def login(self, usuario: str, password: str, puesto: str = "") -> None:
        """
        Navega a BandeJA, completa el SSO y selecciona el puesto de trabajo.
        puesto: subcadena del nombre (ej. "ENERGIA"). Vacío → selecciona el primero.
        """
        await self.page.goto(BANDEJA_URL)

        # Formulario SSO (ssoweb.juntadeandalucia.es)
        await self.page.get_by_role("textbox", name="Usuario").fill(usuario)
        await self.page.get_by_role("textbox", name="Contraseña").fill(password)
        await self.page.get_by_role("button", name="Inicio de sesión").click()

        # Diálogo de obligaciones de uso
        await self.page.get_by_role("button", name="Aceptar").click()

        # Selector de puesto (solo aparece cuando hay más de un perfil)
        try:
            await self.page.wait_for_selector("#usuarioSeleccionado", timeout=4000)
            select = self.page.locator("#usuarioSeleccionado")
            if puesto:
                opciones = await select.locator("option").all_text_contents()
                coincidencia = next(
                    (op for op in opciones if puesto.upper() in op.upper()), None
                )
                if coincidencia:
                    await select.select_option(coincidencia)
            await self.page.get_by_role("button", name="Acceder").click()
        except Exception:
            # Un solo perfil: no aparece el selector, ya entramos directamente
            pass

        await self.page.wait_for_url("**/bandejaTrabajo/inicio.action", timeout=15_000)

    # ── Procesado de cola ────────────────────────────────────────────────────

    async def procesar_cola(
        self,
        cola: Cola,
        destino: Path,
        log_fn:  Callable[[str], None] | None = None,
        parar_fn: Callable[[], bool]  | None = None,
    ) -> None:
        """
        Itera sobre los trabajos pendientes de la cola hasta que no queden más
        o parar_fn() devuelva True.
        """
        destino.mkdir(parents=True, exist_ok=True)
        _log   = log_fn   or (lambda _: None)
        _parar = parar_fn or (lambda: False)

        while not _parar():
            trabajo = cola.siguiente_pendiente()
            if trabajo is None:
                break

            codigo = trabajo.codigo
            cola.iniciar(codigo)
            _log(f"Procesando: {codigo}")

            try:
                nombre_zip = await self._procesar_codigo(codigo, destino)
                if nombre_zip:
                    cola.completar(codigo, Estado.OK, zip_filename=nombre_zip)
                    _log(f"OK {codigo} → {nombre_zip}")
                else:
                    cola.completar(
                        codigo, Estado.SIN_DOCUMENTOS, detalle="Sin documentos adjuntos"
                    )
                    _log(f"Sin documentos: {codigo}")
            except Exception as exc:
                cola.completar(codigo, Estado.ERROR, detalle=str(exc))
                _log(f"Error {codigo}: {exc}")
                await self._cerrar_modal_si_abierto()

    # ── Acciones sobre la página ─────────────────────────────────────────────

    async def _procesar_codigo(self, codigo: str, destino: Path) -> Optional[str]:
        """
        Filtra por código, abre el modal, descarga el ZIP y cierra.
        Devuelve el nombre del fichero o None si no hay documentos.
        """
        await self._filtrar_codigo(codigo)
        await self._abrir_modal(codigo)

        # Comprobar si el botón de descarga está presente
        btn_descarga = self.page.locator('a:has-text("Descargar documentos")')
        if await btn_descarga.count() == 0:
            await self._cerrar_modal()
            return None

        nombre = await self._descargar_zip(btn_descarga, destino)
        await self._cerrar_modal()
        return nombre

    async def _filtrar_codigo(self, codigo: str) -> None:
        await self.page.get_by_role("button", name="Borrar filtros").click()
        # Pequeña espera para que el AJAX de borrado se complete
        await self.page.wait_for_timeout(600)
        await self.page.get_by_placeholder("Código...").fill(codigo)
        await self.page.locator("button#filtrar").click()

        # Esperar a que aparezca la celda con el código exacto
        celda = self.page.get_by_role("cell", name=codigo, exact=True)
        try:
            await celda.wait_for(state="visible", timeout=15_000)
        except Exception:
            raise ValueError(f"Código '{codigo}' no encontrado en la bandeja")

    async def _abrir_modal(self, codigo: str) -> None:
        fila = self.page.get_by_role("row", name=codigo)
        await fila.first.dblclick()
        await self.page.wait_for_selector("text=Información detallada", timeout=10_000)

    async def _descargar_zip(self, btn_descarga, destino: Path) -> str:
        async with self.page.expect_download(timeout=_TIMEOUT_DESCARGA_MS) as dl_info:
            await btn_descarga.click()
        download: Download = await dl_info.value
        nombre = download.suggested_filename or f"bandeja_{asyncio.get_event_loop().time():.0f}.zip"
        await download.save_as(destino / nombre)
        return nombre

    async def _cerrar_modal(self) -> None:
        try:
            await self.page.get_by_role("button", name="Cerrar").click(timeout=3_000)
        except Exception:
            pass

    async def _cerrar_modal_si_abierto(self) -> None:
        """Intenta cerrar el modal si quedó abierto tras un error."""
        try:
            if await self.page.locator("text=Información detallada").count() > 0:
                await self._cerrar_modal()
        except Exception:
            pass
