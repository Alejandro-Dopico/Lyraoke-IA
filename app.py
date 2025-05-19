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
    
    # Aplicar estilo y stylesheet
    app.setStyle('Fusion')
    app.setStyleSheet(get_stylesheet())
    
    # Icono
    if sys.platform.startswith("win"):
        icon_filename = "resources/lyraoke-icon.ico"  # Usar .ico en Windows
    else:
        icon_filename = "resources/lyraoke-icon.png"  # Usar .png en otros sistemas

    icon_path = resource_path(icon_filename)
    print(f"Intentando cargar icono desde: {icon_path}")

    if os.path.exists(icon_path):
        icon = QIcon(icon_path)
        app.setWindowIcon(icon)
    else:
        print(f"¡Error! No se encontró el icono en: {icon_path}")
    
    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
