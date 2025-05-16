import os
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QLabel, 
                           QPushButton, QProgressBar, QHBoxLayout, QFileDialog,
                           QScrollArea, QMessageBox, QButtonGroup)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QTimer
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtMultimedia import QMediaPlayer
from pathlib import Path
from core.audio_processor import AudioProcessor
from core.player import KaraokePlayer
import threading
import json
import time

class MainWindow(QMainWindow):
    processing_finished = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lyraoke-IA - Karaoke con IA")
        self.setAcceptDrops(True)
        self.setMinimumSize(800, 600)
        
        self.audio_processor = AudioProcessor()
        self.player = KaraokePlayer()
        self.current_file = None
        self.current_audio_path = None
        self.original_path = None
        self.vocals_path = None
        self.instrumental_path = None
        
        self.init_ui()
        self.init_connections()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        
        # Área de drag & drop
        self.drop_area = QLabel("Arrastra tu canción aquí (MP3, WAV, etc.)")
        self.drop_area.setAlignment(Qt.AlignCenter)
        self.drop_area.setFixedHeight(150)
        self.drop_area.setObjectName("drop_area")
        layout.addWidget(self.drop_area)
        
        # Botón de selección
        self.select_btn = QPushButton("Seleccionar Archivo")
        layout.addWidget(self.select_btn)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Controles de reproducción
        controls_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.pause_btn = QPushButton("⏸ Pause")
        self.stop_btn = QPushButton("⏹ Stop")
        
        # Botones de modo (MANTENIENDO TUS BOTONES ORIGINALES)
        self.original_btn = QPushButton("🎤 Original")
        self.acapella_btn = QPushButton("🎤 Acapella")
        self.karaoke_btn = QPushButton("🎤 Karaoke")
        
        # Configurar botones (inicialmente deshabilitados)
        for btn in [self.play_btn, self.pause_btn, self.stop_btn, 
                   self.original_btn, self.acapella_btn, self.karaoke_btn]:
            btn.setEnabled(False)
        
        # Agrupar botones de modo
        self.mode_group = QButtonGroup(self)
        for btn in [self.original_btn, self.acapella_btn, self.karaoke_btn]:
            self.mode_group.addButton(btn)
            btn.setCheckable(True)
        self.karaoke_btn.setChecked(True)  # Modo karaoke por defecto
        
        # Añadir a layout
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.original_btn)
        controls_layout.addWidget(self.acapella_btn)
        controls_layout.addWidget(self.karaoke_btn)
        layout.addLayout(controls_layout)
        
        # Barra de progreso de la canción
        self.song_progress = QProgressBar()
        self.song_progress.setTextVisible(False)
        layout.addWidget(self.song_progress)
        
        # Área de letras con scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(200)
        self.lyrics_display = QLabel()
        self.lyrics_display.setAlignment(Qt.AlignCenter)
        self.lyrics_display.setWordWrap(True)
        self.lyrics_display.setObjectName("lyricsDisplay")
        scroll.setWidget(self.lyrics_display)
        layout.addWidget(scroll)

    def init_connections(self):
        # Conectar botones de control
        self.play_btn.clicked.connect(self.play_audio)
        self.pause_btn.clicked.connect(self.player.pause)
        self.stop_btn.clicked.connect(self.player.stop)
        
        # Conectar botones de modo
        self.original_btn.toggled.connect(self.toggle_playback_mode)
        self.acapella_btn.toggled.connect(self.toggle_playback_mode)
        self.karaoke_btn.toggled.connect(self.toggle_playback_mode)
        
        # Otras conexiones
        self.select_btn.clicked.connect(self.select_file)
        self.processing_finished.connect(self.on_processing_finished)
        
        # Conexiones del reproductor
        self.player.positionChanged.connect(self.update_song_progress)
        self.player.lyrics_updated.connect(self.update_lyrics_display)
        self.player.stateChanged.connect(self.update_buttons_state)

    def toggle_playback_mode(self, checked):
        """Manejar cambio entre modos de reproducción (ORIGINAL, ACAPELLA, KARAOKE)"""
        if not checked or not hasattr(self, 'current_audio_path'):
            return
            
        sender = self.sender()
        
        # Determinar qué archivo cargar según el modo seleccionado
        if sender == self.original_btn and hasattr(self, 'original_path'):
            self.current_audio_path = self.original_path
        elif sender == self.acapella_btn and hasattr(self, 'vocals_path'):
            self.current_audio_path = self.vocals_path
        elif hasattr(self, 'instrumental_path'):  # Karaoke por defecto
            self.current_audio_path = self.instrumental_path
        
        # Si está reproduciendo, cambiar el audio inmediatamente
        if self.player.state() == QMediaPlayer.PlayingState:
            self._play_with_retry()

    def _play_with_retry(self, attempt=0):
        """Intentar reproducir con reintentos"""
        if attempt >= 3:
            QMessageBox.warning(self, "Error", "No se pudo cargar el archivo de audio")
            return
            
        if self.player.load_audio(self.current_audio_path):
            self.player.play()
        else:
            QTimer.singleShot(300, lambda: self._play_with_retry(attempt + 1))

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar canción", "", "Audio Files (*.mp3 *.wav *.ogg *.flac)"
        )
        if file_path:
            self.handle_new_file(file_path)

    def handle_new_file(self, file_path):
        self.current_file = file_path
        self.drop_area.setText(f"Procesando:\n{os.path.basename(file_path)}")
        self.start_processing()

    def start_processing(self):
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        self.setEnabled(False)
        
        # Deshabilitar todos los botones de control
        for btn in [self.play_btn, self.pause_btn, self.stop_btn, 
                   self.original_btn, self.acapella_btn, self.karaoke_btn]:
            btn.setEnabled(False)
        
        self.lyrics_display.setText("")
        
        threading.Thread(target=self.process_audio_background, daemon=True).start()

    def process_audio_background(self):
        try:
            result = self.audio_processor.process_audio(self.current_file)
            self.processing_finished.emit(result)
        except Exception as e:
            print(f"Error processing audio: {e}")

    def on_processing_finished(self, result):
        self.progress_bar.hide()
        self.setEnabled(True)
        
        if not result.get('stems'):
            QMessageBox.warning(self, "Error", "No se generaron las pistas de audio correctamente")
            return
        
        try:
            # Asegurar que las rutas son strings válidas
            self.original_path = str(self._validate_audio_path(result['original']))
            self.vocals_path = str(self._validate_audio_path(result['stems']['vocals']))
            self.instrumental_path = str(self._validate_audio_path(result['stems']['instrumental']))
            self.current_audio_path = str(self.instrumental_path)  # Modo karaoke por defecto
            
            # Cargar letras temporizadas
            lyrics_dir = os.path.join('output', 'lyrics')
            timed_path = os.path.join(lyrics_dir, 'song_timed.json')
            text_path = os.path.join(lyrics_dir, 'song_lyrics.txt')
            
            if os.path.exists(timed_path):
                if not self.player.load_timed_lyrics_from_json(timed_path):
                    QMessageBox.warning(self, "Error", "Error al cargar letras temporizadas")
            
            if os.path.exists(text_path):
                try:
                    with open(text_path, 'r', encoding='utf-8') as f:
                        self.lyrics_display.setText(f.read())
                except Exception as e:
                    print(f"Info: No se pudo cargar el texto de letras: {str(e)}")
            
            # Habilitar controles SOLO cuando el procesamiento termine
            self.update_buttons_state(self.player.state())
            self.drop_area.setText(f"Listo:\n{os.path.basename(self.current_file)}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al finalizar el procesamiento: {str(e)}")

    def play_audio(self):
        """Reproducir audio con manejo de errores"""
        if not hasattr(self, 'current_audio_path'):
            QMessageBox.warning(self, "Error", "No hay archivo de audio cargado")
            return
        
        if not os.path.exists(self.current_audio_path):
            QMessageBox.warning(self, "Error", f"Archivo no existe: {self.current_audio_path}")
            return
            
        if os.path.getsize(self.current_audio_path) == 0:
            QMessageBox.warning(self, "Error", "El archivo está vacío")
            return

        # Intentar carga con reintentos
        for attempt in range(3):
            if self.player.load_audio(self.current_audio_path):
                self.player.play()
                return
            time.sleep(0.5)
        
        QMessageBox.warning(self, "Error", "No se pudo cargar el archivo después de 3 intentos")

    def update_buttons_state(self, state=None):
        """Actualizar estado de los botones según el estado del reproductor"""
        if state is None:
            state = self.player.state()
        
        # Verificar si tenemos audio cargado
        has_audio = bool(getattr(self, 'current_audio_path', None))

        
        # Actualizar estado de los botones
        self.play_btn.setEnabled(has_audio and state != QMediaPlayer.PlayingState)
        self.pause_btn.setEnabled(has_audio and state == QMediaPlayer.PlayingState)
        self.stop_btn.setEnabled(has_audio and state != QMediaPlayer.StoppedState)
        
        # Botones de modo solo si hay audio
        for btn in [self.original_btn, self.acapella_btn, self.karaoke_btn]:
            btn.setEnabled(has_audio)

    def _validate_audio_path(self, relative_path):
        """Validar y convertir ruta de audio"""
        path = Path(relative_path).absolute()
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo: {path}")
        return path

    def update_song_progress(self, position):
        if self.player.duration() > 0:
            self.song_progress.setValue(int((position / self.player.duration()) * 100))

    def update_lyrics_display(self, current_word, current_time, context_lines):
        if not context_lines:
            return
            
        html_content = "<div style='text-align: center; font-family: Arial;'>"
        
        for line in context_lines:
            if current_word.lower() in line.lower():  # Línea actual
                highlighted = line.replace(
                    current_word, 
                    f"<span style='color: #4CAF50; font-weight: bold; font-size: 24px;'>{current_word}</span>"
                )
                html_content += f"<div style='margin: 10px 0; font-size: 22px;'>{highlighted}</div>"
            else:  # Líneas de contexto
                html_content += f"<div style='margin: 5px 0; font-size: 20px; opacity: 0.8;'>{line}</div>"
        
        self.lyrics_display.setText(html_content + "</div>")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if urls := event.mimeData().urls():
            if urls[0].isLocalFile():
                self.handle_new_file(urls[0].toLocalFile())

    def closeEvent(self, event):
        self.player.stop()
        event.accept()