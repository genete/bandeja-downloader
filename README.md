# BandeJA Downloader

Herramienta para automatizar la descarga masiva de documentos desde BandeJA mediante una extensión de Chrome y un servidor local.

## Requisitos

- Google Chrome
- Acceso autenticado a BandeJA

Sin otros requisitos — el paquete de distribución incluye el servidor compilado, no es necesario instalar Python.

## Instalación rápida

1. Descarga el ZIP desde [Releases](../../releases/latest)
2. Descomprime y ejecuta `servidor\bandeja-server.exe`
3. En Chrome, ve a `chrome://extensions` → **Cargar descomprimida** → selecciona la carpeta `extension\`
4. Consulta `instrucciones\BandeJA-Downloader-Instrucciones.pdf` para el uso completo

## Uso

1. Filtra los expedientes en BandeJA y exporta el listado como CSV
2. Haz clic en el icono de la extensión y carga el CSV
3. Las descargas arrancan automáticamente; los contadores se actualizan cada 2 segundos
4. Al terminar, descarga el CSV de resultados desde el popup

## Arquitectura

```
CSV de BandeJA → servidor Python (FastAPI :8000)
                       ↑ polling GET /api/next
                 extensión Chrome (background.js)
                       ↓ automatización DOM
                 BandeJA (filtrar → modal → ZIP)
                       ↓ chrome.downloads
                 background.js → POST /api/result
```

## Desarrollo

```bash
pip install -r requirements.txt
python -m server.main
```

### Build del paquete de distribución

```powershell
pip install pyinstaller
.\build.ps1
```

Genera `release\BandeJA-Downloader-vX.X.zip` listo para distribuir.

## Licencia

[MIT](LICENSE)
