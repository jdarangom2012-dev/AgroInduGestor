"""Exportación individual del análisis sensorial."""

from html import escape
from io import BytesIO

from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


DESCRIPTORES = {
    'floral': 'Floral', 'afrutado': 'Afrutado', 'bayas': 'Bayas',
    'frutas_deshidratadas': 'Frutas deshidratadas', 'citricos': 'Cítricos',
    'acido_fermentado': 'Ácido/Fermentado', 'acido': 'Ácido',
    'fermentado': 'Fermentado', 'verde_vegetal': 'Verde/Vegetal',
    'otra': 'Otra', 'quimico': 'Químico', 'humedad_tierra': 'Humedad/Tierra',
    'madera': 'Madera', 'tostado': 'Tostado', 'cereal': 'Cereal',
    'quemado': 'Quemado', 'tabaco': 'Tabaco', 'nueces_cacao': 'Nueces/Cacao',
    'nueces': 'Nueces', 'cacao': 'Cacao', 'especias': 'Especias',
    'dulce': 'Dulce', 'vainilla': 'Vainilla', 'azucar_morena': 'Azúcar morena',
}
GUSTOS = {'salado': 'Salado', 'acido': 'Ácido', 'dulce': 'Dulce', 'amargo': 'Amargo', 'umami': 'Umami'}
SENSACIONES = {
    'aspero': 'Áspero (Arenoso, Rugoso, Rasposo)', 'aceitoso': 'Aceitoso',
    'suave': 'Suave (Aterciopelado, Sedoso, Almibarado)',
    'astringente': 'Deja seca la boca (astringente)', 'metalico': 'Metálico',
}
DEFECTOS = {'mohoso': 'Mohoso', 'fenolico': 'Fenólico', 'papa': 'Papa'}


def _safe(value):
    return escape(str(value)) if value not in (None, '') else '-'


def _lista(values, labels):
    return ', '.join(labels.get(value, value) for value in values) or '-'


def _nivel(value):
    if value is None:
        return '-'
    numeric = float(value)
    if numeric <= 5:
        return 'Baja'
    if numeric <= 10:
        return 'Media'
    return 'Alta'


def _tabla_campos(rows, styles, widths=(5.2 * cm, 10.9 * cm)):
    data = [
        [Paragraph(f'<b>{_safe(label)}</b>', styles['SmallSensory']),
         Paragraph(_safe(value).replace('\n', '<br/>'), styles['SmallSensory'])]
        for label, value in rows
    ]
    table = Table(data, colWidths=list(widths), hAlign='LEFT')
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#d7dce4')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f7fa')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    return table


def render_analisis_sensorial_pdf(registro):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=1.7 * cm, leftMargin=1.7 * cm,
        topMargin=1.5 * cm, bottomMargin=1.6 * cm,
        title=f'Análisis Sensorial - {registro.muestra_numero}',
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='TitleSensory', parent=styles['Title'], textColor=colors.HexColor('#172132'),
        fontSize=18, leading=21, spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name='SectionSensory', parent=styles['Heading2'], textColor=colors.HexColor('#172132'),
        fontSize=12, leading=15, spaceBefore=11, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(name='BodySensory', parent=styles['BodyText'], leading=14, spaceAfter=5))
    styles.add(ParagraphStyle(name='SmallSensory', parent=styles['BodyText'], fontSize=8, leading=11))

    logo_path = finders.find('img/La_Central_IG_Logo.png')
    logo = Image(logo_path, width=2.4 * cm, height=2.7 * cm) if logo_path else Spacer(2.4 * cm, 2.7 * cm)
    heading = [
        Paragraph('ANÁLISIS SENSORIAL', styles['TitleSensory']),
        Paragraph(f'<b>Muestra:</b> {_safe(registro.muestra_numero)}', styles['BodySensory']),
        Paragraph(f'<b>Nombre:</b> {_safe(registro.nombre)}', styles['BodySensory']),
    ]
    header = Table([[logo, heading]], colWidths=[3.1 * cm, 13 * cm], hAlign='LEFT')
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    fecha = registro.fecha.strftime('%d/%m/%Y') if registro.fecha else '-'
    ingreso = registro.fecha_ingreso.strftime('%d/%m/%Y %H:%M') if registro.fecha_ingreso else '-'
    story = [header, HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e8bc2d')), Spacer(1, 0.25 * cm)]

    story.extend([
        Paragraph('Datos generales', styles['SectionSensory']),
        _tabla_campos([
            ('Fecha', fecha), ('Fecha de ingreso', ingreso), ('Objetivo', registro.objetivo),
            ('Nivel de tueste', registro.nivel_tueste),
        ], styles),
        Paragraph('Evaluación descriptiva', styles['SectionSensory']),
        _tabla_campos([
            ('Fragancia', f'{_safe(registro.intensidad_fragancia)} - {_nivel(registro.intensidad_fragancia)}'),
            ('Aroma', f'{_safe(registro.intensidad_aroma)} - {_nivel(registro.intensidad_aroma)}'),
            ('Descriptores fragancia/aroma', _lista(registro.lista_descriptores_fragancia_aroma, DESCRIPTORES)),
            ('Notas fragancia/aroma', registro.notas_fragancia_aroma),
            ('Sabor', f'{_safe(registro.intensidad_sabor)} - {_nivel(registro.intensidad_sabor)}'),
            ('Sabor residual', f'{_safe(registro.intensidad_sabor_residual)} - {_nivel(registro.intensidad_sabor_residual)}'),
            ('Descriptores de sabor', _lista(registro.lista_descriptores_sabor, DESCRIPTORES)),
            ('Gustos predominantes', _lista(registro.lista_gustos_predominantes, GUSTOS)),
            ('Notas de sabor', registro.notas_sabor),
            ('Acidez', f'{_safe(registro.intensidad_acidez)} - {_nivel(registro.intensidad_acidez)}'),
            ('Notas de acidez', registro.notas_acidez),
            ('Dulzor', f'{_safe(registro.intensidad_dulzor)} - {_nivel(registro.intensidad_dulzor)}'),
            ('Notas de dulzor', registro.notas_dulzor),
            ('Sensación en boca', f'{_safe(registro.intensidad_sensacion_boca)} - {_nivel(registro.intensidad_sensacion_boca)}'),
            ('Sensaciones', _lista(registro.lista_sensaciones_boca, SENSACIONES)),
            ('Notas sensación en boca', registro.notas_sensacion_boca),
        ], styles),
        Paragraph('Evaluación afectiva', styles['SectionSensory']),
        _tabla_campos([
            ('Fragancia', registro.calidad_fragancia), ('Aroma', registro.calidad_aroma),
            ('Notas fragancia/aroma', registro.notas_afectiva_fragancia_aroma),
            ('Sabor', registro.calidad_sabor), ('Sabor residual', registro.calidad_sabor_residual),
            ('Notas de sabor', registro.notas_afectiva_sabor),
            ('Acidez', registro.calidad_acidez), ('Notas de acidez', registro.notas_afectiva_acidez),
            ('Dulzor', registro.calidad_dulzor), ('Notas de dulzor', registro.notas_afectiva_dulzor),
            ('Sensación en boca', registro.calidad_sensacion_boca),
            ('Notas sensación en boca', registro.notas_afectiva_sensacion_boca),
            ('Impresión global', registro.impresion_global),
            ('Notas impresión global', registro.notas_impresion_global),
        ], styles),
        Paragraph('Resultado', styles['SectionSensory']),
        _tabla_campos([
            ('Notas de evaluación extrínseca', registro.notas_extrinseca),
            ('Puntaje', registro.puntaje_total),
            ('Tazas no uniformes', registro.tazas_no_uniformes),
            ('Tazas defectuosas', registro.tazas_defectuosas),
            ('Defectos', _lista(registro.lista_defectos_haberlo, DEFECTOS)),
        ], styles),
    ])

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#667085'))
        canvas.drawCentredString(A4[0] / 2, 0.8 * cm, f'Página {document.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
