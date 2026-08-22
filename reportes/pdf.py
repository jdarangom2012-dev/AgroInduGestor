from io import BytesIO

from django.core.exceptions import ImproperlyConfigured
from django.contrib.staticfiles import finders


def _load_reportlab():
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ModuleNotFoundError as exc:
        raise ImproperlyConfigured(
            "La exportación a PDF requiere instalar reportlab. "
            "Ejecuta: python -m pip install -r requirements.txt"
        ) from exc

    return {
        "colors": colors,
        "letter": letter,
        "ParagraphStyle": ParagraphStyle,
        "getSampleStyleSheet": getSampleStyleSheet,
        "cm": cm,
        "Paragraph": Paragraph,
        "Image": Image,
        "KeepTogether": KeepTogether,
        "SimpleDocTemplate": SimpleDocTemplate,
        "Spacer": Spacer,
        "Table": Table,
        "TableStyle": TableStyle,
    }


def _text(value, default="-"):
    if value in (None, ""):
        return default
    return str(value)


def _kg(value):
    return f"{float(value or 0):,.2f} kg"


def _number(value):
    value = float(value or 0)
    if value.is_integer():
        return f"{int(value):,}"
    return f"{value:,.2f}"


def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColorRGB(0.42, 0.45, 0.50)
    canvas.drawCentredString(doc.pagesize[0] / 2, 0.65 * doc.bottomMargin, f"Página {doc.page}")
    canvas.restoreState()


def _find_static_asset(path):
    found = finders.find(path)
    if found:
        return found
    return None


def _cropped_logo_buffer(path):
    try:
        from PIL import Image as PILImage, ImageChops
    except ModuleNotFoundError:
        return None, None

    image = PILImage.open(path).convert("RGBA")

    alpha_bbox = image.getchannel("A").getbbox()
    if alpha_bbox:
        image = image.crop(alpha_bbox)
    else:
        background = PILImage.new(image.mode, image.size, image.getpixel((0, 0)))
        diff = ImageChops.difference(image, background)
        bbox = diff.getbbox()
        if bbox:
            image = image.crop(bbox)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer, image.size


def _logo_flowable(styles, max_width, max_height):
    logo_path = _find_static_asset("img/Logo_central.png")
    if not logo_path:
        return None

    Image = styles["_rl"]["Image"]
    logo_buffer, size = _cropped_logo_buffer(logo_path)
    source = logo_buffer or logo_path
    logo = Image(source)

    width, height = size or (logo.imageWidth, logo.imageHeight)
    if not width or not height:
        return None

    scale = min(max_width / width, max_height / height)
    logo.drawWidth = width * scale
    logo.drawHeight = height * scale
    return logo


def _report_header(orden, styles):
    rl = styles["_rl"]
    colors = rl["colors"]
    cm = rl["cm"]
    Paragraph = rl["Paragraph"]
    Table = rl["Table"]
    TableStyle = rl["TableStyle"]

    logo = _logo_flowable(styles, max_width=3.2 * cm, max_height=2.4 * cm)
    logo_cell = logo or Paragraph("Tostadora<br/>La Central", styles["Eyebrow"])

    order_info = Table(
        [
            [Paragraph("REPORTE DE FACTURACIÓN", styles["HeaderTitle"])],
            [Paragraph("Tostadora La Central", styles["HeaderSubtitle"])],
            [Paragraph(f"<b>Orden de Producción:</b> {_text(orden.orden)}", styles["HeaderMeta"])],
            [Paragraph(f"<b>Cliente:</b> {_text(orden.cliente)}", styles["HeaderMeta"])],
            [
                Paragraph(
                    f"<b>Fecha:</b> {orden.fecha_inicio_orden.strftime('%d/%m/%Y') if orden.fecha_inicio_orden else '-'}",
                    styles["HeaderMeta"],
                )
            ],
            [Paragraph(f"<b>Estado:</b> {_text(orden.estado_orden)}", styles["HeaderMeta"])],
        ],
        colWidths=[11.2 * cm],
        hAlign="LEFT",
    )
    order_info.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )

    header = Table([[logo_cell, order_info]], colWidths=[3.8 * cm, 11.2 * cm], hAlign="LEFT")
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.8, colors.HexColor("#111827")),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return header


def _section(title, styles):
    Paragraph = styles["_rl"]["Paragraph"]
    Spacer = styles["_rl"]["Spacer"]
    cm = styles["_rl"]["cm"]
    return [Spacer(1, 0.24 * cm), Paragraph(title, styles["SectionTitle"]), Spacer(1, 0.08 * cm)]


def _keep_section(title, flowable, styles):
    KeepTogether = styles["_rl"]["KeepTogether"]
    return KeepTogether([*_section(title, styles), flowable])


def _key_value_table(rows, rl):
    colors = rl["colors"]
    cm = rl["cm"]
    Table = rl["Table"]
    TableStyle = rl["TableStyle"]
    table = Table(rows, colWidths=[8 * cm, 7 * cm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _paragraph_cell(value, style, style_name="TableCell"):
    return style["_rl"]["Paragraph"](_text(value), style[style_name])


def _data_table(headers, rows, empty_text, styles, col_widths=None):
    rl = styles["_rl"]
    Paragraph = rl["Paragraph"]
    colors = rl["colors"]
    cm = rl["cm"]
    Table = rl["Table"]
    TableStyle = rl["TableStyle"]
    if not rows:
        return Paragraph(empty_text, styles["Muted"])

    data = [
        [_paragraph_cell(header, styles, "TableHeader") for header in headers],
        *[[_paragraph_cell(value, styles) for value in row] for row in rows],
    ]
    table = Table(data, colWidths=col_widths or [6.2 * cm, 5.2 * cm, 3.6 * cm], hAlign="LEFT", repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def render_facturacion_pdf(report):
    rl = _load_reportlab()
    colors = rl["colors"]
    letter = rl["letter"]
    ParagraphStyle = rl["ParagraphStyle"]
    getSampleStyleSheet = rl["getSampleStyleSheet"]
    cm = rl["cm"]
    Paragraph = rl["Paragraph"]
    SimpleDocTemplate = rl["SimpleDocTemplate"]
    Spacer = rl["Spacer"]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.3 * cm,
        bottomMargin=1.3 * cm,
        title="Reporte de Facturacion",
    )

    base_styles = getSampleStyleSheet()
    styles = {
        "Title": ParagraphStyle(
            "ReportTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=colors.HexColor("#111827"),
            spaceAfter=4,
        ),
        "HeaderTitle": ParagraphStyle(
            "HeaderTitle",
            parent=base_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=colors.HexColor("#111827"),
            spaceAfter=1,
            alignment=0,
        ),
        "HeaderSubtitle": ParagraphStyle(
            "HeaderSubtitle",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#374151"),
        ),
        "HeaderMeta": ParagraphStyle(
            "HeaderMeta",
            parent=base_styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#111827"),
        ),
        "Subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base_styles["Normal"],
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#374151"),
        ),
        "Eyebrow": ParagraphStyle(
            "ReportEyebrow",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#374151"),
        ),
        "SectionTitle": ParagraphStyle(
            "SectionTitle",
            parent=base_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#111827"),
            spaceBefore=2,
            spaceAfter=2,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base_styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#111827"),
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=base_styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        ),
        "Muted": ParagraphStyle(
            "Muted",
            parent=base_styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#6B7280"),
        ),
        "Normal": base_styles["Normal"],
        "_rl": rl,
    }

    orden = report["orden"]
    procesos = report["procesos"]
    story = [
        _report_header(orden, styles),
        Spacer(1, 0.15 * cm),
    ]

    trilla = procesos["trilla"]
    story.append(
        _keep_section(
            "TRILLA",
        _key_value_table(
            [
                ["Peso Café Neto Total", _kg(trilla["entrada"]) if trilla["aplica"] else "Sin registros."],
                ["Peso Café Verde Total", _kg(trilla["salida"]) if trilla["aplica"] else "Sin registros."],
            ],
            rl,
        ),
            styles,
        )
    )

    seleccion_verde = procesos["seleccion_verde"]
    story.append(
        _keep_section(
            "SELECCIÓN VERDE",
        _key_value_table(
            [
                ["Total de Grupo", _kg(seleccion_verde["total_de_grupo"]) if seleccion_verde["aplica"] else "Sin registros."],
                ["Peso Aceptado", _kg(seleccion_verde["peso_aceptado"]) if seleccion_verde["aplica"] else "Sin registros."],
                ["Humedad", _number(seleccion_verde["humedad"]) if seleccion_verde["aplica"] else "Sin registros."],
                ["Densidad", _number(seleccion_verde["densidad"]) if seleccion_verde["aplica"] else "Sin registros."],
            ],
            rl,
        ),
            styles,
        )
    )

    tueste = procesos["tueste"]
    story.append(
        _keep_section(
            "TUESTE",
        _key_value_table(
            [
                ["Peso Café Verde Total", _kg(tueste["entrada"]) if tueste["aplica"] else "Sin registros."],
                ["Peso Café Tostado Total", _kg(tueste["salida"]) if tueste["aplica"] else "Sin registros."],
            ],
            rl,
        ),
            styles,
        )
    )

    seleccion_tostado = procesos["seleccion_tostado"]
    story.append(
        _keep_section(
            "SELECCIÓN TUESTE",
        _key_value_table(
            [
                ["Peso Quaker", _kg(seleccion_tostado["peso_quaker"]) if seleccion_tostado["aplica"] else "Sin registros."],
                ["Peso Grupo 1", _kg(seleccion_tostado["peso_grupo1"]) if seleccion_tostado["aplica"] else "Sin registros."],
                ["Peso Grupo 2", _kg(seleccion_tostado["peso_grupo2"]) if seleccion_tostado["aplica"] else "Sin registros."],
                ["Peso Grupo 3", _kg(seleccion_tostado["peso_grupo3"]) if seleccion_tostado["aplica"] else "Sin registros."],
                [
                    "Total registrado",
                    _kg(seleccion_tostado["total_registrado"]) if seleccion_tostado["aplica"] else "Sin registros.",
                ],
            ],
            rl,
        ),
            styles,
        )
    )

    empaque = procesos["empaque"]
    story += _section("BOLSAS EMPACADAS", styles)
    story.append(
        _data_table(
            ["Empaque Café", "Tamaño Empaque", "Suministro", "Cantidad Bolsas Empacadas"],
            [
                [
                    _text(row.get("empaque_cafe__empaque_cafe"), "Sin tipo"),
                    _text(row.get("tamano_empaque__tamano_empaque"), "Sin tamaño"),
                    "Sí" if row.get("suministro") else "No",
                    _number(row.get("cantidad")),
                ]
                for row in empaque["bolsas_empacadas"]
            ]
            if empaque["aplica"]
            else [],
            "Sin registros.",
            styles,
            col_widths=[4.8 * cm, 3.45 * cm, 2.4 * cm, 4.35 * cm],
        )
    )

    story.append(
        _keep_section(
            "TOTALES DE EMPAQUE",
        _key_value_table(
            [
                ["Cantidad Bolsas Empacadas", _number(empaque["cantidad_bolsas_empacadas"]) if empaque["aplica"] else "Sin registros."],
                ["Total Paquetes", _number(empaque["total_paquetes"]) if empaque["aplica"] else "Sin registros."],
            ],
            rl,
        ),
            styles,
        )
    )

    story += _section("EMPAQUES SUMINISTRADOS POR EL CLIENTE", styles)
    story.append(
        _data_table(
            ["Empaque Café", "Tamaño Empaque", "Cantidad"],
            [
                [
                    _text(row.get("empaque_cafe__empaque_cafe"), "Sin tipo"),
                    _text(row.get("tamano_empaque__tamano_empaque"), "Sin tamaño"),
                    _number(row.get("cantidad")),
                ]
                for row in empaque["empaques_suministrados"]
            ]
            if empaque["suministro_cliente"]
            else [],
            "No se registraron empaques suministrados por el cliente.",
            styles,
            col_widths=[6 * cm, 5.25 * cm, 3.75 * cm],
        )
    )

    etiquetas = report["etiquetas"]
    story.append(
        _keep_section(
            "ETIQUETAS",
        _key_value_table(
            [
                ["Etiquetas Cliente", _number(etiquetas["cliente"])],
                ["Etiquetas INVIMA", _number(etiquetas["invima"])],
                ["Total Etiquetas", _number(etiquetas["total"])],
            ],
            rl,
        ),
            styles,
        )
    )

    if report["observaciones"]:
        story += _section("OBSERVACIONES", styles)
        for item in report["observaciones"]:
            story.append(Paragraph(f"<b>{_text(item['origen'])}:</b> {_text(item['texto'])}", styles["Normal"]))
            story.append(Spacer(1, 0.06 * cm))
    else:
        story.append(_keep_section("OBSERVACIONES", Paragraph("Sin observaciones.", styles["Muted"]), styles))

    doc.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()
