import pandas as pd
import logging

def leer_catalogo_portapapeles():
    """
    Lee la información copiada en el portapapeles (Ctrl+C).
    Verifica que tenga las columnas correctas de tu BASE DE DATOS.xlsx
    """
    try:
        df = pd.read_clipboard()
        columnas_requeridas = ['Código 1', 'Nombre', 'Grupo', 'Existencia']
        
        faltantes = [col for col in columnas_requeridas if col not in df.columns]
        if faltantes:
            return False, f"Error: Faltan estas columnas en lo que copiaste: {', '.join(faltantes)}"
        
        df = df[columnas_requeridas]
        df = df.dropna(subset=['Código 1'])
        return True, df

    except Exception as e:
        logging.error(f"Error leyendo portapapeles: {e}")
        return False, "Error al leer el portapapeles. ¿Estás seguro de que copiaste la tabla del sistema/Excel?"

def leer_pedido_excel(ruta_archivo):
    """
    Lee el archivo de pedido buscando dinámicamente en qué fila están los encabezados.
    ¡Adiós al problema de las filas en blanco al inicio!
    """
    try:
        # 1. Leemos las primeras 20 filas sin formato para localizar dónde están los encabezados
        df_temp = pd.read_excel(ruta_archivo, header=None, nrows=20)
        fila_encabezado = None
        
        for idx, row in df_temp.iterrows():
            # Convertimos la fila a texto en minúsculas para buscar palabras clave
            fila_str = [str(val).strip().lower() for val in row.values]
            if any('codigo' in val or 'código' in val for val in fila_str) and any('cantidad' in val for val in fila_str):
                fila_encabezado = idx
                break
        
        if fila_encabezado is None:
            # Si no se detecta en las primeras 20 filas, intentamos con la fila 0 por defecto
            fila_encabezado = 0
            
        # 2. Leemos el Excel usando exactamente la fila donde encontramos los encabezados
        df = pd.read_excel(ruta_archivo, header=fila_encabezado, dtype=str)
        
        # Limpiamos espacios en blanco en los nombres de las columnas
        df.columns = [str(col).strip() for col in df.columns]
        
        # 3. Identificamos las columnas de forma flexible por si cambian acentos o mayúsculas
        col_codigo = next((c for c in df.columns if 'cod' in c.lower() or 'cód' in c.lower()), None)
        col_nombre = next((c for c in df.columns if 'nom' in c.lower() or 'desc' in c.lower() or 'art' in c.lower()), None)
        col_cant = next((c for c in df.columns if 'cant' in c.lower()), None)
        
        if not col_codigo or not col_nombre or not col_cant:
            return False, f"Revisa el Excel: No se encontraron las columnas 'Codigo', 'Nombre' y 'Cantidad' (se buscó desde la fila {fila_encabezado + 1})."
        
        # Estandarizamos a los nombres internos del programa
        df = df[[col_codigo, col_nombre, col_cant]].rename(columns={
            col_codigo: 'Codigo', col_nombre: 'Nombre', col_cant: 'Cantidad'
        })
        
        # 4. Limpieza general de filas vacías y conversión numérica
        df = df.dropna(subset=['Codigo', 'Cantidad'])
        df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce')
        df = df.dropna(subset=['Cantidad'])
        df['Cantidad'] = df['Cantidad'].astype(int)
        
        return True, df
        
    except Exception as e:
        logging.error(f"Error leyendo Excel pedido: {e}")
        return False, f"Error inesperado al abrir el archivo: {e}"