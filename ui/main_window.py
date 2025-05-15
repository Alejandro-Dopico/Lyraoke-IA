import os
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QLabel, 
                           QPushButton, QProgressBar, QHBoxLayout, QFileDialog,
                           QScrollArea, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
from PyQt5.QtMultimedia import QMediaPlayer
from pathlib import Path
from core.audio_processor import AudioProcessor
from core.player import KaraokePlayer
import threading
import json

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
        self.current_instrumental = None
        self.current_vocals = None
        
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
        self.vocals_toggle = QPushButton("🎤 Voces: OFF")
        
        for btn in [self.play_btn, self.pause_btn, self.stop_btn, self.vocals_toggle]:
            btn.setEnabled(False)
            controls_layout.addWidget(btn)
        
        self.vocals_toggle.setCheckable(True)
        layout.addLayout(controls_layout)
        
        # Barra de progreso de la canción
        self.song_progress = QProgressBar()
        self.song_progress.setTextVisible(False)
        layout.addWidget(self.song_progress)
        
        # Área de letras con scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.lyrics_display = QLabel()
        self.lyrics_display.setAlignment(Qt.AlignCenter)
        self.lyrics_display.setWordWrap(True)
        self.lyrics_display.setObjectName("lyricsDisplay")
        scroll.setWidget(self.lyrics_display)
        layout.addWidget(scroll, stretch=1)

    def init_connections(self):
        """Conectar todas las señales correctamente"""
        # Conectar botones
        self.play_btn.clicked.connect(self.play_audio)
        self.pause_btn.clicked.connect(lambda: self.player.pause())
        self.stop_btn.clicked.connect(lambda: self.player.stop())
        
        # Otras conexiones
        self.select_btn.clicked.connect(self.select_file)
        self.vocals_toggle.toggled.connect(self.toggle_vocals)
        self.processing_finished.connect(self.on_processing_finished)
        
        # Conectar señales del reproductor
        self.player.positionChanged.connect(self.update_song_progress)
        self.player.lyrics_updated.connect(self.update_lyrics_display)
        self.player.stateChanged.connect(self.update_buttons_state)

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
        
        for btn in [self.play_btn, self.pause_btn, self.stop_btn, self.vocals_toggle]:
            btn.setEnabled(False)
        
        self.vocals_toggle.setChecked(False)
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
            stems = result['stems']
            self.current_instrumental = self._validate_audio_path(stems.get('instrumental'))
            self.current_vocals = self._validate_audio_path(stems.get('vocals'))
            self.original_song = str(Path(self.current_file).absolute())
            
            lyrics_info = result.get('lyrics', {})
            if lyrics_info.get('timed_path'):
                if not self.player.load_timed_lyrics_from_json(self._validate_lyrics_path(lyrics_info['timed_path'])):
                    QMessageBox.warning(self, "Error", "Error al cargar letras temporizadas")
            
            if lyrics_info.get('text_path'):
                try:
                    with open(self._validate_lyrics_path(lyrics_info['text_path']), 'r', encoding='utf-8') as f:
                        self.lyrics_display.setText(f.read())
                except Exception as e:
                    print(f"Info: No se pudo cargar el texto de letras: {str(e)}")
            
            for btn in [self.play_btn, self.pause_btn, self.stop_btn, self.vocals_toggle]:
                btn.setEnabled(True)
            
            self.drop_area.setText(f"Listo:\n{os.path.basename(self.current_file)}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al finalizar el procesamiento: {str(e)}")

    def _validate_audio_path(self, relative_path):
        path = Path(relative_path).absolute()
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de audio: {path}")
        return str(path)
    
    def _validate_lyrics_path(self, relative_path):
        if not relative_path:
            return None
        path = Path(relative_path).absolute()
        return str(path) if path.exists() else None
    
    def update_buttons_state(self, state):
        """Actualizar estado de los botones según el estado del reproductor"""
        self.play_btn.setEnabled(state != QMediaPlayer.PlayingState)
        self.pause_btn.setEnabled(state == QMediaPlayer.PlayingState)
        self.stop_btn.setEnabled(state != QMediaPlayer.StoppedState)
        
    def play_audio(self):
        """Reproducir audio con manejo de errores"""
        if not self.current_instrumental or not Path(self.current_instrumental).exists():
            QMessageBox.warning(self, "Error", "No hay archivo de audio cargado")
            return
        
        audio_path = self.current_vocals if self.vocals_toggle.isChecked() else self.current_instrumental
        
        if not self.player.load_audio(audio_path):
            QMessageBox.warning(self, "Error", "No se pudo cargar el archivo de audio")
            return
        
        self.player.play()

    def stop_audio(self):
        self.player.stop()
        self.song_progress.setValue(0)

    def toggle_vocals(self, checked):
        self.vocals_toggle.setText("🎤 Original" if checked else "🎤 Karaoke")
        audio_path = self.original_song if checked else self.current_instrumental
        if self.player.state() == QMediaPlayer.PlayingState and not self.player.load_audio(audio_path):
            QMessageBox.warning(self, "Error", "No se pudo cargar el audio")

    def update_song_progress(self, position):
        if self.player.duration() > 0:
            self.song_progress.setValue(int((position / self.player.duration()) * 100))

    def update_lyrics_display(self, current_word, current_time, context_lines):
        """Muestra la letra en formato karaoke"""
        if not context_lines:
            return
        
        html_content = "<div style='text-align: center; font-family: Arial;'>"
        
        for i, line in enumerate(context_lines):
            if current_word.lower() in line.lower():  # Línea actual
                # Resaltar palabra actual
                highlighted = line.replace(
                    current_word, 
                    f"<span style='color: #4CAF50; font-size: 24px; font-weight: bold;'>{current_word}</span>"
                )
                html_content += f"<div style='margin: 10px 0; font-size: 22px;'>{highlighted}</div>"
            else:  # Líneas de contexto
                opacity = "0.7" if i < 1 else "1.0"  # La línea anterior más tenue
                html_content += f"<div style='margin: 5px 0; font-size: 18px; opacity: {opacity};'>{line}</div>"
        
        html_content += "</div>"
        self.lyrics_display.setText(html_content)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if urls := event.mimeData().urls():
            if urls[0].isLocalFile():
                self.handle_new_file(urls[0].toLocalFile())