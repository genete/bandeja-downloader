"""
Formulario de configuración — Tkinter.
Recoge credenciales, CSV, carpeta destino y opciones de navegador.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path
from typing import Optional

from .config import PENDING_CSV, DOWNLOADS_DIR


def mostrar_formulario() -> Optional[dict]:
    """
    Muestra el formulario antes de arrancar.
    Devuelve dict de configuración si el usuario pulsa Iniciar, None si cancela.
    """
    resultado: Optional[dict] = None

    root = tk.Tk()
    root.title("BandeJA Downloader")
    root.resizable(False, False)

    frame = ttk.Frame(root, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")

    fila = 0

    # — CSV —
    ttk.Label(frame, text="CSV de BandeJA:").grid(row=fila, column=0, sticky="w", pady=4)
    csv_var = tk.StringVar(value=str(PENDING_CSV))
    ttk.Entry(frame, textvariable=csv_var, width=45).grid(row=fila, column=1, padx=4)
    ttk.Button(
        frame, text="…", width=3,
        command=lambda: csv_var.set(
            filedialog.askopenfilename(
                filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
            ) or csv_var.get()
        ),
    ).grid(row=fila, column=2)
    fila += 1

    # — Carpeta destino —
    ttk.Label(frame, text="Carpeta destino:").grid(row=fila, column=0, sticky="w", pady=4)
    destino_var = tk.StringVar(value=str(DOWNLOADS_DIR))
    ttk.Entry(frame, textvariable=destino_var, width=45).grid(row=fila, column=1, padx=4)
    ttk.Button(
        frame, text="…", width=3,
        command=lambda: destino_var.set(filedialog.askdirectory() or destino_var.get()),
    ).grid(row=fila, column=2)
    fila += 1

    ttk.Separator(frame).grid(row=fila, column=0, columnspan=3, sticky="ew", pady=8)
    fila += 1

    # — Usuario —
    ttk.Label(frame, text="Usuario BandeJA:").grid(row=fila, column=0, sticky="w", pady=4)
    usuario_var = tk.StringVar()
    ttk.Entry(frame, textvariable=usuario_var, width=45).grid(
        row=fila, column=1, columnspan=2, padx=4
    )
    fila += 1

    # — Contraseña —
    ttk.Label(frame, text="Contraseña:").grid(row=fila, column=0, sticky="w", pady=4)
    password_var = tk.StringVar()
    pw_entry = ttk.Entry(frame, textvariable=password_var, width=45, show="•")
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
    puesto_var = tk.StringVar()
    ttk.Entry(frame, textvariable=puesto_var, width=45).grid(
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
    headless_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        frame, text="Headless (sin ventana de navegador)", variable=headless_var
    ).grid(row=fila, column=0, columnspan=3, sticky="w", pady=2)
    fila += 1

    # — Navegador —
    ttk.Label(frame, text="Navegador:").grid(row=fila, column=0, sticky="w", pady=4)
    navegador_var = tk.StringVar(value="msedge")
    nav_frame = ttk.Frame(frame)
    nav_frame.grid(row=fila, column=1, columnspan=2, sticky="w")
    ttk.Radiobutton(nav_frame, text="Chromium", variable=navegador_var, value="chromium").pack(
        side="left", padx=(0, 12)
    )
    ttk.Radiobutton(nav_frame, text="Edge", variable=navegador_var, value="msedge").pack(
        side="left"
    )
    fila += 1

    # — Mensaje de error —
    error_var = tk.StringVar()
    ttk.Label(frame, textvariable=error_var, foreground="red").grid(
        row=fila, column=0, columnspan=3, pady=4
    )
    fila += 1

    # — Botones —
    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=fila, column=0, columnspan=3, pady=8)

    def iniciar():
        nonlocal resultado
        csv_path = Path(csv_var.get())
        if not csv_var.get() or not csv_path.exists():
            error_var.set("El fichero CSV no existe.")
            return
        if not usuario_var.get().strip():
            error_var.set("Introduce el usuario.")
            return
        if not password_var.get():
            error_var.set("Introduce la contraseña.")
            return
        resultado = {
            "csv":       csv_path,
            "destino":   Path(destino_var.get()),
            "usuario":   usuario_var.get().strip(),
            "password":  password_var.get(),
            "puesto":    puesto_var.get().strip(),
            "headless":  headless_var.get(),
            "navegador": navegador_var.get(),
        }
        root.destroy()

    ttk.Button(btn_frame, text="Iniciar", command=iniciar).pack(side="left", padx=8)
    ttk.Button(btn_frame, text="Cancelar", command=root.destroy).pack(side="left")

    root.mainloop()
    return resultado
