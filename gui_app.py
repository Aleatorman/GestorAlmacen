import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget, 
                               QLabel, QPushButton, QMessageBox, QTextEdit, 
                               QFileDialog, QComboBox, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QInputDialog, QHeaderView, QDialog,
                               QDateEdit, QAbstractItemView)
from PySide6.QtCore import Qt, QDate

import db_manager
import excel_processor
import pdf_generator

# NUEVA CLASE: Ventana modal para configurar exclusivamente productos nuevos detectados
class DialogConfigurarNuevos(QDialog):
    def __init__(self, nuevos_productos, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Configuración Rápida - Productos Nuevos Detectados")
        self.resize(750, 450)
        self.nuevos_productos = nuevos_productos
        
        layout = QVBoxLayout(self)
        info_lbl = QLabel(
            f"<b>Se detectaron {len(nuevos_productos)} productos nuevos</b> que no existían en la base de datos.<br>"
            "Por defecto se han asignado a <b>ABAJO</b>. Si alguno va <b>ARRIBA</b>, cámbialo aquí directamente:"
        )
        layout.addWidget(info_lbl)
        layout.addSpacing(10)
        
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["Código", "Descripción", "Grupo / Categoría", "Ubicación en Almacén"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.tabla)
        
        self.cargar_tabla()
        
        btn_listo = QPushButton("✅ Guardar Ubicaciones y Terminar")
        btn_listo.setStyleSheet("background-color: #28B463; color: white; font-weight: bold; padding: 10px; font-size: 14px;")
        btn_listo.clicked.connect(self.accept)
        layout.addWidget(btn_listo)

    def cargar_tabla(self):
        self.tabla.setRowCount(0)
        for fila, (cod, desc, cat) in enumerate(self.nuevos_productos):
            self.tabla.insertRow(fila)
            item_cod = QTableWidgetItem(cod)
            item_cod.setFlags(item_cod.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(fila, 0, item_cod)
            
            item_desc = QTableWidgetItem(desc)
            item_desc.setFlags(item_desc.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(fila, 1, item_desc)
            
            item_cat = QTableWidgetItem(cat)
            item_cat.setFlags(item_cat.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(fila, 2, item_cat)
            
            combo_ubi = QComboBox()
            combo_ubi.addItems(["ABAJO", "ARRIBA"])
            combo_ubi.setCurrentText("ABAJO")  # Por defecto ABAJO
            combo_ubi.currentTextChanged.connect(lambda texto, c=cod: db_manager.set_ubicacion_producto(c, texto))
            self.tabla.setCellWidget(fila, 3, combo_ubi)

class DialogSucursales(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Sucursales")
        self.resize(500, 400)
        layout = QVBoxLayout(self)
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["ID", "Nombre de Sucursal", "Estado"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.cargar_tabla()
        layout.addWidget(self.tabla)
        fila_btn = QHBoxLayout()
        btn_add = QPushButton("➕ Agregar Nueva")
        btn_add.clicked.connect(self.agregar_sucursal)
        btn_toggle = QPushButton("🔄 Activar/Desactivar Seleccionada")
        btn_toggle.clicked.connect(self.toggle_sucursal)
        fila_btn.addWidget(btn_add)
        fila_btn.addWidget(btn_toggle)
        layout.addLayout(fila_btn)

    def cargar_tabla(self):
        self.tabla.setRowCount(0)
        sucursales = db_manager.get_sucursales(solo_activas=False)
        for fila_num, row_data in enumerate(sucursales):
            self.tabla.insertRow(fila_num)
            self.tabla.setItem(fila_num, 0, QTableWidgetItem(str(row_data[0])))
            self.tabla.setItem(fila_num, 1, QTableWidgetItem(row_data[1]))
            estado = "✅ Activa" if row_data[2] == 1 else "❌ Inactiva"
            self.tabla.setItem(fila_num, 2, QTableWidgetItem(estado))

    def agregar_sucursal(self):
        nombre, ok = QInputDialog.getText(self, "Nueva Sucursal", "Nombre de la sucursal:")
        if ok and nombre.strip():
            res = db_manager.agregar_sucursal(nombre.strip().upper())
            if res == True: self.cargar_tabla()
            elif res == "Duplicada": QMessageBox.warning(self, "Atención", "Ya existe una sucursal con ese nombre.")

    def toggle_sucursal(self):
        fila = self.tabla.currentRow()
        if fila < 0: return
        id_suc = int(self.tabla.item(fila, 0).text())
        estado_actual = 1 if "Activa" in self.tabla.item(fila, 2).text() else 0
        if db_manager.toggle_sucursal(id_suc, estado_actual): self.cargar_tabla()

class DialogUbicaciones(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Almacén (Arriba/Abajo)")
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        panel_top = QHBoxLayout()
        panel_top.addWidget(QLabel("<b>1. Selecciona el Grupo:</b>"))
        self.combo_grupo = QComboBox()
        self.combo_grupo.addItems(db_manager.get_categorias())
        self.combo_grupo.currentTextChanged.connect(self.cargar_tabla_productos)
        panel_top.addWidget(self.combo_grupo, stretch=1)
        layout.addLayout(panel_top)
        layout.addWidget(QLabel("<b>2. Aplica a todo el grupo o cambia uno por uno:</b>"))
        panel_botones = QHBoxLayout()
        btn_todo_arriba = QPushButton("⬆️ Mover Todo a ARRIBA")
        btn_todo_arriba.setStyleSheet("background-color: #D6EAF8; font-weight: bold;")
        btn_todo_arriba.clicked.connect(lambda: self.aplicar_a_todo("ARRIBA"))
        btn_todo_abajo = QPushButton("⬇️ Mover Todo a ABAJO")
        btn_todo_abajo.setStyleSheet("background-color: #FCF3CF; font-weight: bold;")
        btn_todo_abajo.clicked.connect(lambda: self.aplicar_a_todo("ABAJO"))
        panel_botones.addWidget(btn_todo_arriba)
        panel_botones.addWidget(btn_todo_abajo)
        layout.addLayout(panel_botones)
        
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Código", "Producto", "Ubicación en Almacén"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.tabla)
        self.cargar_tabla_productos()

    def cargar_tabla_productos(self):
        grupo = self.combo_grupo.currentText()
        if not grupo: return
        productos = db_manager.get_productos_por_categoria(grupo)
        self.tabla.setRowCount(0)
        for fila, prod in enumerate(productos):
            self.tabla.insertRow(fila)
            item_codigo = QTableWidgetItem(prod[0])
            item_codigo.setFlags(item_codigo.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(fila, 0, item_codigo)
            item_desc = QTableWidgetItem(prod[1])
            item_desc.setFlags(item_desc.flags() & ~Qt.ItemIsEditable)
            self.tabla.setItem(fila, 1, item_desc)
            
            combo_ubi = QComboBox()
            combo_ubi.addItems(["ABAJO", "ARRIBA"])  # MODIFICADO: Orden default ABAJO primero
            combo_ubi.setCurrentText(prod[2])
            combo_ubi.currentTextChanged.connect(lambda texto, cod=prod[0]: db_manager.set_ubicacion_producto(cod, texto))
            self.tabla.setCellWidget(fila, 2, combo_ubi)

    def aplicar_a_todo(self, ubicacion):
        grupo = self.combo_grupo.currentText()
        if not grupo: return
        resp = QMessageBox.question(self, "Confirmar", f"¿Mover todo lo de '{grupo}' a {ubicacion}?", QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            db_manager.set_ubicacion_categoria(grupo, ubicacion)
            self.cargar_tabla_productos()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gestión de Pedidos Almacén v1.1")
        self.resize(900, 650)
        self.ruta_excel_actual = ""
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout_principal = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        self.tab_procesar = QWidget()
        self.tab_catalogo = QWidget()
        self.tab_config = QWidget()
        self.tab_historico = QWidget()
        
        self.tabs.addTab(self.tab_procesar, "1. Procesar Pedido")
        self.tabs.addTab(self.tab_catalogo, "2. Actualizar Catálogo")
        self.tabs.addTab(self.tab_config, "3. Configuración")
        self.tabs.addTab(self.tab_historico, "4. Histórico y Reportes")
        
        layout_principal.addWidget(self.tabs)
        
        self.setup_tab_catalogo()
        self.setup_tab_procesar()
        self.setup_tab_config()
        self.setup_tab_historico()
        
        self.tabs.currentChanged.connect(self.al_cambiar_pestana)

    def setup_tab_procesar(self):
        layout = QVBoxLayout(self.tab_procesar)
        layout.addWidget(QLabel("<b>1. Seleccionar archivo Excel de la sucursal (Pedido):</b>"))
        fila_archivo = QHBoxLayout()
        self.lbl_ruta_excel = QLabel("Ningún archivo seleccionado...")
        self.lbl_ruta_excel.setStyleSheet("border: 1px solid gray; padding: 5px;")
        btn_examinar = QPushButton("Examinar...")
        btn_examinar.clicked.connect(self.seleccionar_archivo) 
        fila_archivo.addWidget(self.lbl_ruta_excel, stretch=1)
        fila_archivo.addWidget(btn_examinar)
        layout.addLayout(fila_archivo)
        
        layout.addSpacing(15)
        layout.addWidget(QLabel("<b>2. Seleccionar Sucursal:</b>"))
        self.combo_sucursal = QComboBox()
        self.cargar_sucursales_combo()
        layout.addWidget(self.combo_sucursal)
        
        layout.addSpacing(15)
        self.btn_procesar = QPushButton("⚙️ PROCESAR PEDIDO Y GENERAR PDF")
        self.btn_procesar.setStyleSheet("background-color: #28B463; color: white; font-weight: bold; font-size: 16px; padding: 15px;")
        self.btn_procesar.clicked.connect(self.ejecutar_procesamiento)
        layout.addWidget(self.btn_procesar)
        
        self.log_procesar = QTextEdit()
        self.log_procesar.setReadOnly(True)
        layout.addWidget(self.log_procesar)

    def setup_tab_catalogo(self):
        layout = QVBoxLayout(self.tab_catalogo)
        instrucciones = QLabel(
            "<b>INSTRUCCIONES:</b><br>"
            "1. Abre el SRV y ve a PRODUCTOS'.<br>"
            "2. Selecciona toda la tabla.<br>"
            "3. Presiona <b>Ctrl+C</b> para copiar.<br>"
            "4. Presiona el botón de abajo."
        )
        instrucciones.setStyleSheet("font-size: 14px;")
        layout.addWidget(instrucciones)
        
        self.btn_pegar = QPushButton("📋 PEGAR CATÁLOGO DESDE PORTAPAPELES")
        self.btn_pegar.setStyleSheet("background-color: #2E86C1; color: white; font-weight: bold; font-size: 16px; padding: 15px;")
        self.btn_pegar.clicked.connect(self.procesar_portapapeles)
        layout.addWidget(self.btn_pegar)
        self.log_catalogo = QTextEdit()
        self.log_catalogo.setReadOnly(True)
        layout.addWidget(self.log_catalogo)

    def setup_tab_config(self):
        layout = QVBoxLayout(self.tab_config)
        layout.setAlignment(Qt.AlignCenter)
        titulo = QLabel("Panel de Control del Sistema")
        titulo.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)
        layout.addSpacing(30)
        
        btn_sucursales = QPushButton("🏢 Gestionar Sucursales")
        btn_sucursales.setStyleSheet("font-size: 16px; padding: 20px; background-color: #EAEDED;")
        btn_sucursales.clicked.connect(lambda: DialogSucursales(self).exec())
        layout.addWidget(btn_sucursales)
        layout.addSpacing(15)
        
        btn_ubicaciones = QPushButton("📦 Configurar Almacén (Arriba / Abajo)")
        btn_ubicaciones.setStyleSheet("font-size: 16px; padding: 20px; background-color: #EAEDED;")
        btn_ubicaciones.clicked.connect(lambda: DialogUbicaciones(self).exec())
        layout.addWidget(btn_ubicaciones)

    def setup_tab_historico(self):
        layout = QVBoxLayout(self.tab_historico)
        fila_filtros = QHBoxLayout()
        fila_filtros.addWidget(QLabel("Desde:"))
        self.date_desde = QDateEdit()
        self.date_desde.setCalendarPopup(True)
        self.date_desde.setDate(QDate.currentDate().addDays(-30))
        fila_filtros.addWidget(self.date_desde)
        fila_filtros.addWidget(QLabel("Hasta:"))
        self.date_hasta = QDateEdit()
        self.date_hasta.setCalendarPopup(True)
        self.date_hasta.setDate(QDate.currentDate())
        fila_filtros.addWidget(self.date_hasta)
        fila_filtros.addWidget(QLabel("Sucursal:"))
        self.combo_filtro_suc = QComboBox()
        self.cargar_filtro_sucursales()
        fila_filtros.addWidget(self.combo_filtro_suc)
        btn_buscar = QPushButton("🔍 Buscar")
        btn_buscar.clicked.connect(self.buscar_historial)
        fila_filtros.addWidget(btn_buscar)
        layout.addLayout(fila_filtros)
        
        self.tabla_historial = QTableWidget()
        self.tabla_historial.setColumnCount(8)
        self.tabla_historial.setHorizontalHeaderLabels([
            "ID", "Fecha de Proceso", "Sucursal", "Archivo Procesado", 
            "Cant. Productos", "No Detectados", "Alertas", "Ruta PDF"
        ])
        self.tabla_historial.setColumnHidden(0, True) 
        self.tabla_historial.setColumnHidden(7, True) 
        self.tabla_historial.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabla_historial.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla_historial.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.tabla_historial)
        
        # MODIFICACIÓN: Dos botones abajo (PDF y TXT Alertas)
        fila_botones_historial = QHBoxLayout()
        btn_abrir_pdf = QPushButton("📄 Abrir PDF de Pedido")
        btn_abrir_pdf.setStyleSheet("background-color: #2E86C1; color: white; font-weight: bold; padding: 12px; font-size: 14px;")
        btn_abrir_pdf.clicked.connect(self.abrir_pdf_historial)
        
        btn_abrir_txt = QPushButton("⚠️ Ver Alertas TXT")
        btn_abrir_txt.setStyleSheet("background-color: #F39C12; color: white; font-weight: bold; padding: 12px; font-size: 14px;")
        btn_abrir_txt.clicked.connect(self.abrir_txt_historial)
        
        fila_botones_historial.addWidget(btn_abrir_pdf)
        fila_botones_historial.addWidget(btn_abrir_txt)
        layout.addLayout(fila_botones_historial)

    def al_cambiar_pestana(self, index):
        if index == 0: self.cargar_sucursales_combo()
        elif index == 3: self.cargar_filtro_sucursales()

    def cargar_sucursales_combo(self):
        self.combo_sucursal.clear()
        sucursales = db_manager.get_sucursales(solo_activas=True)
        if not sucursales: self.combo_sucursal.addItem("No hay sucursales activas")
        for suc in sucursales: self.combo_sucursal.addItem(suc[1], userData=suc[0])

    def cargar_filtro_sucursales(self):
        self.combo_filtro_suc.clear()
        self.combo_filtro_suc.addItem("Todas las sucursales", userData=None)
        sucursales = db_manager.get_sucursales(solo_activas=False)
        for suc in sucursales: self.combo_filtro_suc.addItem(suc[1], userData=suc[0])

    def procesar_portapapeles(self):
        self.log_catalogo.append("Leyendo portapapeles...")
        exito, resultado = excel_processor.leer_catalogo_portapapeles()
        if not exito:
            QMessageBox.critical(self, "Error", resultado)
            return
        
        # MODIFICACIÓN: upsert_catalogo ahora devuelve exito y la lista de nuevos productos
        exito_bd, nuevos_productos = db_manager.upsert_catalogo(resultado)
        if exito_bd:
            self.log_catalogo.append(f"✅ Catálogo guardado en BD con éxito. ({len(resultado)} filas procesadas)")
            
            # Si se encontraron productos nuevos, preguntamos al usuario si desea configurarlos
            if nuevos_productos:
                resp = QMessageBox.question(
                    self, 
                    "🆕 Productos Nuevos Detectados", 
                    f"Se han registrado {len(nuevos_productos)} productos nuevos en el catálogo.\n\n"
                    "Por defecto se enviaron al almacén 'ABAJO'. ¿Deseas revisar si alguno va ARRIBA ahora mismo?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if resp == QMessageBox.Yes:
                    dialogo = DialogConfigurarNuevos(nuevos_productos, self)
                    dialogo.exec()
            else:
                QMessageBox.information(self, "Éxito", "Catálogo actualizado sin productos nuevos detectados.")
        else:
            QMessageBox.critical(self, "Error", "Fallo al guardar BD.")

    def seleccionar_archivo(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar Pedido", "", "Archivos Excel (*.xlsx *.xls)")
        if ruta:
            self.ruta_excel_actual = ruta
            self.lbl_ruta_excel.setText(ruta)
            self.log_procesar.append(f"Archivo seleccionado: {ruta}")

    def ejecutar_procesamiento(self):
        if not self.ruta_excel_actual: return QMessageBox.warning(self, "Atención", "Selecciona el archivo primero.")
        if self.combo_sucursal.currentText() == "No hay sucursales activas": return QMessageBox.warning(self, "Atención", "Agrega una sucursal primero.")
            
        sucursal = self.combo_sucursal.currentText()
        id_sucursal = self.combo_sucursal.currentData()
        self.log_procesar.append(f"\n--- Iniciando proceso para {sucursal} ---")
        
        exito, resultado = excel_processor.leer_pedido_excel(self.ruta_excel_actual)
        if not exito: return QMessageBox.critical(self, "Error", resultado)
            
        exito_bd, encontrados, no_detectados, alertas = db_manager.procesar_pedido_contra_bd(resultado)
        if not exito_bd: return QMessageBox.critical(self, "Error BD", "Error al consultar BD.")
            
        self.log_procesar.append(f"✅ Encontrados: {len(encontrados)} | ❌ No detectados: {len(no_detectados)} | ⚠️ Alertas: {len(alertas)}")
        
        try:
            # Generamos el PDF
            ruta_pdf = pdf_generator.generar_pdf_picking(sucursal, encontrados, no_detectados, alertas)
            
            # MODIFICACIÓN: Si hay alertas, generamos el archivo TXT silencioso sin cuadro intrusivo
            ruta_txt_alertas = None
            if alertas:
                ruta_txt_alertas = pdf_generator.generar_txt_alertas(ruta_pdf, alertas, sucursal)
                self.log_procesar.append(f"⚠️ Se generó archivo de alertas TXT: {os.path.basename(ruta_txt_alertas)}")

            nombre_archivo = os.path.basename(self.ruta_excel_actual)
            total_pedidos = len(encontrados) + len(no_detectados)
            db_manager.guardar_historial_pedido(id_sucursal, nombre_archivo, ruta_pdf, total_pedidos, len(no_detectados), len(alertas))
            
            os.startfile(ruta_pdf)
            
            # Mensaje final agradable indicando si hubo alertas
            msj_final = "¡PDF de surtido generado y guardado en el histórico con éxito!"
            if alertas:
                msj_final += f"\n\n⚠️ NOTA: Se detectaron {len(alertas)} productos con stock insuficiente. Se creó un archivo TXT en la misma carpeta del PDF para su revisión."
            
            QMessageBox.information(self, "Terminado", msj_final)
            
        except Exception as e:
            QMessageBox.critical(self, "Error PDF", f"Error: {str(e)}")

    def buscar_historial(self):
        fecha_ini = self.date_desde.date().toString("yyyy-MM-dd")
        fecha_fin = self.date_hasta.date().toString("yyyy-MM-dd")
        id_suc = self.combo_filtro_suc.currentData()
        resultados = db_manager.obtener_historial_pedidos(fecha_ini, fecha_fin, id_suc)
        self.tabla_historial.setRowCount(0)
        for fila, row_data in enumerate(resultados):
            self.tabla_historial.insertRow(fila)
            for col in range(8):
                item = QTableWidgetItem(str(row_data[col]))
                self.tabla_historial.setItem(fila, col, item)

    def abrir_pdf_historial(self):
        fila = self.tabla_historial.currentRow()
        if fila < 0: return QMessageBox.warning(self, "Atención", "Selecciona un pedido de la tabla.")
        ruta_pdf = self.tabla_historial.item(fila, 7).text()
        if os.path.exists(ruta_pdf): os.startfile(ruta_pdf)
        else: QMessageBox.critical(self, "Error", "Archivo PDF no encontrado en el disco.")

    # MODIFICACIÓN: Función para abrir el TXT de alertas desde la tabla de historial
    def abrir_txt_historial(self):
        fila = self.tabla_historial.currentRow()
        if fila < 0: return QMessageBox.warning(self, "Atención", "Selecciona un pedido de la tabla.")
        
        alertas_num = int(self.tabla_historial.item(fila, 6).text())
        if alertas_num == 0:
            return QMessageBox.information(self, "Sin Alertas", "Este pedido no registró alertas de stock insuficiente.")
            
        ruta_pdf = self.tabla_historial.item(fila, 7).text()
        ruta_txt = ruta_pdf.replace(".pdf", "_ALERTAS.txt")
        
        if os.path.exists(ruta_txt):
            os.startfile(ruta_txt)
        else:
            QMessageBox.warning(self, "Aviso", "El archivo PDF original se generó sin archivo TXT adjunto o fue eliminado del disco.")