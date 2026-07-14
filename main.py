import sys
from PySide6.QtWidgets import QApplication
from db_manager import inicializar_bd
from gui_app import MainWindow 

def main():
    # 1. Asegurarnos de que la BD y las tablas existan
    print("Inicializando base de datos...")
    inicializar_bd()
    
    # 2. Iniciar la aplicación de la interfaz gráfica
    app = QApplication(sys.argv)
    
    # 3. Cargar y mostrar la ventana principal
    ventana = MainWindow()
    ventana.show()
    
    print("Sistema listo.")
    
    # 4. Mantener la ventana abierta
    sys.exit(app.exec())

if __name__ == "__main__":
    main()