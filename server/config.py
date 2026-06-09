import sys
from pathlib import Path

# Raíz del proyecto — cuando corre como .exe (PyInstaller frozen) apunta
# al directorio del ejecutable; en desarrollo apunta a la raíz del repo.
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent

DOWNLOADS_DIR = BASE_DIR / "downloads"
DATA_DIR      = BASE_DIR / "data"
PENDING_CSV   = DATA_DIR / "pending.csv"

BANDEJA_URL = "https://extranet.chie.junta-andalucia.es/bandeja/"
