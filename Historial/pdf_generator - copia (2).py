import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generar_pdf_picking(nombre_sucursal, encontrados, no_detectados, alertas):
    """
    Genera un PDF de picking ultra-optimizado para ahorrar espacio y tinta.
    """
    # 1. Crear directorios
    ahora = datetime.now()
    anio = ahora.strftime("%Y")
    mes = ahora.strftime("%m")
    fecha_hora = ahora.strftime("%Y-%m-%d_%H-%M-%S")
    
    directorio = os.path.join("pdfs", anio, mes)
    os.makedirs(directorio, exist_ok=True)
    ruta_pdf = os.path.abspath(os.path.join(directorio, f"{fecha_hora}_{nombre_sucursal.replace(' ', '_')}.pdf"))
    
    # 2. Configurar el documento PDF (Márgenes muy reducidos para aprovechar la hoja)
    doc = SimpleDocTemplate(ruta_pdf, pagesize=letter, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elementos = []
    estilos = getSampleStyleSheet()
    
    # Estilos compactos
    estilo_titulo = ParagraphStyle('Titulo', parent=estilos['Heading2'], fontSize=12, spaceAfter=5, textColor=colors.black)
    estilo_seccion = ParagraphStyle('Seccion', parent=estilos['Heading3'], fontSize=11, spaceAfter=2, spaceBefore=8, textColor=colors.black)

    # 3. Encabezado compacto (Título a la izquierda, Fecha a la derecha)
    fecha_str = ahora.strftime('%d/%m/%Y %H:%M')
    datos_header = [[
        Paragraph(f"<b>Orden Surtido - {nombre_sucursal}</b>", estilo_titulo), 
        Paragraph(f"<span color='gray'>{fecha_str}</span>", ParagraphStyle('R', alignment=2, fontSize=9))
    ]]
    tabla_header = Table(datos_header, colWidths=[350, 200])
    tabla_header.setStyle(TableStyle([('ALIGN', (1, 0), (1, 0), 'RIGHT'), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]))
    elementos.append(tabla_header)
    elementos.append(Spacer(1, 5))

    # --- FUNCIÓN INTERNA PARA CREAR TABLAS ---
    def crear_tabla_productos(lista_productos):
        # El encabezado ahora tiene la columna "GRUPO"
        datos_tabla = [['[  ]', 'CÓDIGO', 'DESCRIPCIÓN', 'CANT.', 'GRUPO']]
        for p in lista_productos:
            datos_tabla.append(['[  ]', p['codigo'], p['descripcion'][:55], str(p['cantidad']), p['categoria'][:15]])
        
        # Ajustamos los anchos para que quepa la nueva columna
        tabla = Table(datos_tabla, colWidths=[30, 60, 310, 50, 100])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EAECEE")), # Gris muy claro para ahorrar tinta
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (1, -1), 'CENTER'), # Checkbox y Código centrados
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),   # Descripción izq
            ('ALIGN', (3, 0), (3, -1), 'CENTER'), # Cantidad centrada
            ('ALIGN', (4, 0), (4, -1), 'LEFT'),   # Grupo izq
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),    # Letra un poco más pequeña pero legible
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
        ]))
        return tabla

    # 4. Procesar productos ENCONTRADOS (Separar Arriba/Abajo y ordenar por Grupo)
    if encontrados:
        prod_abajo = [p for p in encontrados if p['ubicacion'] == 'ABAJO']
        prod_arriba = [p for p in encontrados if p['ubicacion'] == 'ARRIBA']
        
        # Ordenamos alfabéticamente por Grupo y luego por Descripción
        prod_abajo.sort(key=lambda x: (x['categoria'], x['descripcion']))
        prod_arriba.sort(key=lambda x: (x['categoria'], x['descripcion']))

        if prod_abajo:
            elementos.append(Paragraph("<b>📍 UBICACIÓN: ABAJO</b>", estilo_seccion))
            elementos.append(crear_tabla_productos(prod_abajo))
            elementos.append(Spacer(1, 5))

        if prod_arriba:
            elementos.append(Paragraph("<b>📍 UBICACIÓN: ARRIBA</b>", estilo_seccion))
            elementos.append(crear_tabla_productos(prod_arriba))
            elementos.append(Spacer(1, 5))

    # 5. Sección de Productos No Detectados (Compacta y con el texto solicitado)
    if no_detectados:
        elementos.append(Spacer(1, 10))
        titulo_no_det = "<b>❌ NO ENCONTRADOS EN CATÁLOGO</b> <font size=9 color='#555555'><i>(por errores en la captura o por errores en el nombre en el sistema y el pedido)</i></font>"
        elementos.append(Paragraph(titulo_no_det, estilo_seccion))
        
        datos_no_det = [['CÓDIGO', 'NOMBRE EN PEDIDO', 'CANT.']]
        for nd in no_detectados:
            datos_no_det.append([nd['codigo'], nd['descripcion'][:65], str(nd['cantidad'])])
        
        tabla_nd = Table(datos_no_det, colWidths=[80, 410, 60])
        tabla_nd.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FCF3CF")),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.gray),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ]))
        elementos.append(tabla_nd)

    # Generar el documento físico
    doc.build(elementos)
    return ruta_pdf