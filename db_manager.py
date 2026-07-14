import sqlite3
import os
import logging
from datetime import datetime

logging.basicConfig(filename='app_error.log', level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

DB_PATH = 'data/almacen.db'

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def inicializar_bd():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS productos (
                    codigo TEXT PRIMARY KEY, descripcion TEXT NOT NULL,
                    categoria TEXT NOT NULL, existencia INTEGER NOT NULL DEFAULT 0,
                    fecha_actualizacion TEXT NOT NULL)''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ubicaciones (
                    codigo_producto TEXT PRIMARY KEY,
                    ubicacion TEXT NOT NULL CHECK(ubicacion IN ('ARRIBA','ABAJO')) DEFAULT 'ARRIBA')''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sucursales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE NOT NULL,
                    activa INTEGER DEFAULT 1 CHECK(activa IN (0,1)))''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pedidos_historico (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, fecha_proceso TEXT NOT NULL,
                    id_sucursal INTEGER NOT NULL, nombre_archivo_origen TEXT NOT NULL,
                    ruta_pdf_generado TEXT NOT NULL, total_productos_solicitados INTEGER,
                    total_productos_no_detectados INTEGER, total_alertas_resurtido INTEGER,
                    FOREIGN KEY(id_sucursal) REFERENCES sucursales(id))''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria)')
            conn.commit()
    except Exception as e:
        logging.error(f"Error inicializando BD: {e}")
        raise

def upsert_catalogo(df_catalogo):
    fecha_hoy = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for index, row in df_catalogo.iterrows():
                codigo = str(row['Código 1']).strip()
                descripcion = str(row['Nombre']).strip()
                categoria = str(row['Grupo']).strip()
                try: existencia = int(float(row['Existencia']))
                except (ValueError, TypeError): existencia = 0

                cursor.execute('''
                    INSERT INTO productos (codigo, descripcion, categoria, existencia, fecha_actualizacion)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(codigo) DO UPDATE SET
                        descripcion=excluded.descripcion, categoria=excluded.categoria,
                        existencia=excluded.existencia, fecha_actualizacion=excluded.fecha_actualizacion
                ''', (codigo, descripcion, categoria, existencia, fecha_hoy))
            conn.commit()
            return True
    except Exception as e:
        logging.error(f"Error en upsert_catalogo: {e}")
        return False

def procesar_pedido_contra_bd(df_pedido):
    encontrados = []
    no_detectados = []
    alertas = []
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            for index, row in df_pedido.iterrows():
                codigo = str(row['Codigo']).strip()
                desc_excel = str(row['Nombre']).strip()
                cantidad = int(row['Cantidad'])
                
                cursor.execute('''
                    SELECT p.descripcion, p.categoria, p.existencia, COALESCE(u.ubicacion, 'ARRIBA') as ubicacion 
                    FROM productos p 
                    LEFT JOIN ubicaciones u ON p.codigo = u.codigo_producto 
                    WHERE p.codigo = ?
                ''', (codigo,))
                res = cursor.fetchone()
                
                if res is None:
                    no_detectados.append({'codigo': codigo, 'descripcion': desc_excel, 'cantidad': cantidad})
                else:
                    desc_db, categoria, existencia, ubicacion = res
                    prod_data = {'codigo': codigo, 'descripcion': desc_db, 'categoria': categoria,
                                 'existencia': existencia, 'ubicacion': ubicacion, 'cantidad': cantidad}
                    encontrados.append(prod_data)
                    if cantidad > existencia: alertas.append(prod_data)
        return True, encontrados, no_detectados, alertas
    except Exception as e:
        logging.error(f"Error procesando pedido: {e}")
        return False, [], [], []

def get_categorias():
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT categoria FROM productos ORDER BY categoria')
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        return []

def get_productos_por_categoria(categoria):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.codigo, p.descripcion, COALESCE(u.ubicacion, 'ARRIBA')
                FROM productos p
                LEFT JOIN ubicaciones u ON p.codigo = u.codigo_producto
                WHERE p.categoria = ?
                ORDER BY p.descripcion
            ''', (categoria,))
            return cursor.fetchall()
    except Exception as e:
        return []

def set_ubicacion_categoria(categoria, ubicacion):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT codigo FROM productos WHERE categoria = ?', (categoria,))
            codigos = cursor.fetchall()
            for (codigo,) in codigos:
                cursor.execute('''
                    INSERT INTO ubicaciones (codigo_producto, ubicacion) VALUES (?, ?)
                    ON CONFLICT(codigo_producto) DO UPDATE SET ubicacion=excluded.ubicacion
                ''', (codigo, ubicacion))
            conn.commit()
            return True
    except Exception as e:
        return False

def set_ubicacion_producto(codigo, ubicacion):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO ubicaciones (codigo_producto, ubicacion) VALUES (?, ?)
                ON CONFLICT(codigo_producto) DO UPDATE SET ubicacion=excluded.ubicacion
            ''', (codigo, ubicacion))
            conn.commit()
            return True
    except Exception as e:
        return False

def get_sucursales(solo_activas=False):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            if solo_activas:
                cursor.execute('SELECT id, nombre, activa FROM sucursales WHERE activa = 1')
            else:
                cursor.execute('SELECT id, nombre, activa FROM sucursales')
            return cursor.fetchall()
    except Exception as e:
        return []

def agregar_sucursal(nombre):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO sucursales (nombre, activa) VALUES (?, 1)', (nombre,))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return "Duplicada"
    except Exception as e:
        return False

def toggle_sucursal(id_sucursal, estado_actual):
    nuevo_estado = 0 if estado_actual == 1 else 1
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE sucursales SET activa = ? WHERE id = ?', (nuevo_estado, id_sucursal))
            conn.commit()
            return True
    except Exception as e:
        return False

# --- NUEVAS FUNCIONES PARA HISTÓRICO ---

def guardar_historial_pedido(id_sucursal, nombre_archivo, ruta_pdf, tot_solicitados, tot_no_detectados, tot_alertas):
    fecha_hoy = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO pedidos_historico 
                (fecha_proceso, id_sucursal, nombre_archivo_origen, ruta_pdf_generado, 
                 total_productos_solicitados, total_productos_no_detectados, total_alertas_resurtido)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (fecha_hoy, id_sucursal, nombre_archivo, ruta_pdf, tot_solicitados, tot_no_detectados, tot_alertas))
            conn.commit()
            return True
    except Exception as e:
        logging.error(f"Error guardando historial: {e}")
        return False

def obtener_historial_pedidos(fecha_inicio, fecha_fin, id_sucursal=None):
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT h.id, h.fecha_proceso, s.nombre, h.nombre_archivo_origen, 
                       h.total_productos_solicitados, h.total_productos_no_detectados, 
                       h.total_alertas_resurtido, h.ruta_pdf_generado
                FROM pedidos_historico h
                JOIN sucursales s ON h.id_sucursal = s.id
                WHERE date(h.fecha_proceso) BETWEEN ? AND ?
            '''
            params = [fecha_inicio, fecha_fin]
            
            if id_sucursal:
                query += ' AND h.id_sucursal = ?'
                params.append(id_sucursal)
                
            query += ' ORDER BY h.fecha_proceso DESC'
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"Error obteniendo historial: {e}")
        return []