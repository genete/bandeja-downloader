from pathlib import Path

# Raíz del proyecto
BASE_DIR = Path(__file__).parent.parent

# Directorios
DOWNLOADS_DIR = BASE_DIR / "downloads"
DATA_DIR      = BASE_DIR / "data"

# Fichero de entrada
PENDING_CSV = DATA_DIR / "pending.csv"

# Servidor
SERVER_HOST = "localhost"
SERVER_PORT = 8000
