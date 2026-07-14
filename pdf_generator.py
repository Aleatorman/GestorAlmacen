import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def generar_pdf_picking(nombre_sucursal, encontrados, no_detectados, alertas):
    """
    Genera un PDF de picking optimizado con sección de firmas en cada hoja.
    """
    ahora = datetime.now()
    anio = ahora.strftime("%Y")
    mes = ahora.strftime("%m")
    fecha_hora = ahora.strftime("%Y-%m-%d_%H-%M-%S")
    
    directorio = os.path.join("pdfs", anio, mes)
    os.makedirs(directorio, exist_ok=True)
    ruta_pdf = os.path.abspath(os.path.join(directorio, f"{fecha_hora}_{nombre_sucursal.replace(' ', '_')}.pdf"))
    
    doc = SimpleDocTemplate(
        ruta_pdf, 
        pagesize=letter, 
        rightMargin=20, 
        leftMargin=20, 
        topMargin=20, 
        bottomMargin=80
    )
    elementos = []
    estilos = getSampleStyleSheet()
    
    estilo_titulo = ParagraphStyle('Titulo', parent=estilos['Heading2'], fontSize=12, spaceAfter=5)
    estilo_seccion = ParagraphStyle('Seccion', parent=estilos['Heading3'], fontSize=11, spaceAfter=2, spaceBefore=8)

    def dibujar_firmas(canvas, doc):
        canvas.saveState()
        ancho, alto = letter
        canvas.line(1 * inch, 0.7 * inch, 3.5 * inch, 0.7 * inch)
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(2.25 * inch, 0.55 * inch, "Firma Chofer (Entrega)")
        canvas.line(5 * inch, 0.7 * inch, 7.5 * inch, 0.7 * inch)
        canvas.drawCentredString(6.25 * inch, 0.55 * inch, "Firma Responsable Sucursal (Recibe)")
        canvas.drawRightString(ancho - 20, 20, f"Página {doc.page}")
        canvas.restoreState()

    fecha_str = ahora.strftime('%d/%m/%Y %H:%M')
    datos_header = [[
        Paragraph(f"<b>Orden Surtido - {nombre_sucursal}</b>", estilo_titulo), 
        Paragraph(f"<span color='gray'>{fecha_str}</span>", ParagraphStyle('R', alignment=2, fontSize=9))
    ]]
    tabla_header = Table(datos_header, colWidths=[350, 200])
    tabla_header.setStyle(TableStyle([('ALIGN', (1, 0), (1, 0), 'RIGHT'), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    elementos.append(tabla_header)
    elementos.append(Spacer(1, 5))

    def crear_tabla_productos(lista_productos):
        datos_tabla = [['[  ]', 'CÓDIGO', 'DESCRIPCIÓN', 'CANT.', 'GRUPO']]
        for p in lista_productos:
            datos_tabla.append(['[  ]', p['codigo'], p['descripcion'][:55], str(p['cantidad']), p['categoria'][:15]])
        
        tabla = Table(datos_tabla, colWidths=[30, 60, 310, 50, 100])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EAECEE")),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
        ]))
        return tabla

    if encontrados:
        prod_abajo = [p for p in encontrados if p['ubicacion'] == 'ABAJO']
        prod_arriba = [p for p in encontrados if p['ubicacion'] == 'ARRIBA']
        
        prod_abajo.sort(key=lambda x: (x['categoria'], x['descripcion']))
        prod_arriba.sort(key=lambda x: (x['categoria'], x['descripcion']))

        if prod_abajo:
            elementos.append(Paragraph("<b>📍 UBICACIÓN: ABAJO</b>", estilo_seccion))
            elementos.append(crear_tabla_productos(prod_abajo))

        if prod_arriba:
            elementos.append(Paragraph("<b>📍 UBICACIÓN: ARRIBA</b>", estilo_seccion))
            elementos.append(crear_tabla_productos(prod_arriba))

    if no_detectados:
        elementos.append(Spacer(1, 10))
        titulo_no_det = "<b>❌ NO ENCONTRADOS EN CATÁLOGO</b> <font size=8 color='#555555'>(errores de captura o nombre)</font>"
        elementos.append(Paragraph(titulo_no_det, estilo_seccion))
        
        datos_no_det = [['CÓDIGO', 'NOMBRE EN PEDIDO', 'CANT.']]
        for nd in no_detectados:
            datos_no_det.append([nd['codigo'], nd['descripcion'][:65], str(nd['cantidad'])])
        
        tabla_nd = Table(datos_no_det, colWidths=[80, 410, 60])
        tabla_nd.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FCF3CF")),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ]))
        elementos.append(tabla_nd)

    doc.build(elementos, onFirstPage=dibujar_firmas, onLaterPages=dibujar_firmas)
    return ruta_pdf

# MODIFICACIÓN: Nueva función para generar TXT en vez del cuadro de advertencia
def generar_txt_alertas(ruta_pdf, alertas, sucursal):
    """
    Crea un archivo .txt con las alertas de stock insuficiente en la misma carpeta del PDF.
    """
    if not alertas:
        return None
    
    ruta_txt = ruta_pdf.replace(".pdf", "_ALERTAS.txt")
    try:
        with open(ruta_txt, "w", encoding="utf-8") as f:
            f.write(f"=== REPORTE DE ALERTAS DE STOCK INSUFICIENTE ===\n")
            f.write(f"Sucursal: {sucursal}\n")
            f.write(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write("="*50 + "\n\n")
            f.write("Los siguientes productos solicitados superan la existencia actual en catálogo:\n\n")
            
            for a in alertas:
                f.write(f"• [Código: {a['codigo']}] {a['descripcion']}\n")
                f.write(f"  -> Solicitado por tienda : {a['cantidad']} unidades\n")
                f.write(f"  -> Existencia en sistema : {a['existencia']} unidades\n")
                f.write(f"  -> Faltante estimado     : {a['cantidad'] - a['existencia']} unidades\n")
                f.write("-" * 40 + "\n")
        return ruta_txt
    except Exception as e:
        print(f"Error generando archivo TXT de alertas: {e}")
        return None