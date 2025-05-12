from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
import os
import json
from typing import List, Dict

class KaraokePlayer(QMediaPlayer):
    lyrics_updated = pyqtSignal(str, float)  # palabra_actual, tiempo_actual
    position_changed = pyqtSignal(float)     # posición actual en segundos
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._timed_lyrics: List[Dict] = []
        self._current_word_index: int = 0
        self._lyrics_update_timer = QTimer()
        self._lyrics_update_timer.setInterval(100)  # Actualizar cada 100ms
        self._lyrics_update_timer.timeout.connect(self._update_lyrics_display)
        
        # Conexiones de señales
        self.positionChanged.connect(self._handle_position_changed)
        self.stateChanged.connect(self._handle_state_change)
    
    def load_audio(self, audio_path: str):
        """Carga un archivo de audio para reproducción"""
        if not os.path.exists(audio_path):
            QMessageBox.warning(None, "Error", f"Archivo no encontrado: {audio_path}")
            return False
        
        self.setMedia(QMediaContent(QUrl.fromLocalFile(audio_path)))
        return True
    
    def load_timed_lyrics(self, lyrics_path: str):
        """Carga letras con información de tiempo desde archivo JSON"""
        try:
            with open(lyrics_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.set_timed_lyrics(data.get('segments', []))
            return True
        except Exception as e:
            QMessageBox.warning(None, "Error", f"No se pudieron cargar las letras: {str(e)}")
            return False
    
    def set_timed_lyrics(self, segments: List[Dict]):
        """Configura las letras temporizadas para sincronización"""
        self._timed_lyrics = []
        for segment in segments:
            self._timed_lyrics.extend(segment.get('words', []))
        self._current_word_index = 0
    
    def play(self):
        """Inicia la reproducción con sincronización de letras"""
        super().play()
        if self._timed_lyrics:
            self._lyrics_update_timer.start()
    
    def pause(self):
        """Pausa la reproducción"""
        super().pause()
        self._lyrics_update_timer.stop()
    
    def stop(self):
        """Detiene la reproducción y reinicia las letras"""
        super().stop()
        self._lyrics_update_timer.stop()
        self._current_word_index = 0
        self.lyrics_updated.emit("", 0.0)
    
    def _handle_position_changed(self, position_ms):
        """Emitir posición actual en segundos"""
        self.position_changed.emit(position_ms / 1000)
    
    def _handle_state_change(self, state):
        """Manejar cambios de estado del reproductor"""
        if state == QMediaPlayer.StoppedState:
            self._lyrics_update_timer.stop()
            self._current_word_index = 0
    
    def _update_lyrics_display(self):
        """Actualizar la visualización de letras según el tiempo actual"""
        if not self._timed_lyrics or self.state() != QMediaPlayer.PlayingState:
            return
        
        current_time = self.position() / 1000  # Convertir a segundos
        
        # Avanzar hasta encontrar la palabra actual
        while (self._current_word_index < len(self._timed_lyrics) and (
            current_time >= self._timed_lyrics[self._current_word_index].get('start', 0))
        ):
            self._current_word_index += 1
        
        # Retroceder si necesario (por ejemplo, al hacer seek)
        while (self._current_word_index > 0) and (
            current_time < self._timed_lyrics[self._current_word_index - 1].get('start', 0)
        ):
            self._current_word_index -= 1
        
        # Emitir palabra actual si corresponde
        if 0 < self._current_word_index <= len(self._timed_lyrics):
            current_word = self._timed_lyrics[self._current_word_index - 1]
            self.lyrics_updated.emit(
                current_word.get('word', ''),
                current_time
            )
    
    def seek_to_word(self, word_index: int):
        """Saltar a una palabra específica en las letras"""
        if 0 <= word_index < len(self._timed_lyrics):
            self._current_word_index = word_index
            word_time = self._timed_lyrics[word_index].get('start', 0)
            self.setPosition(int(word_time * 1000))
            if self.state() != QMediaPlayer.PlayingState:
                self._update_lyrics_display()
    
    def get_current_word_index(self) -> int:
        """Obtener el índice de la palabra actual"""
        return max(0, self._current_word_index - 1)
    
    def get_lyrics_data(self) -> List[Dict]:
        """Obtener los datos completos de las letras temporizadas"""
        return self._timed_lyrics