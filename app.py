from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from ui.main_window import MainWindow
from ui.styles import get_stylesheet
import os
import sys

def resource_path(relative_path):
    """Obtiene la ruta absoluta al recurso, útil para PyInstaller y ejecución normal."""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def main():
    app = QApplication(sys.argv)
    
    # 1. Aplicar estilos (esto debe ir primero)
    app.setStyle('Fusion')
    app.setStyleSheet(get_stylesheet())
    
    # 2. Cargar icono desde la carpeta resources/ (ahora PNG)
    icon_path = resource_path('resources/lyraoke-icon.png')
    print(f"Intentando cargar icono desde: {icon_path}")
    
    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        app.setWindowIcon(icon)
        print("Icono cargado correctamente")
    else:
        print(f"¡Error! No se encontró el icono en: {icon_path}")
    
    # 3. Crear y mostrar ventana principal
    window = MainWindow()
    
    # En Linux ayuda setear también el icono en la ventana directamente
    if os.path.exists(icon_path):
        window.setWindowIcon(icon)
    
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
