"""
Notificaciones toast de Windows via PowerShell (sin dependencias extra).
"""
from __future__ import annotations

import subprocess
import threading


def _lanzar(titulo: str, mensaje: str) -> None:
    """Ejecuta el script PowerShell en un hilo para no bloquear el servidor."""
    # Escapar comillas simples en los textos
    titulo  = titulo.replace("'", "''")
    mensaje = mensaje.replace("'", "''")

    script = f"""
$xml = [Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom,ContentType=WindowsRuntime]::new()
$xml.LoadXml('<toast duration="short"><visual><binding template="ToastText02">
  <text id="1">{titulo}</text>
  <text id="2">{mensaje}</text>
</binding></visual></toast>')
$toast = [Windows.UI.Notifications.ToastNotification,Windows.UI.Notifications,ContentType=WindowsRuntime]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager,Windows.UI.Notifications,ContentType=WindowsRuntime]::CreateToastNotifier('BandeJA Downloader').Show($toast)
"""
    subprocess.run(
        ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", script],
        capture_output=True,
    )


def notificar(titulo: str, mensaje: str) -> None:
    """Lanza la notificación en segundo plano (no bloquea)."""
    threading.Thread(target=_lanzar, args=(titulo, mensaje), daemon=True).start()
