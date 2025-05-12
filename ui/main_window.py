import os
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QLabel, 
                           QPushButton, QProgressBar, QHBoxLayout, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from core.audio_processor import AudioProcessor
from core.player import KaraokePlayer
from core.file_manager import FileManager
from ui.styles import get_stylesheet
import threading

class MainWindow(QMainWindow):
    processing_finished = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lyraoke-IA - Karaoke con IA")
        self.setAcceptDrops(True)
        self.setMinimumSize(800, 600)
        
        # Inicializar componentes
        self.audio_processor = AudioProcessor()
        self.player = KaraokePlayer()
        self.current_file = None
        
        # Configurar UI
        self.init_ui()
        self.init_connections()
        self.apply_styles()
    
    def init_ui(self):
        # Widget principal
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Layout principal
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # Área de drag & drop
        self.drop_area = QLabel("Arrastra tu canción aquí (MP3, WAV, etc.)")
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setFixedHeight(150)
        layout.addWidget(self.drop_area)
        
        # Botón de selección manual
        self.select_btn = QPushButton("Seleccionar Archivo")
        layout.addWidget(self.select_btn)
        
        # Barra de progreso de procesamiento
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Controles de reproducción
        controls_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setEnabled(False)
        
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        layout.addLayout(controls_layout)
        
        # Barra de progreso de la canción
        self.song_progress = QProgressBar()
        self.song_progress.setTextVisible(False)
        layout.addWidget(self.song_progress)
        
        # Visualización de letras
        self.lyrics_display = QLabel()
        self.lyrics_display.setAlignment(Qt.AlignCenter)
        self.lyrics_display.setWordWrap(True)
        layout.addWidget(self.lyrics_display, stretch=1)
    
    def init_connections(self):
        # Señales y slots
        self.select_btn.clicked.connect(self.select_file)
        self.play_btn.clicked.connect(self.player.play)
        self.pause_btn.clicked.connect(self.player.pause)
        self.stop_btn.clicked.connect(self.player.stop)
        self.processing_finished.connect(self.on_processing_finished)
        self.player.positionChanged.connect(self.update_song_progress)
        self.player.lyrics_updated.connect(self.update_lyrics_display)
    
    def apply_styles(self):
        self.setStyleSheet(get_stylesheet())
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.handle_new_file(urls[0].toLocalFile())
    
    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar canción",
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.flac)"
        )
        
        if file_path:
            self.handle_new_file(file_path)
    
    def handle_new_file(self, file_path):
        # Guardar archivo en la carpeta songs y limpiar previos
        self.current_file = FileManager.save_uploaded_file(file_path)
        self.drop_area.setText(f"Canción cargada:\n{os.path.basename(self.current_file)}")
        
        # Iniciar procesamiento
        self.start_processing()
    
    def start_processing(self):
        # Mostrar progreso
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)  # Modo indeterminado
        
        # Deshabilitar controles durante el procesamiento
        self.select_btn.setEnabled(False)
        self.drop_area.setEnabled(False)
        
        # Procesar en un hilo separado
        processing_thread = threading.Thread(
            target=self.process_audio,
            daemon=True
        )
        processing_thread.start()
    
    def process_audio(self):
        try:
            result = self.audio_processor.process_audio(self.current_file)
            self.processing_finished.emit(result)
        except Exception as e:
            print(f"Error processing audio: {e}")
            self.progress_bar.hide()
    
    def on_processing_finished(self, result):
        # Ocultar barra de progreso
        self.progress_bar.hide()
        
        # Habilitar controles
        self.select_btn.setEnabled(True)
        self.drop_area.setEnabled(True)
        
        # Configurar reproductor
        self.player.load_audio(result['stems']['vocals'])
        self.player.set_timed_lyrics(result['lyrics']['timed_segments'])
        
        # Habilitar controles de reproducción
        self.play_btn.setEnabled(True)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        # Mostrar letras completas inicialmente
        self.lyrics_display.setText(result['lyrics']['text'])
    
    def update_song_progress(self, position):
        duration = self.player.duration()
        if duration > 0:
            progress = int((position / duration) * 100)
            self.song_progress.setValue(progress)
    
    def update_lyrics_display(self, current_word, current_time):
        # Implementar lógica de resaltado de palabras
        self.lyrics_display.setText(f"Palabra actual: {current_word}")