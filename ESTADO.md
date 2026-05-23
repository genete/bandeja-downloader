# Estado del proyecto — BandeJA Downloader

> Actualizado: 2025-05-23

## Qué funciona

- Servidor Python arranca con `python -m server.main`
- TUI Textual muestra la cola, estadísticas y acepta teclas `r` (recargar CSV), `p` (pausar), `q` (salir)
- La pausa (`p`) detiene el polling de la extensión correctamente
- Extensión Chrome cargada en modo desarrollador
- La extensión inyecta el content script automáticamente si la pestaña estaba abierta antes de cargarla
- El paso de borrar filtros y filtrar por código está implementado

## Incertidumbres / pendientes

### 1. Log de actividad ✅ RESUELTO
`bandeja_downloader.log` en la raíz del proyecto.
Formato: `2026-05-23 12:34:56 | EXT/2026/... | ok | fichero.zip | detalle`
Escrito desde `downloader.py::completar()` usando el módulo `logging`.

### 2. Nombre del ZIP en la TUI ✅ RESUELTO
- `background.js::onCreated` guarda `item.filename` en `activeJob.filename`
- `finishJob()` lo pasa a `reportResult()` como `zip_filename`
- `api.py` lo recibe en `ResultadoPayload` y lo pasa a `Cola.completar()`
- `downloader.py::Trabajo` tiene campo `zip_filename`
- TUI muestra `zip_filename` (si existe) o `detalle` en la columna Detalle

### 3. Verificar apertura del modal (PRIORIDAD MEDIA)
`abrirModalInfo()` en `content.js` tiene 3 intentos:
1. Doble clic sobre la fila (confirmado que funciona manualmente)
2. Hover + búsqueda de icono por `title`/`aria-label`/`onclick`
3. Extrae ID interno del onclick y llama `abrirModal()` directamente

En prueba anterior falló con "icono no encontrado". El doble clic debería funcionar.
Si sigue fallando, pedir al usuario que haga hover sobre una fila con BandeJA abierto
y ejecute en consola: `document.querySelector('[title*="nformaci"]')?.outerHTML`

### 4. Verificar selectores del filtro (PRIORIDAD MEDIA)
En `content.js::filtrarPorCodigo()`:
- Campo código: `input[placeholder*="digo"]` — puede no coincidir
- Botón filtrar: busca button con texto "filtrar" — puede tener texto diferente
- Si falla, inspeccionar en DevTools y ajustar

## Arquitectura de comunicación

```
pending.csv → Python server (FastAPI :8000)
                    ↑ polling GET /api/next cada 3s
              Chrome extension (background.js)
                    ↓ chrome.runtime.sendMessage
              content.js (inyectado en BandeJA)
                    ↓ DOM automation
              BandeJA (filtrar → modal → ZIP)
                    ↓ chrome.downloads events
              background.js → POST /api/result
```

## Ficheros clave

| Fichero | Rol |
|---|---|
| `extension/content.js` | Automatización DOM de BandeJA |
| `extension/background.js` | Polling, eventos de descarga Chrome, relay de resultados |
| `server/main.py` | TUI Textual, arranca servidor |
| `server/api.py` | Endpoints FastAPI (`/api/next`, `/api/result`, `/api/status`) |
| `server/downloader.py` | Cola de trabajos con estados |
| `data/pending.csv` | Códigos a procesar (gitignored) |
| `data/pending.csv.example` | Ejemplo de formato |
