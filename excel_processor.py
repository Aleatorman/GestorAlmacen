import pandas as pd
import logging

def leer_catalogo_portapapeles():
    """
    Lee la información copiada en el portapapeles (Ctrl+C).
    Verifica que tenga las columnas correctas de tu BASE DE DATOS.xlsx
    """
    try:
        # read_clipboard() lee exactamente lo que copiaste
        df = pd.read_clipboard()
        
        # Validamos que vengan tus columnas exactas
        columnas_requeridas = ['Código 1', 'Nombre', 'Grupo', 'Existencia']
        
        # Checamos si falta alguna
        faltantes = [col for col in columnas_requeridas if col not in df.columns]
        if faltantes:
            return False, f"Error: Faltan estas columnas en lo que copiaste: {', '.join(faltantes)}"
        
        # Nos quedamos solo con las columnas que importan
        df = df[columnas_requeridas]
        
        # Limpiamos datos nulos o vacíos en la columna principal
        df = df.dropna(subset=['Código 1'])
        
        return True, df

    except Exception as e:
        logging.error(f"Error leyendo portapapeles: {e}")
        return False, "Error al leer el portapapeles. ¿Estás seguro de que copiaste la tabla del sistema/Excel?"

def leer_pedido_excel(ruta_archivo):
    """
    Lee el archivo de pedido (ej. pedido cantera 15 junio.xlsx).
    """
    try:
        # 1. Leemos el archivo asegurando que Codigo sea texto, pero dejamos Cantidad libre por si hay celdas vacías
        df = pd.read_excel(ruta_archivo, usecols=['Codigo', 'Nombre', 'Cantidad'], dtype={'Codigo': str})
        
        # 2. Eliminamos las filas que vengan en blanco (sin código o sin cantidad)
        df = df.dropna(subset=['Codigo', 'Cantidad'])
        
        # 3. Forzamos a que todo en cantidad sea numérico (si alguien escribió "cinco", lo vuelve nulo)
        df['Cantidad'] = pd.to_numeric(df['Cantidad'], errors='coerce')
        
        # 4. Volvemos a limpiar por si se generaron nulos en el paso anterior y convertimos a entero
        df = df.dropna(subset=['Cantidad'])
        df['Cantidad'] = df['Cantidad'].astype(int)
        
        return True, df
        
    except ValueError as e:
        # Este error ahora solo saltará si DE VERDAD no están las columnas en el Excel
        return False, "Revisa el Excel: Asegúrate de que los encabezados se llamen exactamente 'Codigo', 'Nombre' y 'Cantidad'."
    except Exception as e:
        logging.error(f"Error leyendo Excel pedido: {e}")
        return False, f"Error inesperado al abrir el archivo: {e}"