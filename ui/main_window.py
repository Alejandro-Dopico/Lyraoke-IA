import os
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QLabel, 
                           QPushButton, QProgressBar, QHBoxLayout, QFileDialog,
                           QScrollArea, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QTimer
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from pathlib import Path
from core.audio_processor import AudioProcessor
import threading
import time
import json
import tempfile
from pydub import AudioSegment

class KaraokePlayer(QMediaPlayer):
    lyrics_updated = pyqtSignal(str, float, list)  # palabra_actual, tiempo_actual, contexto
    position_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._timed_lyrics = []
        self._current_segment_index = 0
        self._lyrics_update_timer = QTimer(self)
        self._lyrics_update_timer.setInterval(100)  # 100ms
        self._lyrics_update_timer.timeout.connect(self._update_lyrics_display)
        self._temp_files = []
        
        self.positionChanged.connect(self._handle_position_changed)
        self.stateChanged.connect(self._handle_state_change)
    
    def _handle_position_changed(self, position):
        """Manejador para positionChanged"""
        self.position_changed.emit(position)
    
    def _handle_state_change(self, state):
        """Manejador para stateChanged"""
        if state == QMediaPlayer.StoppedState:
            self._lyrics_update_timer.stop()
            self._current_segment_index = 0
            self.lyrics_updated.emit("", 0.0, [])
    
    def load_audio(self, audio_path: str):
        """Carga y convierte el audio a formato compatible"""
        try:
            path = Path(audio_path)
            
            if not path.exists():
                QMessageBox.warning(None, "Error", f"Archivo no encontrado: {audio_path}")
                return False
            
            if not os.access(audio_path, os.R_OK):
                QMessageBox.warning(None, "Error", "No hay permisos para leer el archivo")
                return False
            
            if path.suffix.lower() != '.wav':
                temp_wav = Path(tempfile.mktemp(suffix='.wav'))
                try:
                    AudioSegment.from_file(path).export(temp_wav, format="wav")
                    self._temp_files.append(temp_wav)
                    audio_path = str(temp_wav)
                except Exception as e:
                    QMessageBox.warning(None, "Error", f"No se pudo convertir el audio: {str(e)}")
                    return False
            
            time.sleep(0.5)  # Esperar para asegurar disponibilidad
            
            content = QMediaContent(QUrl.fromLocalFile(audio_path))
            self.setMedia(content)
            
            if self.mediaStatus() == QMediaPlayer.InvalidMedia:
                QMessageBox.warning(None, "Error", "Formato de audio no soportado")
                return False
                
            return True
        except Exception as e:
            QMessageBox.warning(None, "Error", f"Error al cargar audio: {str(e)}")
            return False

    def load_timed_lyrics_from_json(self, json_path: str) -> bool:
        """Carga letras temporizadas desde archivo JSON"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                if not isinstance(data, dict) or 'segments' not in data:
                    raise ValueError("Formato de letras inválido")
                
                self._timed_lyrics = []
                for segment in data['segments']:
                    if 'words' in segment:
                        for word in segment['words']:
                            word['segment_text'] = segment['text']
                            self._timed_lyrics.append(word)
                
                self._current_segment_index = 0
                return True
                
        except Exception as e:
            QMessageBox.warning(None, "Error", f"No se pudieron cargar las letras: {str(e)}")
            return False

    def play(self):
        """Inicia reproducción con sincronización de letras"""
        super().play()
        if self._timed_lyrics:
            self._lyrics_update_timer.start()

    def stop(self):
        """Detiene la reproducción y reinicia posición"""
        super().stop()
        self.setPosition(0)
        self._lyrics_update_timer.stop()
        self._current_segment_index = 0
        self.lyrics_updated.emit("", 0.0, [])

    def _update_lyrics_display(self):
        """Actualiza la visualización de letras según el tiempo actual"""
        if not self._timed_lyrics or self.state() != QMediaPlayer.PlayingState:
            return
        
        current_time = self.position() / 1000  # Convertir a segundos
        
        # Encontrar segmento actual
        current_segment = None
        for i, word in enumerate(self._timed_lyrics):
            if word['start'] <= current_time <= word.get('end', word['start'] + 1):
                current_segment = word
                self._current_segment_index = i
                break
        
        if current_segment:
            # Obtener contexto (3 líneas)
            context_lines = []
            start_idx = max(0, self._current_segment_index - 1)
            end_idx = min(len(self._timed_lyrics), self._current_segment_index + 2)
            
            for i in range(start_idx, end_idx):
                text = self._timed_lyrics[i].get('segment_text', '')
                if text not in context_lines:
                    context_lines.append(text)
            
            self.lyrics_updated.emit(
                current_segment.get('word', ''),
                current_time,
                context_lines
            )

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
        self.current_instrumental = None
        self.current_vocals = None
        
        # Configurar UI
        self.init_ui()
        self.init_connections()
        self.apply_styles()
    
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
        self.play_btn.setEnabled(False)
        
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        
        self.vocals_toggle = QPushButton("🎤 Voces: OFF")
        self.vocals_toggle.setEnabled(False)
        self.vocals_toggle.setCheckable(True)
        
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.vocals_toggle)
        layout.addLayout(controls_layout)
        
        # Barra de progreso de la canción
        self.song_progress = QProgressBar()
        self.song_progress.setTextVisible(False)
        layout.addWidget(self.song_progress)
        
        # Área de letras con scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        
        self.lyrics_display = QLabel()
        self.lyrics_display.setAlignment(Qt.AlignCenter)
        self.lyrics_display.setWordWrap(True)
        self.lyrics_display.setObjectName("lyricsDisplay")
        
        scroll.setWidget(self.lyrics_display)
        layout.addWidget(scroll, stretch=1)
    
    def init_connections(self):
        self.select_btn.clicked.connect(self.select_file)
        self.play_btn.clicked.connect(self.play_audio)
        self.pause_btn.clicked.connect(self.player.pause)
        self.stop_btn.clicked.connect(self.stop_audio)
        self.vocals_toggle.toggled.connect(self.toggle_vocals)
        self.processing_finished.connect(self.on_processing_finished)
        self.player.positionChanged.connect(self.update_song_progress)
        self.player.lyrics_updated.connect(self.update_lyrics_display)
    
    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QLabel#drop_area {
                background-color: #3d3d3d;
                border: 2px dashed #5a5a5a;
                border-radius: 10px;
                color: #aaaaaa;
                font-size: 18px;
                padding: 20px;
            }
            QLabel#lyricsDisplay {
                font-size: 20px;
                color: white;
                padding: 15px;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
            QPushButton:disabled {
                background-color: #3a3a3a;
                color: #7a7a7a;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                height: 8px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
            QScrollArea {
                border: none;
                background: rgba(0, 0, 0, 0.3);
            }
        """)
    
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
        self.current_file = file_path
        self.drop_area.setText(f"Procesando:\n{os.path.basename(file_path)}")
        self.start_processing()
    
    def start_processing(self):
        self.progress_bar.show()
        self.progress_bar.setRange(0, 0)
        self.setEnabled(False)
        
        # Resetear controles
        self.play_btn.setEnabled(False)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.vocals_toggle.setEnabled(False)
        self.vocals_toggle.setChecked(False)
        self.lyrics_display.setText("")
        
        threading.Thread(
            target=self.process_audio_background,
            daemon=True
        ).start()
    
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
            # Rutas absolutas con verificación
            stems = result['stems']
            self.current_instrumental = self._validate_audio_path(stems.get('instrumental'))
            self.current_vocals = self._validate_audio_path(stems.get('vocals'))
            self.original_song = str(Path(self.current_file).absolute())
            
            # Procesamiento de letras con feedback detallado
            lyrics_info = result.get('lyrics', {})
            if lyrics_info.get('timed_path'):
                lyrics_path = self._validate_lyrics_path(lyrics_info['timed_path'])
                if lyrics_path:
                    if not self.player.load_timed_lyrics_from_json(lyrics_path):
                        QMessageBox.warning(self, "Error", "Las letras no se pudieron cargar. Verifique el formato del archivo.")
            
            # Cargar texto de letras
            if lyrics_info.get('text_path'):
                try:
                    with open(str(Path(lyrics_info['text_path']).absolute()), 'r', encoding='utf-8') as f:
                        self.lyrics_display.setText(f.read())
                except Exception as e:
                    print(f"Info: No se pudo cargar el texto de letras: {str(e)}")
            
            # Habilitar controles
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.vocals_toggle.setEnabled(True)
            
            self.drop_area.setText(f"Listo:\n{os.path.basename(self.current_file)}")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error al finalizar el procesamiento: {str(e)}")
    
    def _validate_audio_path(self, relative_path):
        """Valida y devuelve la ruta absoluta del archivo de audio"""
        if not relative_path:
            raise ValueError("Ruta de audio no especificada")
        
        path = Path(relative_path).absolute()
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo de audio: {path}")
        
        return str(path)
    
    def _validate_lyrics_path(self, relative_path):
        """Valida y devuelve la ruta absoluta del archivo de letras"""
        if not relative_path:
            return None
        
        path = Path(relative_path).absolute()
        if not path.exists():
            print(f"Advertencia: Archivo de letras no encontrado: {path}")
            return None
        
        return str(path)
        
    def play_audio(self):
        """Reproduce la pista instrumental o vocal según el toggle"""
        audio_path = self.current_vocals if self.vocals_toggle.isChecked() else self.current_instrumental
        
        if audio_path and Path(audio_path).exists():
            if self.player.load_audio(audio_path):
                self.player.play()
            else:
                QMessageBox.warning(self, "Error", "No se pudo cargar el audio")
    
    def stop_audio(self):
        """Detiene la reproducción y reinicia la posición"""
        self.player.stop()
        self.song_progress.setValue(0)
    
    def toggle_vocals(self, checked):
        """Alternar entre pista instrumental y canción original"""
        self.vocals_toggle.setText("🎤 Original" if checked else "🎤 Karaoke")
        if checked:
            # Reproducir canción original
            audio_path = self.original_song
        else:
            # Reproducir pista instrumental
            audio_path = self.current_instrumental
        
        if self.player.state() == QMediaPlayer.PlayingState:
            if self.player.load_audio(audio_path):
                self.player.play()
            else:
                QMessageBox.warning(self, "Error", "No se pudo cargar el audio")
    
    def update_song_progress(self, position):
        duration = self.player.duration()
        if duration > 0:
            progress = int((position / duration) * 100)
            self.song_progress.setValue(progress)
    
    def update_lyrics_display(self, current_word, current_time, context_lines):
        """Actualiza la visualización de letras con formato karaoke"""
        if not context_lines:
            return
            
        html_content = ""
        for i, line in enumerate(context_lines):
            if i == 1:  # Línea actual
                # Resaltar palabra actual
                highlighted_line = line.replace(
                    current_word, 
                    f"<span style='color: #4CAF50; font-weight: bold;'>{current_word}</span>"
                )
                html_content += f"<div style='margin: 10px 0; font-size: 22px;'>{highlighted_line}</div>"
            else:
                html_content += f"<div style='margin: 5px 0; font-size: 18px; color: #aaa;'>{line}</div>"
        
        self.lyrics_display.setText(html_content)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            self.handle_new_file(urls[0].toLocalFile())