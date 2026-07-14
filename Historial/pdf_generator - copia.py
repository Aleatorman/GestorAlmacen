import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generar_pdf_picking(nombre_sucursal, encontrados, no_detectados, alertas):
    """
    Genera un PDF de picking agrupado por categoría y ubicación.
    Devuelve la ruta absoluta del PDF generado.
    """
    # 1. Crear directorios para organizar los PDFs (ej. pdfs/2026/05/)
    ahora = datetime.now()
    anio = ahora.strftime("%Y")
    mes = ahora.strftime("%m")
    fecha_hora = ahora.strftime("%Y-%m-%d_%H-%M-%S")
    
    directorio = os.path.join("pdfs", anio, mes)
    os.makedirs(directorio, exist_ok=True)
    
    # Nombre del archivo
    nombre_archivo = f"{fecha_hora}_{nombre_sucursal.replace(' ', '_')}.pdf"
    ruta_pdf = os.path.abspath(os.path.join(directorio, nombre_archivo))
    
    # 2. Configurar el documento PDF
    doc = SimpleDocTemplate(ruta_pdf, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos = []
    estilos = getSampleStyleSheet()
    
    # Estilos personalizados
    estilo_titulo = ParagraphStyle('Titulo', parent=estilos['Heading1'], fontSize=16, spaceAfter=15, textColor=colors.HexColor("#2E86C1"))
    estilo_categoria = ParagraphStyle('Categoria', parent=estilos['Heading2'], fontSize=14, spaceAfter=10, spaceBefore=15)
    estilo_ubicacion = ParagraphStyle('Ubicacion', parent=estilos['Heading3'], fontSize=12, textColor=colors.gray)

    # Título principal
    elementos.append(Paragraph(f"Orden de Surtido - Sucursal: {nombre_sucursal}", estilo_titulo))
    elementos.append(Paragraph(f"Fecha de impresión: {ahora.strftime('%d/%m/%Y %H:%M')}", estilos['Normal']))
    elementos.append(Spacer(1, 15))

    # 3. Procesar productos ENCONTRADOS (Agrupar por Categoría y Ubicación)
    if encontrados:
        # Agrupar datos: diccionario[categoria][ubicacion] = [lista de productos]
        grupos = {}
        for prod in encontrados:
            cat = prod['categoria']
            ubi = prod['ubicacion']
            if cat not in grupos:
                grupos[cat] = {'ARRIBA': [], 'ABAJO': []}
            grupos[cat][ubi].append(prod)

        for cat in sorted(grupos.keys()):
            elementos.append(Paragraph(f"📦 Categoría: {cat}", estilo_categoria))
            
            for ubi in ['ABAJO', 'ARRIBA']: # Orden sugerido: primero recolectar lo de abajo, luego arriba
                productos_ubi = grupos[cat][ubi]
                if not productos_ubi:
                    continue
                    
                elementos.append(Paragraph(f"Ubicación: {ubi}", estilo_ubicacion))
                
                # Crear tabla para esta ubicación
                datos_tabla = [['[   ]', 'CÓDIGO', 'DESCRIPCIÓN', 'CANTIDAD PEDIDA']]
                for p in productos_ubi:
                    # El '[   ]' es la cajita física para que el almacenista palomee
                    datos_tabla.append(['[   ]', p['codigo'], p['descripcion'], str(p['cantidad'])])
                
                tabla = Table(datos_tabla, colWidths=[40, 80, 320, 110])
                tabla.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('ALIGN', (2, 1), (2, -1), 'LEFT'), # Descripción alineada a la izquierda
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                elementos.append(tabla)
                elementos.append(Spacer(1, 10))

    # 4. Sección de Alertas (Falta de Existencia)
    if alertas:
        elementos.append(Spacer(1, 20))
        elementos.append(Paragraph("⚠️ ALERTAS DE RESURTIDO (Stock Insuficiente)", estilo_titulo))
        datos_alertas = [['CÓDIGO', 'DESCRIPCIÓN', 'PEDIDO', 'EN EXISTENCIA']]
        for a in alertas:
            datos_alertas.append([a['codigo'], a['descripcion'], str(a['cantidad']), str(a['existencia'])])
        
        tabla_alertas = Table(datos_alertas, colWidths=[80, 270, 100, 100])
        tabla_alertas.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FADBD8")), # Rojo claro
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elementos.append(tabla_alertas)

    # 5. Sección de Productos No Detectados
    if no_detectados:
        elementos.append(Spacer(1, 20))
        elementos.append(Paragraph("❌ PRODUCTOS NO RECONOCIDOS EN CATÁLOGO", estilo_titulo))
        datos_no_det = [['CÓDIGO ENVIADO', 'NOMBRE EN EXCEL', 'CANTIDAD PEDIDA']]
        for nd in no_detectados:
            datos_no_det.append([nd['codigo'], nd['descripcion'], str(nd['cantidad'])])
        
        tabla_nd = Table(datos_no_det, colWidths=[120, 310, 120])
        tabla_nd.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FCF3CF")), # Amarillo claro
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        elementos.append(tabla_nd)

    # Generar el documento físico
    doc.build(elementos)
    return ruta_pdf