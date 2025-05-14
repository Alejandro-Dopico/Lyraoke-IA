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
        self.model = self._load_whisper_model(model_size)
        logger.info(f"✅ Modelo cargado en {self.device}")

    def _load_whisper_model(self, model_size):
        """Carga el modelo Whisper con manejo de errores"""
        try:
            model = whisper.load_model(model_size, device=self.device)
            return model
        except Exception as e:
            logger.error(f"Error cargando modelo Whisper: {str(e)}")
            raise

    def transcribe_audio(self, audio_path: str, output_dir: str = None, language: str = None) -> Dict:
        """Transcribe el audio directamente desde el archivo vocals.wav"""
        try:
            # Verificar existencia del archivo
            if not Path(audio_path).exists():
                raise FileNotFoundError(f"Archivo de voces no encontrado: {audio_path}")

            # Transcripción
            result = self.model.transcribe(
                audio_path,
                language=language,
                word_timestamps=True,
                fp16=(self.device == "cuda"),
                verbose=None
            )

            # Procesar resultados
            processed = {
                'text': result.get('text', ''),
                'segments': result.get('segments', [])
            }

            # Guardar resultados si se especifica directorio
            if output_dir:
                self._save_results(processed, Path(audio_path).stem, output_dir)

            return processed
            
        except Exception as e:
            logger.error(f"Error en transcripción: {str(e)}")
            raise

    def _save_results(self, result: Dict, base_name: str, output_dir: Path):
        """Guarda los resultados en archivos"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Archivo de texto
        txt_path = output_dir / f"{base_name}_lyrics.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        
        # Archivo JSON con tiempos
        json_path = output_dir / f"{base_name}_timed.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result['segments'], f, ensure_ascii=False, indent=2)