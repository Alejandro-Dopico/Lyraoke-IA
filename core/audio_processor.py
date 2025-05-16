import os
import shutil
from pathlib import Path
from typing import Dict, Union
from src.scripts.separate import separate_audio
from src.scripts.transcribe import LyricsTranscriber
from pydub import AudioSegment

class AudioProcessor:
    def __init__(self, model_size="medium"):
        self.transcriber = LyricsTranscriber(model_size=model_size)

    def process_audio(self, input_path: Union[str, Path], output_base_dir: str = "output") -> Dict:
        try:
            input_path = Path(input_path)
            output_dir = Path(output_base_dir)
            
            # Crear estructura de directorios
            stems_dir = output_dir / "stems"
            lyrics_dir = output_dir / "lyrics"
            original_dir = output_dir / "original"
            
            # Limpiar y crear directorios
            shutil.rmtree(output_dir, ignore_errors=True)
            stems_dir.mkdir(parents=True, exist_ok=True)
            lyrics_dir.mkdir(parents=True, exist_ok=True)
            original_dir.mkdir(parents=True, exist_ok=True)

            # 1. Convertir el original a WAV estándar
            original_wav = original_dir / "song.wav"
            self._convert_to_standard_wav(input_path, original_wav)

            # 2. Separación de stems
            stems_result = separate_audio(
                input_path=str(original_wav),
                output_dir=str(stems_dir)
            )
            
            # 3. Verificar stems
            vocals_wav = stems_dir / 'vocals.wav'
            instrumental_wav = stems_dir / 'instrumental.wav'
            
            if not vocals_wav.exists():
                raise RuntimeError("No se generó el archivo vocals.wav")

            # 4. Transcripción con nombres fijos
            lyrics_result = self.transcriber.transcribe_audio(
                audio_path=str(vocals_wav),
                output_dir=str(lyrics_dir)
            )
            
            # Rutas fijas para los archivos de letras
            text_path = lyrics_dir / "song_lyrics.txt"
            timed_path = lyrics_dir / "song_timed.json"
            
            return {
                'original': str(original_wav),
                'stems': {
                    'vocals': str(vocals_wav),
                    'instrumental': str(instrumental_wav)
                },
                'lyrics': {
                    'text_path': str(text_path),
                    'timed_path': str(timed_path),
                    'data': lyrics_result
                }
            }

        except Exception as e:
            print(f"Error en procesamiento: {str(e)}")
            raise

    def _convert_to_standard_wav(self, input_path: Path, output_path: Path):
        """Conversión a WAV con parámetros fijos"""
        audio = AudioSegment.from_file(input_path)
        audio.export(
            output_path,
            format="wav",
            codec="pcm_s16le",
            parameters=["-ac", "2", "-ar", "44100"]
        )