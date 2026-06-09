"""
Formulario de configuración — Tkinter.
Vive durante toda la sesión: se oculta mientras corre la TUI y reaparece al terminar.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from typing import Optional

from .config import PENDING_CSV, DOWNLOADS_DIR


class FormularioBandeJA:
    """Ventana de configuración reutilizable entre lotes."""

    def __init__(self) -> None:
        self._config: Optional[dict] = None
        self._destruido = False

        self._root = tk.Tk()
        self._root.title("BandeJA Downloader")
        self._root.resizable(False, False)
        self._root.protocol("WM_DELETE_WINDOW", self._on_cerrar)

        self._error_var = tk.StringVar()
        self._csv_var      = tk.StringVar(value=str(PENDING_CSV))
        self._destino_var  = tk.StringVar(value=str(DOWNLOADS_DIR))
        self._usuario_var  = tk.StringVar()
        self._password_var = tk.StringVar()
        self._puesto_var   = tk.StringVar()
        self._headless_var  = tk.BooleanVar(value=False)
        self._finalizar_var = tk.BooleanVar(value=False)
        self._navegador_var = tk.StringVar(value="msedge")

        self._build()

    # ── Ciclo de vida ────────────────────────────────────────────────────────

    def mostrar(self) -> Optional[dict]:
        """
        Muestra (o re-muestra) el formulario y bloquea hasta que el usuario
        pulse Iniciar o cierre la ventana.
        Devuelve el dict de configuración, o None si se cerró.
        """
        if self._destruido:
            return None
        self._config = None
        self._error_var.set("")
        self._root.deiconify()
        self._root.mainloop()
        return self._config

    def destroy(self) -> None:
        if not self._destruido:
            self._destruido = True
            try:
                self._root.destroy()
            except Exception:
                pass

    # ── Construcción UI ──────────────────────────────────────────────────────

    def _build(self) -> None:
        frame = ttk.Frame(self._root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        fila = 0

        # — CSV —
        ttk.Label(frame, text="CSV de BandeJA:").grid(row=fila, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self._csv_var, width=45).grid(row=fila, column=1, padx=4)
        ttk.Button(
            frame, text="…", width=3,
            command=lambda: self._csv_var.set(
                filedialog.askopenfilename(
                    filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
                ) or self._csv_var.get()
            ),
        ).grid(row=fila, column=2)
        fila += 1

        # — Carpeta destino —
        ttk.Label(frame, text="Carpeta destino:").grid(row=fila, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self._destino_var, width=45).grid(row=fila, column=1, padx=4)
        ttk.Button(
            frame, text="…", width=3,
            command=lambda: self._destino_var.set(
                filedialog.askdirectory() or self._destino_var.get()
            ),
        ).grid(row=fila, column=2)
        fila += 1

        ttk.Separator(frame).grid(row=fila, column=0, columnspan=3, sticky="ew", pady=8)
        fila += 1

        # — Usuario —
        ttk.Label(frame, text="Usuario BandeJA:").grid(row=fila, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self._usuario_var, width=45).grid(
            row=fila, column=1, columnspan=2, padx=4
        )
        fila += 1

        # — Contraseña —
        ttk.Label(frame, text="Contraseña:").grid(row=fila, column=0, sticky="w", pady=4)
        pw_entry = ttk.Entry(frame, textvariable=self._password_var, width=45, show="•")
        pw_entry.grid(row=fila, column=1, padx=4)
        mostrar_pw = tk.BooleanVar(value=False)

        def toggle_pw():
            pw_entry.config(show="" if mostrar_pw.get() else "•")

        ttk.Checkbutton(frame, text="👁", variable=mostrar_pw, command=toggle_pw).grid(
            row=fila, column=2
        )
        fila += 1

        # — Puesto de trabajo —
        ttk.Label(frame, text="Puesto (parte del nombre):").grid(
            row=fila, column=0, sticky="w", pady=4
        )
        ttk.Entry(frame, textvariable=self._puesto_var, width=45).grid(
            row=fila, column=1, columnspan=2, padx=4
        )
        fila += 1
        ttk.Label(frame, text="Dejar vacío si solo tienes un perfil", foreground="gray").grid(
            row=fila, column=1, sticky="w", padx=4
        )
        fila += 1

        ttk.Separator(frame).grid(row=fila, column=0, columnspan=3, sticky="ew", pady=8)
        fila += 1

        # — Headless —
        ttk.Checkbutton(
            frame, text="Headless (sin ventana de navegador)", variable=self._headless_var
        ).grid(row=fila, column=0, columnspan=3, sticky="w", pady=2)
        fila += 1

        # — Finalizar —
        ttk.Checkbutton(
            frame, text="Finalizar comunicación tras descargar", variable=self._finalizar_var
        ).grid(row=fila, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Label(frame, text="⚠ deja trazas", foreground="darkorange").grid(
            row=fila, column=2, sticky="w"
        )
        fila += 1

        # — Navegador —
        ttk.Label(frame, text="Navegador:").grid(row=fila, column=0, sticky="w", pady=4)
        nav_frame = ttk.Frame(frame)
        nav_frame.grid(row=fila, column=1, columnspan=2, sticky="w")
        ttk.Radiobutton(nav_frame, text="Edge", variable=self._navegador_var, value="msedge").pack(
            side="left", padx=(0, 12)
        )
        ttk.Radiobutton(
            nav_frame, text="Chromium", variable=self._navegador_var, value="chromium"
        ).pack(side="left")
        fila += 1

        # — Error —
        ttk.Label(frame, textvariable=self._error_var, foreground="red").grid(
            row=fila, column=0, columnspan=3, pady=4
        )
        fila += 1

        # — Botones —
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=fila, column=0, columnspan=3, pady=8)
        ttk.Button(btn_frame, text="Iniciar", command=self._on_iniciar).pack(side="left", padx=8)
        ttk.Button(btn_frame, text="Cerrar", command=self._on_cerrar).pack(side="left")

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _on_iniciar(self) -> None:
        csv_path = Path(self._csv_var.get())
        if not self._csv_var.get() or not csv_path.exists():
            self._error_var.set("El fichero CSV no existe.")
            return
        if not self._usuario_var.get().strip():
            self._error_var.set("Introduce el usuario.")
            return
        if not self._password_var.get():
            self._error_var.set("Introduce la contraseña.")
            return

        self._config = {
            "csv":       csv_path,
            "destino":   Path(self._destino_var.get()),
            "usuario":   self._usuario_var.get().strip(),
            "password":  self._password_var.get(),
            "puesto":    self._puesto_var.get().strip(),
            "headless":   self._headless_var.get(),
            "finalizar":  self._finalizar_var.get(),
            "navegador":  self._navegador_var.get(),
        }
        self._root.withdraw()
        self._root.quit()

    def _on_cerrar(self) -> None:
        self._destruido = True
        self._config = None
        self._root.quit()
        self._root.destroy()
