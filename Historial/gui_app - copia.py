import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget, 
                               QLabel, QPushButton, QMessageBox, QTextEdit, 
                               QFileDialog, QComboBox, QHBoxLayout, QTableWidget, 
                               QTableWidgetItem, QInputDialog, QHeaderView, QDialog)
from PySide6.QtCore import Qt

import db_manager
import excel_processor
import pdf_generator

# =====================================================================
# VENTANAS EMERGENTES (DIALOGS) PARA CONFIGURACIÓN
# =====================================================================

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
            if res == True:
                self.cargar_tabla()
            elif res == "Duplicada":
                QMessageBox.warning(self, "Atención", "Ya existe una sucursal con ese nombre.")

    def toggle_sucursal(self):
        fila = self.tabla.currentRow()
        if fila < 0:
            QMessageBox.warning(self, "Atención", "Selecciona una sucursal de la tabla primero.")
            return
        id_suc = int(self.tabla.item(fila, 0).text())
        estado_actual = 1 if "Activa" in self.tabla.item(fila, 2).text() else 0
        if db_manager.toggle_sucursal(id_suc, estado_actual):
            self.cargar_tabla()

class DialogUbicaciones(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración de Almacén (Arriba/Abajo)")
        self.resize(700, 500)
        layout = QVBoxLayout(self)
        
        # Panel superior de filtros y acciones globales
        panel_top = QHBoxLayout()
        panel_top.addWidget(QLabel("<b>1. Selecciona el Grupo:</b>"))
        self.combo_grupo = QComboBox()
        self.cargar_grupos()
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
        
        # Tabla interactiva
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(3)
        self.tabla.setHorizontalHeaderLabels(["Código", "Producto", "Ubicación en Almacén"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.tabla)
        
        # Cargar productos por primera vez
        self.cargar_tabla_productos()

    def cargar_grupos(self):
        categorias = db_manager.get_categorias()
        self.combo_grupo.addItems(categorias)

    def cargar_tabla_productos(self):
        grupo_actual = self.combo_grupo.currentText()
        if not grupo_actual: return
        
        productos = db_manager.get_productos_por_categoria(grupo_actual)
        self.tabla.setRowCount(0)
        
        for fila, prod in enumerate(productos):
            self.tabla.insertRow(fila)
            
            item_codigo = QTableWidgetItem(prod[0])
            item_codigo.setFlags(item_codigo.flags() & ~Qt.ItemIsEditable) # Solo lectura
            self.tabla.setItem(fila, 0, item_codigo)
            
            item_desc = QTableWidgetItem(prod[1])
            item_desc.setFlags(item_desc.flags() & ~Qt.ItemIsEditable) # Solo lectura
            self.tabla.setItem(fila, 1, item_desc)
            
            # Crear un ComboBox para cada fila para cambiarlo rápido
            combo_ubi = QComboBox()
            combo_ubi.addItems(["ARRIBA", "ABAJO"])
            combo_ubi.setCurrentText(prod[2])
            
            # Conectamos el cambio del combo a la base de datos (usando lambda para pasar el código)
            combo_ubi.currentTextChanged.connect(lambda texto, cod=prod[0]: self.actualizar_producto_individual(cod, texto))
            
            self.tabla.setCellWidget(fila, 2, combo_ubi)

    def actualizar_producto_individual(self, codigo, nueva_ubicacion):
        db_manager.set_ubicacion_producto(codigo, nueva_ubicacion)

    def aplicar_a_todo(self, ubicacion):
        grupo = self.combo_grupo.currentText()
        if not grupo: return
        
        resp = QMessageBox.question(self, "Confirmar", f"¿Mover todo lo de '{grupo}' a {ubicacion}?", QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            db_manager.set_ubicacion_categoria(grupo, ubicacion)
            self.cargar_tabla_productos() # Refresca la tabla para que los combos se actualicen


# =====================================================================
# VENTANA PRINCIPAL DEL SISTEMA
# =====================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gestión de Pedidos Almacén v1.0")
        self.resize(850, 650)
        self.ruta_excel_actual = ""
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout_principal = QVBoxLayout(central_widget)
        
        self.tabs = QTabWidget()
        self.tab_procesar = QWidget()
        self.tab_catalogo = QWidget()
        self.tab_config = QWidget()
        
        self.tabs.addTab(self.tab_procesar, "1. Procesar Pedido")
        self.tabs.addTab(self.tab_catalogo, "2. Actualizar Catálogo")
        self.tabs.addTab(self.tab_config, "3. Panel de Configuración")
        
        layout_principal.addWidget(self.tabs)
        
        self.setup_tab_catalogo()
        self.setup_tab_procesar()
        self.setup_tab_config()
        
        self.tabs.currentChanged.connect(self.al_cambiar_pestana)

    # --- PESTAÑA 1: PROCESAR ---
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

    # --- PESTAÑA 2: CATÁLOGO ---
    def setup_tab_catalogo(self):
        layout = QVBoxLayout(self.tab_catalogo)
        instrucciones = QLabel(
            "<b>INSTRUCCIONES:</b><br>"
            "1. Abre tu archivo 'BASE DE DATOS.xlsx'.<br>"
            "2. Selecciona toda la tabla (incluyendo encabezados).<br>"
            "3. Presiona <b>Ctrl+C</b> para copiar.<br>"
            "4. Presiona el botón verde de abajo."
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

    # --- PESTAÑA 3: CONFIGURACIÓN (REDISEÑADA) ---
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
        btn_sucursales.clicked.connect(self.abrir_dialogo_sucursales)
        layout.addWidget(btn_sucursales)
        
        layout.addSpacing(15)
        
        btn_ubicaciones = QPushButton("📦 Configurar Almacén (Arriba / Abajo)")
        btn_ubicaciones.setStyleSheet("font-size: 16px; padding: 20px; background-color: #EAEDED;")
        btn_ubicaciones.clicked.connect(self.abrir_dialogo_ubicaciones)
        layout.addWidget(btn_ubicaciones)

    # --- ACCIONES DE LA INTERFAZ ---
    def al_cambiar_pestana(self, index):
        if index == 0:
            self.cargar_sucursales_combo()

    def cargar_sucursales_combo(self):
        self.combo_sucursal.clear()
        sucursales = db_manager.get_sucursales(solo_activas=True)
        if not sucursales:
            self.combo_sucursal.addItem("No hay sucursales activas")
        for suc in sucursales:
            self.combo_sucursal.addItem(suc[1], userData=suc[0])

    def abrir_dialogo_sucursales(self):
        dlg = DialogSucursales(self)
        dlg.exec() # Abre la ventana emergente y pausa lo demás
        self.cargar_sucursales_combo() # Actualiza el combo al cerrar

    def abrir_dialogo_ubicaciones(self):
        dlg = DialogUbicaciones(self)
        dlg.exec()

    def procesar_portapapeles(self):
        self.log_catalogo.append("Leyendo portapapeles...")
        exito, resultado = excel_processor.leer_catalogo_portapapeles()
        if not exito:
            QMessageBox.critical(self, "Error de lectura", resultado)
            self.log_catalogo.append(f"❌ Error: {resultado}")
            return
        exito_db = db_manager.upsert_catalogo(resultado)
        if exito_db:
            QMessageBox.information(self, "Éxito", "Catálogo actualizado correctamente.")
            self.log_catalogo.append("✅ ¡Base de datos actualizada con éxito!")
        else:
            QMessageBox.critical(self, "Error de BD", "Hubo un error al guardar.")

    def seleccionar_archivo(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Seleccionar Pedido", "", "Archivos Excel (*.xlsx *.xls)")
        if ruta:
            self.ruta_excel_actual = ruta
            self.lbl_ruta_excel.setText(ruta)
            self.log_procesar.append(f"Archivo seleccionado: {ruta}")

    def ejecutar_procesamiento(self):
        if not self.ruta_excel_actual:
            QMessageBox.warning(self, "Atención", "Por favor selecciona el archivo de pedido primero.")
            return
        if self.combo_sucursal.currentText() == "No hay sucursales activas":
            QMessageBox.warning(self, "Atención", "Ve a la pestaña Configuración y agrega una sucursal primero.")
            return
            
        sucursal = self.combo_sucursal.currentText()
        self.log_procesar.append(f"\n--- Iniciando proceso para {sucursal} ---")
        
        exito, resultado = excel_processor.leer_pedido_excel(self.ruta_excel_actual)
        if not exito:
            QMessageBox.critical(self, "Error", resultado)
            return
            
        exito_bd, encontrados, no_detectados, alertas = db_manager.procesar_pedido_contra_bd(resultado)
        if not exito_bd:
            QMessageBox.critical(self, "Error BD", "Error al consultar la base de datos.")
            return
            
        self.log_procesar.append(f"✅ Encontrados: {len(encontrados)} | ❌ No detectados: {len(no_detectados)} | ⚠️ Alertas: {len(alertas)}")
        
        try:
            ruta_pdf = pdf_generator.generar_pdf_picking(sucursal, encontrados, no_detectados, alertas)
            os.startfile(ruta_pdf)
            QMessageBox.information(self, "Proceso Terminado", "¡PDF generado con éxito!\nSe abrirá automáticamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error PDF", f"Error al crear el PDF: {str(e)}")