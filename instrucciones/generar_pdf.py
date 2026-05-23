"""Genera el PDF de instrucciones de BandeJA Downloader."""
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Flowable, Image,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.graphics.shapes import (
    Drawing, Rect, String, Line, Group,
)
from reportlab.graphics import renderPDF

SALIDA    = str(Path(__file__).parent / "BandeJA-Downloader-Instrucciones.pdf")
CAPTURAS  = Path(__file__).parent / "capturas"

# ── Paleta ───────────────────────────────────────────────────────────────────

VERDE       = colors.HexColor("#087021")
VERDE_OSC   = colors.HexColor("#065a1a")
GRIS_BTN    = colors.HexColor("#6c757d")
GRIS_OSC    = colors.HexColor("#495057")
NARANJA     = colors.HexColor("#e67e22")
AZUL_TIT    = colors.HexColor("#1a3a5c")
ROJO        = colors.HexColor("#c0392b")
FONDO_POPUP = colors.HexColor("#f8f9fa")
GRIS_BORDE  = colors.HexColor("#dee2e6")
VERDE_BG    = colors.HexColor("#d4edda")
VERDE_TXT   = colors.HexColor("#155724")
ROJO_BG     = colors.HexColor("#f8d7da")
ROJO_TXT    = colors.HexColor("#721c24")

# ── Estilos ──────────────────────────────────────────────────────────────────

base = getSampleStyleSheet()

titulo = ParagraphStyle(
    "Titulo", parent=base["Title"],
    fontSize=20, spaceAfter=6, textColor=AZUL_TIT,
)
subtitulo = ParagraphStyle(
    "Subtitulo", parent=base["Normal"],
    fontSize=11, textColor=colors.HexColor("#555555"),
    spaceAfter=20, alignment=TA_CENTER,
)
h2 = ParagraphStyle(
    "H2", parent=base["Heading2"],
    fontSize=13, textColor=AZUL_TIT,
    spaceBefore=16, spaceAfter=6,
)
cuerpo = ParagraphStyle(
    "Cuerpo", parent=base["Normal"],
    fontSize=10, leading=15, spaceAfter=4,
)
cuerpo_blanco = ParagraphStyle(
    "CuerpoBlanco", parent=base["Normal"],
    fontSize=10, leading=15, spaceAfter=4,
    textColor=colors.white,
)
mono = ParagraphStyle(
    "Mono", parent=base["Normal"],
    fontSize=9, fontName="Courier", leading=13, spaceAfter=2,
)
nota = ParagraphStyle(
    "Nota", parent=base["Normal"],
    fontSize=9, textColor=colors.HexColor("#555555"),
    leading=13, spaceAfter=4,
)


def bala(texto: str):
    return Paragraph(f"&#8226;&#160;&#160;{texto}", cuerpo)


def sep():
    return HRFlowable(
        width="100%", thickness=0.5,
        color=colors.HexColor("#cccccc"),
        spaceAfter=4, spaceBefore=4,
    )


def captura(nombre: str, ancho: float = 15 * cm) -> Image:
    ruta = str(CAPTURAS / nombre)
    img = Image(ruta)
    factor = ancho / img.imageWidth
    img.drawWidth  = ancho
    img.drawHeight = img.imageHeight * factor
    return img


def placeholder(descripcion: str):
    """Recuadro gris con texto de captura pendiente."""
    data = [[Paragraph(
        f"[ CAPTURA PENDIENTE: {descripcion} ]",
        ParagraphStyle("ph", parent=base["Normal"], fontSize=9,
                       textColor=colors.HexColor("#666666"), alignment=TA_CENTER),
    )]]
    t = Table(data, colWidths=[15 * cm], rowHeights=[2.2 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e8e8e8")),
        ("BOX",        (0, 0), (-1, -1), 1, colors.HexColor("#aaaaaa")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


# ── Mockup del popup ─────────────────────────────────────────────────────────

def _rect(d, x, y, w, h, fill, stroke=None, radius=3):
    r = Rect(x, y, w, h, rx=radius, ry=radius, fillColor=fill,
             strokeColor=stroke or fill, strokeWidth=0.5)
    d.add(r)


def _txt(d, x, y, text, size=8, color=colors.HexColor("#333333"),
         bold=False, align="left"):
    font = "Helvetica-Bold" if bold else "Helvetica"
    s = String(x, y, text, fontSize=size, fillColor=color,
               fontName=font, textAnchor=align)
    d.add(s)


def _boton(d, x, y, w, h, label, bg, fg=colors.white, size=8):
    _rect(d, x, y, w, h, fill=bg, radius=3)
    _txt(d, x + w / 2, y + h / 2 - size / 2.8, label,
         size=size, color=fg, align="middle")


def mockup_popup(
    total=0, pendiente=0, en_curso=0, ok=0, error=0,
    conectado=True, pausado=False,
    destino="Sin carpeta configurada",
    feedback="",
    titulo_mockup="Estado del popup",
) -> "PopupMockup":
    return PopupMockup(
        total=total, pendiente=pendiente, en_curso=en_curso,
        ok=ok, error=error, conectado=conectado, pausado=pausado,
        destino=destino, feedback=feedback, titulo_mockup=titulo_mockup,
    )


class PopupMockup(Flowable):
    """Dibuja una representación fiel del popup de la extensión."""

    W = 200      # ancho interior del popup (pts)
    PAD = 8      # padding
    LINE_H = 13  # altura de cada línea de stat

    def __init__(self, total, pendiente, en_curso, ok, error,
                 conectado, pausado, destino, feedback, titulo_mockup):
        super().__init__()
        self.total = total; self.pendiente = pendiente
        self.en_curso = en_curso; self.ok = ok; self.error = error
        self.conectado = conectado; self.pausado = pausado
        self.destino = destino; self.feedback = feedback
        self.titulo_mockup = titulo_mockup

    def _altura(self):
        h = self.PAD
        h += 14          # título
        h += 5 * self.LINE_H  # 5 stats
        h += 4           # gap
        h += 16          # barra servidor
        h += 6           # gap
        h += 16          # btn CSV
        h += 4           # gap
        h += 16          # btn pausa
        h += 4
        h += 16          # btn export
        h += 6           # gap
        h += 1           # divisor destino
        h += 6
        h += 16          # btn destino
        h += 4
        h += 10          # path destino
        if self.feedback:
            h += 10      # feedback
        h += self.PAD
        return h

    def wrap(self, avail_w, avail_h):
        self.avail_w = avail_w
        return self.W + 2 * self.PAD + 4, self._altura() + 20 + 4

    def draw(self):
        d = self.canv
        pad = self.PAD
        W = self.W
        h_total = self._altura()
        off_x = 2  # sombra
        off_y = 2

        # Etiqueta encima del popup
        d.setFont("Helvetica-Oblique", 7)
        d.setFillColor(colors.HexColor("#888888"))
        d.drawString(0, h_total + off_y + 6, self.titulo_mockup)

        # Fondo del popup
        d.setFillColor(FONDO_POPUP)
        d.setStrokeColor(GRIS_BORDE)
        d.setLineWidth(0.8)
        d.roundRect(off_x, off_y, W + 2 * pad, h_total, 4, fill=1, stroke=1)

        y = h_total + off_y - pad

        # Título
        y -= 13
        d.setFont("Helvetica-Bold", 10)
        d.setFillColor(VERDE)
        d.drawString(off_x + pad, y, "BandeJA Downloader")
        y -= 3

        # Stats
        def stat_line(label, valor, color_val):
            nonlocal y
            y -= self.LINE_H
            d.setFont("Helvetica", 8)
            d.setFillColor(colors.HexColor("#666666"))
            d.drawString(off_x + pad, y, label)
            d.setFont("Helvetica-Bold", 8)
            d.setFillColor(color_val)
            d.drawString(off_x + pad + 65, y, str(valor))

        stat_line("Total:",       self.total,     colors.HexColor("#333333"))
        stat_line("Pendiente:",   self.pendiente, colors.HexColor("#333333"))
        stat_line("En curso:",    self.en_curso,  NARANJA)
        stat_line("Completados:", self.ok,        VERDE)
        stat_line("Errores:",     self.error,     ROJO)
        y -= 4

        # Barra de estado del servidor
        srv_bg  = VERDE_BG  if self.conectado else ROJO_BG
        srv_txt = VERDE_TXT if self.conectado else ROJO_TXT
        srv_lbl = "✓ Conectado al servidor" if self.conectado else "✗ Servidor no disponible"
        d.setFillColor(srv_bg)
        d.setStrokeColor(srv_txt)
        d.setLineWidth(0.4)
        d.roundRect(off_x + pad, y - 13, W, 15, 3, fill=1, stroke=1)
        d.setFont("Helvetica", 7.5)
        d.setFillColor(srv_txt)
        d.drawCentredString(off_x + pad + W / 2, y - 9.5, srv_lbl)
        y -= 20

        # Botón Cargar CSV
        d.setFillColor(VERDE)
        d.setStrokeColor(VERDE)
        d.setLineWidth(0)
        d.roundRect(off_x + pad, y - 13, W, 15, 3, fill=1, stroke=0)
        d.setFont("Helvetica", 8)
        d.setFillColor(colors.white)
        d.drawCentredString(off_x + pad + W / 2, y - 9.5, "Cargar CSV de BandeJA")
        y -= 18

        # Botón Pausar / Reanudar
        btn_color = VERDE  if not self.pausado else NARANJA
        btn_lbl   = "|| Pausar" if not self.pausado else "> Reanudar"
        d.setFillColor(btn_color)
        d.roundRect(off_x + pad, y - 13, W, 15, 3, fill=1, stroke=0)
        d.setFont("Helvetica", 8)
        d.setFillColor(colors.white)
        d.drawCentredString(off_x + pad + W / 2, y - 9.5, btn_lbl)
        y -= 18

        # Botón Descargar CSV resultados
        d.setFillColor(GRIS_OSC)
        d.roundRect(off_x + pad, y - 13, W, 15, 3, fill=1, stroke=0)
        d.setFont("Helvetica", 8)
        d.setFillColor(colors.white)
        d.drawCentredString(off_x + pad + W / 2, y - 9.5, "Descargar resultados CSV")
        y -= 18

        # Feedback CSV
        if self.feedback:
            d.setFont("Helvetica-Oblique", 7)
            d.setFillColor(colors.HexColor("#555555"))
            d.drawCentredString(off_x + pad + W / 2, y, self.feedback)
            y -= 10

        # Divisor zona destino
        d.setStrokeColor(GRIS_BORDE)
        d.setLineWidth(0.5)
        d.line(off_x + pad, y, off_x + pad + W, y)
        y -= 7

        # Botón Seleccionar carpeta
        d.setFillColor(GRIS_BTN)
        d.roundRect(off_x + pad, y - 13, W, 15, 3, fill=1, stroke=0)
        d.setFont("Helvetica", 8)
        d.setFillColor(colors.white)
        d.drawCentredString(off_x + pad + W / 2, y - 9.5, "Seleccionar carpeta destino…")
        y -= 18

        # Ruta destino
        d.setFont("Helvetica", 7)
        d.setFillColor(colors.HexColor("#555555"))
        # Truncar si es muy larga
        ruta = self.destino
        if len(ruta) > 38:
            ruta = "…" + ruta[-36:]
        d.drawString(off_x + pad, y, ruta)


# ── Tabla de solución de problemas ───────────────────────────────────────────

def tabla_problemas():
    cab = ParagraphStyle(
        "TablaCab", parent=base["Normal"],
        fontSize=10, leading=14, fontName="Helvetica-Bold",
        textColor=colors.white,
    )
    filas = [
        [
            Paragraph("Síntoma", cab),
            Paragraph("Causa probable", cab),
            Paragraph("Solución", cab),
        ],
        [
            Paragraph("El popup no responde", cuerpo),
            Paragraph("El servidor no está arrancado", cuerpo),
            Paragraph("Ejecutar <font name='Courier'>bandeja-server.exe</font>", cuerpo),
        ],
        [
            Paragraph("El contador no avanza", cuerpo),
            Paragraph("BandeJA no tiene sesión iniciada", cuerpo),
            Paragraph("Iniciar sesión en BandeJA en Chrome", cuerpo),
        ],
        [
            Paragraph("Error en un expediente", cuerpo),
            Paragraph("BandeJA no encontró documentos", cuerpo),
            Paragraph("Revisar CSV de resultados, columna «Detalle»", cuerpo),
        ],
        [
            Paragraph("Código no reconocido", cuerpo),
            Paragraph("Formato de CSV inesperado", cuerpo),
            Paragraph("Verificar que los códigos empiezan por EXT/ o INT/", cuerpo),
        ],
    ]
    t = Table(filas, colWidths=[4.5 * cm, 5 * cm, 5.5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  AZUL_TIT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("BOX",            (0, 0), (-1, -1), 0.5, colors.HexColor("#aaaaaa")),
        ("INNERGRID",      (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
    ]))
    return t


# ── Construcción del documento ────────────────────────────────────────────────

def construir():
    historia = []

    # Portada
    historia.append(Paragraph("BandeJA Downloader", titulo))
    historia.append(Paragraph("Guía de instalación y uso", subtitulo))
    historia.append(sep())

    # ── Contenido del paquete ──────────────────────────────────────────────
    historia.append(Paragraph("Contenido del paquete", h2))
    historia.append(Paragraph(
        "Al descomprimir el fichero <font name='Courier'>BandeJA-Downloader-vX.X.zip</font> "
        "obtendrás esta estructura de carpetas:", cuerpo,
    ))

    historia.append(captura("Tree.jpg", ancho=10 * cm))
    historia.append(Spacer(1, 8))

    # Glosario de ficheros
    historia.append(Paragraph("Qué es cada elemento:", h2))
    glosario = [
        [
            Paragraph("<b>bandeja-server.exe</b>", cuerpo),
            Paragraph(
                "El servidor local. Debe estar en ejecución durante todo el proceso. "
                "No requiere instalación — basta con ejecutarlo.", cuerpo,
            ),
        ],
        [
            Paragraph("<b>extension\\</b>", cuerpo),
            Paragraph(
                "Carpeta de la extensión de Chrome. Se carga una sola vez en "
                "<font name='Courier'>chrome://extensions</font> mediante "
                "\"Cargar descomprimida\".", cuerpo,
            ),
        ],
        [
            Paragraph("<b>Instrucciones.pdf</b>", cuerpo),
            Paragraph("Este documento.", cuerpo),
        ],
    ]
    t_glos = Table(glosario, colWidths=[4.5 * cm, 10.5 * cm])
    t_glos.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("BOX",            (0, 0), (-1, -1), 0.5, colors.HexColor("#aaaaaa")),
        ("INNERGRID",      (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
    ]))
    historia.append(t_glos)
    historia.append(Spacer(1, 8))

    # ── Paso 1 ────────────────────────────────────────────────────────────
    historia.append(sep())
    historia.append(Paragraph("Paso 1 — Arrancar el servidor", h2))
    historia.append(bala(
        "Abrir la carpeta <font name='Courier'>servidor\\</font> "
        "y hacer doble clic en <b>bandeja-server.exe</b>"
    ))
    historia.append(bala(
        "Se abre una ventana de terminal — <b>no cerrarla</b> "
        "mientras se usen las descargas"
    ))
    historia.append(bala("El servidor queda escuchando en el puerto 8000"))
    historia.append(Spacer(1, 6))
    historia.append(captura("Server_sin_listado.jpg"))
    historia.append(Spacer(1, 8))

    # ── Paso 2 ────────────────────────────────────────────────────────────
    historia.append(sep())
    historia.append(Paragraph("Paso 2 — Instalar la extensión en Chrome", h2))
    historia.append(bala(
        "Abrir Chrome y navegar a "
        "<font name='Courier'>chrome://extensions</font>"
    ))
    historia.append(bala(
        "Activar el interruptor <b>\"Modo desarrollador\"</b> "
        "(esquina superior derecha)"
    ))
    historia.append(bala("Pulsar <b>\"Cargar descomprimida\"</b>"))
    historia.append(bala(
        "Seleccionar la carpeta <font name='Courier'>extension\\</font> "
        "del paquete descomprimido"
    ))
    historia.append(Spacer(1, 6))
    historia.append(captura("Extensión_cargada.jpg"))
    historia.append(Spacer(1, 8))
    historia.append(Paragraph(
        "<b>Importante — pinear la extensión:</b> para acceder al popup "
        "desde la barra de Chrome, haz clic en el icono del puzzle "
        "(esquina superior derecha), localiza <b>BandeJA Downloader</b> "
        "y pulsa el icono del pin. El icono de la extensión quedará "
        "visible de forma permanente en la barra.",
        nota,
    ))
    historia.append(Spacer(1, 8))

    # ── Paso 3 ────────────────────────────────────────────────────────────
    historia.append(sep())
    historia.append(Paragraph("Paso 3 — Abrir BandeJA en Chrome", h2))
    historia.append(bala("Navegar a la URL de BandeJA e iniciar sesión"))
    historia.append(bala(
        "La pestaña de BandeJA debe permanecer abierta "
        "durante todo el proceso de descarga"
    ))
    historia.append(Spacer(1, 8))

    # ── Paso 4 ────────────────────────────────────────────────────────────
    historia.append(sep())
    historia.append(Paragraph("Paso 4 — Exportar el listado desde BandeJA", h2))
    historia.append(bala(
        "Aplicar los filtros deseados en BandeJA "
        "(fechas, estado, tipo de comunicación…)"
    ))
    historia.append(bala(
        "Pulsar el botón de exportación para descargar el listado como CSV"
    ))
    historia.append(Spacer(1, 6))
    historia.append(captura("Menu_exportar_csv.jpg", ancho=8 * cm))
    historia.append(Spacer(1, 8))

    # ── Paso 5 ────────────────────────────────────────────────────────────
    historia.append(sep())
    historia.append(Paragraph("Paso 5 — Seleccionar carpeta destino", h2))
    historia.append(bala(
        "Hacer clic en el icono de la extensión en la barra de Chrome"
    ))
    historia.append(captura("Boton_extension_pulsado.jpg", ancho=10 * cm))
    historia.append(bala(
        "Pulsar <b>\"Seleccionar carpeta destino…\"</b>"
    ))
    historia.append(bala(
        "Se abre un diálogo de Windows para elegir la carpeta "
        "donde se guardarán los ZIPs descargados"
    ))
    historia.append(bala(
        "La ruta elegida aparece bajo el botón y se mantiene durante la sesión"
    ))
    historia.append(Paragraph(
        "<b>Nota:</b> si no se selecciona ninguna carpeta, los ZIPs descargados "
        "se guardan en la carpeta <b>Descargas</b> del usuario de Windows "
        "(la misma que usa Chrome por defecto).",
        nota,
    ))
    historia.append(Spacer(1, 6))
    historia.append(mockup_popup(
        total=0, pendiente=0, en_curso=0, ok=0, error=0,
        conectado=True, pausado=False,
        destino="C:\\Users\\Usuario\\Descargas\\BandeJA",
        titulo_mockup="Popup — carpeta destino configurada antes de cargar el CSV",
    ))
    historia.append(Spacer(1, 8))

    # ── Paso 6 ────────────────────────────────────────────────────────────
    historia.append(sep())
    historia.append(Paragraph("Paso 6 — Cargar el CSV en el popup", h2))
    historia.append(bala(
        "Pulsar <b>\"Cargar CSV de BandeJA\"</b> y seleccionar el fichero exportado"
    ))
    historia.append(bala(
        "El contador «Pendiente» se actualiza con los expedientes cargados"
    ))
    historia.append(bala("Las descargas arrancan automáticamente"))
    historia.append(Spacer(1, 6))
    historia.append(mockup_popup(
        total=12, pendiente=9, en_curso=1, ok=2, error=0,
        conectado=True, pausado=False,
        destino="C:\\Users\\Usuario\\Descargas\\BandeJA",
        feedback="12 nuevos expedientes cargados",
        titulo_mockup="Popup tras cargar el CSV — descargas en curso",
    ))
    historia.append(Spacer(1, 8))
    historia.append(Paragraph(
        "El servidor muestra en tiempo real el estado de cada expediente "
        "en la columna Estado, junto con la hora de finalización y el "
        "nombre del fichero ZIP descargado.",
        cuerpo,
    ))
    historia.append(Spacer(1, 6))
    historia.append(captura("Server_con_listado.jpg"))
    historia.append(Spacer(1, 8))

    # ── Paso 7 ────────────────────────────────────────────────────────────
    historia.append(sep())
    historia.append(Paragraph("Paso 7 — Seguimiento y fin", h2))
    historia.append(bala(
        "Los contadores del popup se actualizan solos cada 2 segundos"
    ))
    historia.append(bala(
        "Durante el proceso y al finalizar, la aplicación muestra "
        "<b>notificaciones toast de Windows</b> (las alertas emergentes "
        "de la esquina inferior derecha del escritorio) con el resultado "
        "de cada expediente y un resumen final con el total de "
        "completados, errores y expedientes sin documentos"
    ))
    historia.append(bala(
        "Pulsar <b>\"Descargar resultados CSV\"</b> para obtener el informe final "
        "con el resultado de cada expediente"
    ))
    historia.append(Spacer(1, 6))
    historia.append(mockup_popup(
        total=12, pendiente=0, en_curso=0, ok=11, error=1,
        conectado=True, pausado=False,
        destino="C:\\Users\\Usuario\\Descargas\\BandeJA",
        titulo_mockup="Popup al finalizar la cola",
    ))
    historia.append(Spacer(1, 8))

    # ── Pausar y reanudar ─────────────────────────────────────────────────
    historia.append(sep())
    historia.append(Paragraph("Pausar y reanudar", h2))
    historia.append(bala(
        "El botón <b>\"|| Pausar\"</b> detiene la cola "
        "sin perder el progreso ni los datos"
    ))
    historia.append(bala(
        "Pulsar <b>\"> Reanudar\"</b> para continuar desde donde se dejó"
    ))
    historia.append(Spacer(1, 6))
    historia.append(mockup_popup(
        total=12, pendiente=5, en_curso=0, ok=7, error=0,
        conectado=True, pausado=True,
        destino="C:\\Users\\Usuario\\Descargas\\BandeJA",
        titulo_mockup="Popup en estado Pausado",
    ))
    historia.append(Spacer(1, 8))

    # ── Solución de problemas ─────────────────────────────────────────────
    historia.append(sep())
    historia.append(Paragraph("Solución de problemas", h2))
    historia.append(tabla_problemas())

    return historia


# ── Generar PDF ───────────────────────────────────────────────────────────────

doc = SimpleDocTemplate(
    SALIDA,
    pagesize=A4,
    leftMargin=2.5 * cm,
    rightMargin=2.5 * cm,
    topMargin=2 * cm,
    bottomMargin=2 * cm,
)
doc.build(construir())
print(f"PDF generado: {SALIDA}")
