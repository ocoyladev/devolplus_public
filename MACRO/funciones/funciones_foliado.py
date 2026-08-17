"""Foliado de PDF: estampa un sello de folio en la esquina superior derecha.

Solo se usa en expedientes virtuales. El sello (círculo "ACME" con la unidad
orgánica y el número de folio) se dibuja por código con reportlab, de modo que
la unidad orgánica es configurable. La numeración es inversa: la primera página
(carátula) no se folia; la última lleva el folio 01 y va subiendo hacia el
inicio (la página 2 lleva el folio más alto).
"""

from __future__ import annotations

import io
import math
import os

try:
    from reportlab.pdfgen import canvas as _rl_canvas
    from reportlab.lib.colors import red as _ROJO
except ImportError:  # entorno sin reportlab
    _rl_canvas = None
    _ROJO = None

try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:  # entorno sin PyPDF2
    PdfReader = None
    PdfWriter = None

UNIDAD_ORGANICA_DEFAULT = "7EC400"


# ---------------------------------------------------------------------------
#  Numeración (lógica pura)
# ---------------------------------------------------------------------------

def ancho_folio(total_paginas: int) -> int:
    """Ancho (dígitos) del folio: 2 por defecto, 3+ si el folio máx lo requiere."""
    folio_max = max(1, total_paginas - 1)
    return max(2, len(str(folio_max)))


def plan_foliado(total_paginas: int) -> list[str | None]:
    """Lista por página (1..N) con el folio a estampar; ``None`` en la carátula.

    Folio de la página ``i`` (1-indexada, i>=2) = ``total + 1 - i`` con relleno
    de ceros al ancho del documento. La página 1 no se folia.
    """
    if total_paginas <= 0:
        return []
    ancho = ancho_folio(total_paginas)
    plan: list[str | None] = [None]
    for i in range(2, total_paginas + 1):
        numero = total_paginas + 1 - i
        plan.append(str(numero).zfill(ancho))
    return plan


# ---------------------------------------------------------------------------
#  Dibujo del sello
# ---------------------------------------------------------------------------

def _texto_en_arco(c, cx, cy, radio, texto, font, size, *, arriba=True):
    """Dibuja ``texto`` centrado a lo largo de un arco del círculo."""
    c.setFont(font, size)
    # separación angular por carácter (en grados), proporcional al tamaño
    paso = math.degrees((size * 0.62) / radio)
    total = paso * (len(texto) - 1)
    ang0 = 90 + total / 2 if arriba else -90 - total / 2
    for i, ch in enumerate(texto):
        ang = ang0 - paso * i if arriba else ang0 + paso * i
        rad = math.radians(ang)
        x = cx + radio * math.cos(rad)
        y = cy + radio * math.sin(rad)
        c.saveState()
        c.translate(x, y)
        # tangente al círculo: rota la letra para seguir el arco
        rot = (ang - 90) if arriba else (ang + 90)
        c.rotate(rot)
        c.drawCentredString(0, 0, ch)
        c.restoreState()


def _dibujar_sello(c, cx, cy, radio, unidad_organica, numero):
    """Dibuja el sello de folio centrado en (cx, cy) con el ``numero`` indicado.

    Proporciones tomadas del 'creador_sello.pptx' (círculo Ø = 2R como referencia):
      - borde del círculo: 8pt sobre Ø425 -> 0.038R
      - "ACME" en arco superior, font 70/212.6 = 0.33R
      - línea divisoria a 0.35R bajo el centro, semiancho 0.737R, grosor 0.021R
      - "FOLIO" (centro a 0.514R) y unidad orgánica (centro a 0.813R), font 0.216R
      - número de folio centrado en el espacio entre el arco y la línea
    """
    R = radio
    num = str(numero)
    c.saveState()
    c.setStrokeColor(_ROJO)
    c.setFillColor(_ROJO)

    # Círculo
    c.setLineWidth(max(0.8, R * 0.038))
    c.circle(cx, cy, R, stroke=1, fill=0)

    # "ACME" en arco superior
    _texto_en_arco(c, cx, cy, R * 0.72, "ACME", "Helvetica-Bold",
                   R * 0.32, arriba=True)

    # Línea divisoria bajo el centro
    y_linea = cy - R * 0.35
    c.setLineWidth(max(0.6, R * 0.021))
    c.line(cx - R * 0.737, y_linea, cx + R * 0.737, y_linea)

    # "FOLIO" y unidad orgánica en la mitad inferior (centro -> baseline ~ -0.35font)
    fpie = R * 0.216
    c.setFont("Helvetica-Bold", fpie)
    c.drawCentredString(cx, cy - R * 0.514 - 0.35 * fpie, "FOLIO")
    c.drawCentredString(cx, cy - R * 0.813 - 0.35 * fpie, str(unidad_organica))

    # Número de folio: centrado en el espacio entre el arco y la línea
    font_num = R * 0.55 if len(num) <= 2 else R * 0.42
    centro_num = cy - R * 0.08
    c.setFont("Helvetica-Bold", font_num)
    c.drawCentredString(cx, centro_num - 0.35 * font_num, num)
    c.restoreState()


def _overlay_sello(ancho_pag, alto_pag, unidad_organica, numero):
    """Crea un PDF de una página (overlay) con el sello en la esquina sup. der.

    En páginas apaisadas (landscape) el sello se rota 90° (versión vertical).
    """
    buf = io.BytesIO()
    c = _rl_canvas.Canvas(buf, pagesize=(ancho_pag, alto_pag))

    # Sello más compacto en páginas pequeñas; tamaño base ~44pt de radio.
    radio = min(44.0, min(ancho_pag, alto_pag) * 0.115)
    # Margen pequeño e igual respecto a los bordes de la esquina usada.
    margen = max(9.0, radio * 0.18)

    if ancho_pag > alto_pag:
        # Página horizontal (landscape): sello en la esquina INFERIOR derecha,
        # echado (rotado -90°), tal como el foliado de referencia.
        cx = ancho_pag - margen - radio
        cy = margen + radio
        c.saveState()
        c.translate(cx, cy)
        c.rotate(-90)
        _dibujar_sello(c, 0, 0, radio, unidad_organica, numero)
        c.restoreState()
    else:
        # Página vertical (portrait): sello upright en la esquina superior derecha.
        cx = ancho_pag - margen - radio
        cy = alto_pag - margen - radio
        _dibujar_sello(c, cx, cy, radio, unidad_organica, numero)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
#  Foliado del PDF
# ---------------------------------------------------------------------------

def foliar_pdf(pdf_in, pdf_out, unidad_organica=UNIDAD_ORGANICA_DEFAULT, log=print):
    """Genera ``pdf_out`` foliado a partir de ``pdf_in``. Devuelve la ruta o None."""
    if PdfReader is None or _rl_canvas is None:
        log("  ⚠ Foliado no disponible (faltan reportlab/PyPDF2)")
        return None
    if not os.path.exists(pdf_in):
        log(f"  ⚠ PDF a foliar no encontrado: {pdf_in}")
        return None

    try:
        lector = PdfReader(pdf_in)
        total = len(lector.pages)
        plan = plan_foliado(total)
        escritor = PdfWriter()

        for i, pagina in enumerate(lector.pages):
            folio = plan[i] if i < len(plan) else None
            if folio is not None:
                ancho = float(pagina.mediabox.width)
                alto = float(pagina.mediabox.height)
                buf = _overlay_sello(ancho, alto, unidad_organica, folio)
                overlay = PdfReader(buf).pages[0]
                pagina.merge_page(overlay)
            escritor.add_page(pagina)

        with open(pdf_out, "wb") as fh:
            escritor.write(fh)
        log(f"  ✓ PDF foliado generado ({max(0, total - 1)} folios)")
        return pdf_out
    except Exception as e:
        log(f"  ⚠ Error al foliar: {e}")
        return None
