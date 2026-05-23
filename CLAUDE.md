# BandeJA Downloader — CLAUDE.md

## Descripción del proyecto
Sistema para automatizar descargas desde la aplicación BandeJA.  
Flujo: lista de identificadores de comunicaciones → extensión Chrome → descarga al directorio destino.

## Arquitectura
- **Extensión Chrome**: intercepta y ejecuta descargas dentro del contexto del navegador autenticado en BandeJA.
- **Servidor HTTP local (Python)**: recibe órdenes, gestiona la cola de descargas y expone una interfaz interactiva (TUI o web local).
- **Comunicación**: extensión Chrome ↔ servidor Python via HTTP (localhost).

## Estructura del proyecto
```
BANDEJADL/
├── extension/          # Extensión Chrome (Manifest V3)
│   ├── manifest.json
│   ├── background.js   # Service worker — recibe comandos HTTP y ejecuta descargas
│   └── popup/          # UI opcional de la extensión
├── server/             # Servidor Python
│   ├── main.py         # Punto de entrada con interfaz interactiva (Textual o similar)
│   ├── api.py          # Endpoints HTTP que la extensión consume
│   ├── downloader.py   # Lógica de cola y gestión de descargas
│   └── config.py       # Directorio destino y configuración
├── data/
│   └── pending.csv     # Listado de identificadores pendientes
├── downloads/          # Directorio destino por defecto (gitignored)
├── requirements.txt
└── .claude/
    └── settings.json
```

## Convenciones
- Código comentado en español cuando la lógica no sea obvia.
- Python 3.11+. Preferir `httpx` para cliente HTTP y `FastAPI` para el servidor.
- Interfaz interactiva con `Textual` (TUI en terminal).
- La extensión usa Manifest V3 con service worker.

## Directorio de descarga por defecto
`downloads/` dentro del proyecto. Configurable en `server/config.py`.
