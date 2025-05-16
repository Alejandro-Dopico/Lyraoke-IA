import whisper
import torch
import torchaudio
from pathlib import Path
import json
import logging
import warnings
from typing import Dict


# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LyricsTranscriber:
    def __init__(self, model_size="medium"):
        logger.info(f"Inicializando transcriber con modelo {model_size}")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(model_size, device=self.device)
        logger.info(f"✅ Modelo cargado en {self.device}")

    def _load_whisper_model(self, model_size):
        """Carga el modelo Whisper con manejo de errores"""
        try:
            model = whisper.load_model(model_size, device=self.device)
            return model
        except Exception as e:
            logger.error(f"Error cargando modelo Whisper: {str(e)}")
            raise

    def transcribe_audio(self, audio_path: str, output_dir: str = None) -> Dict:
        """Transcribe audio y guarda con nombres fijos"""
        try:
            # Verificar archivo
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"Archivo no encontrado: {audio_path}")

            # Transcripción
            result = self.model.transcribe(
                audio_path,
                word_timestamps=True,
                fp16=(self.device == "cuda")
            )

            processed = {
                'text': result.get('text', ''),
                'segments': result.get('segments', [])
            }

            if output_dir:
                # Guardar con nombres fijos
                self._save_results(processed, Path(output_dir))

            return processed
            
        except Exception as e:
            logger.error(f"Error en transcripción: {str(e)}")
            raise

    def _save_results(self, result: Dict, output_dir: Path):
        """Guarda resultados con nombres fijos"""
        output_dir.mkdir(exist_ok=True)
        
        # Archivo de texto (nombre fijo)
        with open(output_dir / "song_lyrics.txt", 'w', encoding='utf-8') as f:
            f.write(result.get('text', ''))
        
        # Archivo JSON (nombre fijo)
        with open(output_dir / "song_timed.json", 'w', encoding='utf-8') as f:
            json.dump(result.get('segments', []), f, ensure_ascii=False, indent=2)