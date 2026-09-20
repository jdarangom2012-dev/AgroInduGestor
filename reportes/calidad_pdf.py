"""Exportación de las muestras de laboratorio de un cliente."""

from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _safe(value):
    return escape(str(value)) if value not in (None, '') else '-'


def render_calidad_pdf(cliente, registros):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=1.7*cm, leftMargin=1.7*cm,
                            topMargin=1.6*cm, bottomMargin=1.6*cm, title='Reporte de Calidad')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SectionQuality', parent=styles['Heading2'], textColor=colors.HexColor('#172132'), spaceBefore=11, spaceAfter=6))
    styles.add(ParagraphStyle(name='BodyQuality', parent=styles['BodyText'], leading=14, spaceAfter=5))
    styles.add(ParagraphStyle(name='SmallQuality', parent=styles['BodyText'], fontSize=8, leading=11))
    story = [Paragraph('REPORTE DE CALIDAD', styles['Title']),
             Paragraph(f'<b>Cliente:</b> {_safe(cliente)}', styles['BodyQuality']),
             Paragraph(f'<b>Total de muestras:</b> {len(registros)}', styles['BodyQuality']),
             HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e8bc2d')), Spacer(1, 0.3*cm)]

    for index, registro in enumerate(registros):
        if index:
            story.append(PageBreak())
        story.append(Paragraph(f'Muestra #{_safe(registro.muestra_numero or registro.pk)} - Orden {_safe(registro.orden)}', styles['SectionQuality']))
        recibida = registro.fecha_recibido.strftime('%d/%m/%Y') if registro.fecha_recibido else '-'
        story.append(Paragraph(f'Ingreso: {registro.fecha_ingreso:%d/%m/%Y %H:%M} | Recibida: {recibida}', styles['BodyQuality']))
        tipo = ' / '.join(part for part, active in [('Sencilla', registro.sencilla), ('Q Grader', registro.q_grader)] if active) or '-'
        fields = [
            ('Tipo', tipo), ('Variedad', registro.variedad), ('Proceso', registro.proceso),
            ('Origen', registro.origen), ('Altura', registro.altura),
            ('Peso pergamino', registro.peso_pergamino), ('Peso verde', registro.peso_verde),
            ('Peso excelsio', registro.peso_excelsio), ('Humedad', registro.humedad),
            ('Densidad', registro.densidad), ('Factor', registro.factor),
            ('Peso tostado', registro.peso_tostado),
        ]
        cells = [[Paragraph(f'<b>{_safe(label)}</b>', styles['SmallQuality']), Paragraph(_safe(value), styles['SmallQuality'])] for label, value in fields]
        table = Table(cells, colWidths=[5*cm, 11.1*cm], hAlign='LEFT')
        table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#d7dce4')),
                                   ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f7fa')),
                                   ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                   ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
        story.append(table)
        if registro.notas:
            story.extend([Paragraph('Notas', styles['SectionQuality']), Paragraph(_safe(registro.notas).replace('\n', '<br/>'), styles['BodyQuality'])])
        lecturas = registro.lecturas_tostion
        if lecturas:
            story.append(Paragraph('Tostión', styles['SectionQuality']))
            rows = [[Paragraph(f'<font color="white"><b>{x}</b></font>', styles['SmallQuality']) for x in ('Tiempo', 'Temperatura', 'Evento')]]
            rows.extend([[Paragraph(_safe(row.get(key)), styles['SmallQuality']) for key in ('tiempo', 'temperatura', 'evento')] for row in lecturas])
            readings = Table(rows, colWidths=[3*cm, 4*cm, 9.1*cm], repeatRows=1, hAlign='LEFT')
            readings.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#172132')),
                                          ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                                          ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#d7dce4')),
                                          ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                          ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
            story.append(readings)
        if registro.observaciones:
            story.extend([Paragraph('Observaciones', styles['SectionQuality']), Paragraph(_safe(registro.observaciones).replace('\n', '<br/>'), styles['BodyQuality'])])
    if not registros:
        story.append(Paragraph('No hay muestras registradas para este cliente.', styles['BodyQuality']))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#667085'))
        canvas.drawCentredString(A4[0] / 2, 0.8*cm, f'Página {document.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
