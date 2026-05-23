"""Genera el PDF de instrucciones de BandeJA Downloader."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from pathlib import Path
SALIDA = str(Path(__file__).parent / "BandeJA-Downloader-Instrucciones.pdf")

# ── Estilos ──────────────────────────────────────────────────────────────────

base = getSampleStyleSheet()

titulo = ParagraphStyle(
    "Titulo",
    parent=base["Title"],
    fontSize=20,
    spaceAfter=6,
    textColor=colors.HexColor("#1a3a5c"),
)
subtitulo = ParagraphStyle(
    "Subtitulo",
    parent=base["Normal"],
    fontSize=11,
    textColor=colors.HexColor("#555555"),
    spaceAfter=20,
    alignment=TA_CENTER,
)
h2 = ParagraphStyle(
    "H2",
    parent=base["Heading2"],
    fontSize=13,
    textColor=colors.HexColor("#1a3a5c"),
    spaceBefore=16,
    spaceAfter=6,
    borderPad=4,
)
cuerpo = ParagraphStyle(
    "Cuerpo",
    parent=base["Normal"],
    fontSize=10,
    leading=15,
    spaceAfter=4,
)
codigo = ParagraphStyle(
    "Codigo",
    parent=base["Normal"],
    fontSize=9,
    fontName="Courier",
    backColor=colors.HexColor("#f0f0f0"),
    leading=13,
    leftIndent=8,
    spaceAfter=4,
)
aviso = ParagraphStyle(
    "Aviso",
    parent=base["Normal"],
    fontSize=10,
    leading=14,
    textColor=colors.HexColor("#8B0000"),
    spaceAfter=4,
)


def placeholder(descripcion: str):
    """Recuadro gris con texto de captura pendiente."""
    data = [[Paragraph(f"[ CAPTURA PENDIENTE: {descripcion} ]", ParagraphStyle(
        "ph", parent=base["Normal"], fontSize=9,
        textColor=colors.HexColor("#666666"), alignment=TA_CENTER,
    ))]]
    t = Table(data, colWidths=[15 * cm], rowHeights=[2.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), colors.HexColor("#e8e8e8")),
        ("BOX",          (0, 0), (-1, -1), 1, colors.HexColor("#aaaaaa")),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


def bala(texto: str):
    return Paragraph(f"&#8226;&#160;&#160;{texto}", cuerpo)


def sep():
    return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"),
                      spaceAfter=4, spaceBefore=4)


# ── Contenido ────────────────────────────────────────────────────────────────

historia = []

historia.append(Paragraph("BandeJA Downloader", titulo))
historia.append(Paragraph("Guía de instalación y uso", subtitulo))
historia.append(sep())

# Requisitos
historia.append(Paragraph("Requisitos previos", h2))
historia.append(bala("Google Chrome instalado"))
historia.append(bala("Sin otros requisitos — no se necesita Python ni ningún software adicional"))
historia.append(Spacer(1, 8))

# Paso 1
historia.append(sep())
historia.append(Paragraph("Paso 1 — Arrancar el servidor", h2))
historia.append(bala("Abrir la carpeta <font name='Courier'>servidor\\</font> y hacer doble clic en <b>bandeja-server.exe</b>"))
historia.append(bala("Se abre una ventana de terminal — <b>no cerrarla</b> mientras se usen las descargas"))
historia.append(bala("El servidor arranca en segundo plano en el puerto 8000"))
historia.append(Spacer(1, 6))
historia.append(placeholder("ventana del servidor arrancado"))
historia.append(Spacer(1, 8))

# Paso 2
historia.append(sep())
historia.append(Paragraph("Paso 2 — Instalar la extensión en Chrome", h2))
historia.append(bala("Abrir Chrome y navegar a <font name='Courier'>chrome://extensions</font>"))
historia.append(bala("Activar el interruptor <b>\"Modo desarrollador\"</b> (esquina superior derecha)"))
historia.append(bala("Pulsar <b>\"Cargar descomprimida\"</b>"))
historia.append(bala("Seleccionar la carpeta <font name='Courier'>extension\\</font> del paquete descomprimido"))
historia.append(Spacer(1, 6))
historia.append(placeholder("chrome://extensions con la extensión cargada"))
historia.append(Spacer(1, 8))

# Paso 3
historia.append(sep())
historia.append(Paragraph("Paso 3 — Abrir BandeJA en Chrome", h2))
historia.append(bala("Navegar a la URL de BandeJA e iniciar sesión"))
historia.append(bala("La pestaña de BandeJA debe permanecer abierta durante todo el proceso de descarga"))
historia.append(Spacer(1, 6))
historia.append(placeholder("BandeJA con sesión iniciada"))
historia.append(Spacer(1, 8))

# Paso 4
historia.append(sep())
historia.append(Paragraph("Paso 4 — Exportar el listado desde BandeJA", h2))
historia.append(bala("Aplicar los filtros deseados en BandeJA (fechas, estado, etc.)"))
historia.append(bala("Pulsar el botón de exportación para descargar el listado como CSV"))
historia.append(Spacer(1, 6))
historia.append(placeholder("botón de exportación CSV en BandeJA"))
historia.append(Spacer(1, 8))

# Paso 5
historia.append(sep())
historia.append(Paragraph("Paso 5 — Cargar el CSV en el popup", h2))
historia.append(bala("Hacer clic en el icono de la extensión en la barra de Chrome"))
historia.append(bala("Pulsar <b>\"Cargar CSV de BandeJA\"</b> y seleccionar el fichero exportado"))
historia.append(bala("El contador \"Pendiente\" se actualiza con los expedientes cargados"))
historia.append(bala("Las descargas arrancan automáticamente"))
historia.append(Spacer(1, 6))
historia.append(placeholder("popup de la extensión BandeJA Downloader"))
historia.append(Spacer(1, 8))

# Paso 6
historia.append(sep())
historia.append(Paragraph("Paso 6 — Seleccionar carpeta destino", h2))
historia.append(bala("En el popup, pulsar <b>\"Seleccionar carpeta destino…\"</b>"))
historia.append(bala("Elegir la carpeta donde se guardarán los ZIPs descargados"))
historia.append(bala("La ruta elegida aparece bajo el botón y se mantiene durante la sesión"))
historia.append(Spacer(1, 8))

# Paso 7
historia.append(sep())
historia.append(Paragraph("Paso 7 — Seguimiento y fin", h2))
historia.append(bala("Los contadores del popup (Pendiente, En curso, OK, Error) se actualizan solos cada 2 segundos"))
historia.append(bala("Cuando todos los expedientes estén completados, aparece una notificación de Windows"))
historia.append(bala("Pulsar <b>\"Descargar resultados CSV\"</b> para obtener el informe final"))
historia.append(Spacer(1, 8))

# Pausar y reanudar
historia.append(sep())
historia.append(Paragraph("Pausar y reanudar", h2))
historia.append(bala("El botón <b>\"&#9208; Pausar\"</b> detiene la cola sin perder el progreso ni los datos"))
historia.append(bala("Pulsar <b>\"&#9654; Reanudar\"</b> para continuar desde donde se dejó"))
historia.append(Spacer(1, 8))

# Solución de problemas
historia.append(sep())
historia.append(Paragraph("Solución de problemas", h2))

tabla_data = [
    [
        Paragraph("<b>Síntoma</b>", cuerpo),
        Paragraph("<b>Causa probable</b>", cuerpo),
        Paragraph("<b>Solución</b>", cuerpo),
    ],
    [
        Paragraph("El popup no responde", cuerpo),
        Paragraph("El servidor no está arrancado", cuerpo),
        Paragraph("Ejecutar bandeja-server.exe", cuerpo),
    ],
    [
        Paragraph("El contador no avanza", cuerpo),
        Paragraph("BandeJA no tiene sesión iniciada", cuerpo),
        Paragraph("Iniciar sesión en BandeJA en Chrome", cuerpo),
    ],
    [
        Paragraph("Error en un expediente", cuerpo),
        Paragraph("BandeJA no encontró documentos", cuerpo),
        Paragraph("Revisar CSV de resultados, columna \"Detalle\"", cuerpo),
    ],
    [
        Paragraph("Código no reconocido", cuerpo),
        Paragraph("Formato de CSV inesperado", cuerpo),
        Paragraph("Verificar que los códigos empiezan por EXT/ o INT/", cuerpo),
    ],
]

tabla = Table(tabla_data, colWidths=[4.5 * cm, 5 * cm, 5.5 * cm])
tabla.setStyle(TableStyle([
    ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#1a3a5c")),
    ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
    ("BOX",          (0, 0), (-1, -1), 0.5, colors.HexColor("#aaaaaa")),
    ("INNERGRID",    (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("VALIGN",       (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING",   (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
    ("LEFTPADDING",  (0, 0), (-1, -1), 6),
]))
historia.append(tabla)

# ── Generar PDF ──────────────────────────────────────────────────────────────

doc = SimpleDocTemplate(
    SALIDA,
    pagesize=A4,
    leftMargin=2.5 * cm,
    rightMargin=2.5 * cm,
    topMargin=2 * cm,
    bottomMargin=2 * cm,
)
doc.build(historia)
print(f"PDF generado: {SALIDA}")
