from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtCore import QUrl, QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import QMessageBox
import os
import json
from pathlib import Path
from typing import List, Dict
import tempfile
from pydub import AudioSegment
import time

class KaraokePlayer(QMediaPlayer):
    lyrics_updated = pyqtSignal(str, float, list)  # palabra_actual, tiempo_actual, contexto
    position_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._timed_lyrics: List[Dict] = []
        self._current_segment_index: int = 0
        self._lyrics_update_timer = QTimer()
        self._lyrics_update_timer.setInterval(100)  # 100ms
        self._lyrics_update_timer.timeout.connect(self._update_lyrics_display)
        self._temp_files = []
        
        self.positionChanged.connect(self._handle_position_changed)
        self.stateChanged.connect(self._handle_state_change)
    
    def __del__(self):
        """Limpiar archivos temporales"""
        for temp_file in self._temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass

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
            
            if path.suffix.lower() not in ['.wav', '.mp3']:
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
        """Carga letras temporizadas desde archivo JSON con manejo robusto de errores"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Verificación profunda de la estructura
                if not isinstance(data, list):
                    raise ValueError("El archivo JSON no contiene una lista de segmentos")
                
                self._timed_lyrics = []
                for segment in data:
                    if not isinstance(segment, dict):
                        continue
                    
                    # Verificar campos esenciales
                    if 'words' not in segment or not isinstance(segment['words'], list):
                        continue
                    
                    segment_text = segment.get('text', '').strip()
                    if not segment_text:
                        continue
                    
                    # Procesar cada palabra con validación
                    for word in segment['words']:
                        if not isinstance(word, dict):
                            continue
                        
                        if 'word' not in word or 'start' not in word:
                            continue
                        
                        # Asegurar que los tiempos sean números válidos
                        try:
                            start = float(word['start'])
                            end = float(word.get('end', start + 1.0))  # Valor por defecto si no hay 'end'
                        except (TypeError, ValueError):
                            continue
                        
                        # Crear entrada de palabra con datos limpios
                        clean_word = {
                            'word': str(word['word']).strip(),
                            'start': start,
                            'end': end,
                            'segment_text': segment_text
                        }
                        
                        if clean_word['word']:  # Solo añadir si hay texto
                            self._timed_lyrics.append(clean_word)
                
                if not self._timed_lyrics:
                    raise ValueError("El archivo no contiene palabras válidas con tiempos")
                
                # Ordenar las palabras por tiempo de inicio
                self._timed_lyrics.sort(key=lambda x: x['start'])
                self._current_segment_index = 0
                return True
                
        except json.JSONDecodeError as e:
            error_msg = f"Error de sintaxis en el JSON: {str(e)}"
        except Exception as e:
            error_msg = f"Error al procesar letras: {str(e)}"
        
        QMessageBox.warning(None, "Error", f"No se pudieron cargar las letras: {error_msg}")
        return False

    def play(self):
        """Inicia reproducción con sincronización de letras"""
        super().play()
        if self._timed_lyrics:
            self._lyrics_update_timer.start()

    def pause(self):
        """Pausa la reproducción"""
        super().pause()
        self._lyrics_update_timer.stop()

    def stop(self):
        """Detiene la reproducción y reinicia la posición"""
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
                if text and text not in context_lines:
                    context_lines.append(text)
            
            self.lyrics_updated.emit(
                current_segment.get('word', ''),
                current_time,
                context_lines
            )