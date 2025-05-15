from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow
from ui.styles import get_stylesheet
import sys

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(get_stylesheet())  # Aplicar estilos
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()