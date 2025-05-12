import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    # Configurar aplicación
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Mejor aspecto en todos los sistemas
    
    # Crear y mostrar ventana principal
    window = MainWindow()
    window.show()
    
    # Ejecutar aplicación
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()