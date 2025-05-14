import whisper
import torch
import torchaudio
from pathlib import Path
import tempfile
import json
import os
import logging
from datetime import datetime
import warnings
import numpy as np
import sys

# Solución para NumPy 2.x
if np.__version__.startswith('2'):
    # Parche para compatibilidad con Whisper
    sys.modules['numpy.core._multiarray_umath'] = np
    np._no_nep50_warning = True

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('audio_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LyricsTranscriber:
    def __init__(self, model_size="medium"):
        """Inicializador con compatibilidad NumPy 2.x"""
        logger.info(f"Inicializando transcriber con modelo {model_size}")
        try:
            # Carga segura con parche NumPy
            self.model = self._safe_load_whisper(model_size)
            device = next(self.model.parameters()).device
            logger.info(f"✅ Modelo cargado en {device}")
        except Exception as e:
            logger.error(f"❌ Error cargando modelo: {str(e)}")
            raise

    def _safe_load_whisper(self, model_size):
        """Carga el modelo Whisper con compatibilidad NumPy 2.x"""
        # Parche temporal para arrays NumPy
        original_from_numpy = torch.from_numpy
        torch.from_numpy = lambda x: original_from_numpy(x.copy())
        
        try:
            model = whisper.load_model(model_size)
        finally:
            torch.from_numpy = original_from_numpy
            
        return model

    def transcribe_audio(self, audio_path, output_dir=None, language=None):
        """Transcripción compatible con NumPy 2.x"""
        audio_path = Path(audio_path)
        temp_wav = None
        
        try:
            # Verificación del archivo
            if not audio_path.exists():
                raise FileNotFoundError(f"Archivo no encontrado: {audio_path}")

            # Conversión a WAV segura
            temp_wav = self._convert_to_wav(audio_path)
            
            # Transcripción con manejo de dispositivo
            result = self._safe_transcribe(temp_wav, language)
            
            # Procesamiento de resultados
            return self._process_results(result, audio_path, output_dir)
            
        finally:
            if temp_wav and os.path.exists(temp_wav):
                try:
                    os.unlink(temp_wav)
                except:
                    pass

    def _convert_to_wav(self, input_path):
        """Conversión optimizada a WAV"""
        temp_path = f"/tmp/whisper_{os.getpid()}.wav"
        waveform, sr = torchaudio.load(input_path)
        
        if sr != 16000:
            waveform = torchaudio.functional.resample(waveform, sr, 16000)
            
        torchaudio.save(temp_path, waveform, 16000, encoding="PCM_S", bits_per_sample=16)
        return temp_path

    def _safe_transcribe(self, audio_path, language):
        """Transcripción con manejo de errores mejorado"""
        original_device = next(self.model.parameters()).device
        
        try:
            # Mover a CPU si hay problemas con CUDA
            if "cuda" in str(original_device):
                self.model.to("cpu")
            
            return self.model.transcribe(
                str(audio_path),
                language=language,
                word_timestamps=True,
                fp16=False,  # Mejor compatibilidad
                verbose=None
            )
        finally:
            self.model.to(original_device)

    def _process_results(self, result, original_path, output_dir):
        """Procesamiento eficiente de resultados"""
        processed = {
            'text': result.get('text', ''),
            'segments': result.get('segments', [])
        }
        
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            self._save_outputs(processed, original_path, output_dir)
            
        return processed

    def _save_outputs(self, result, original_path, output_dir):
        """Guardado seguro de archivos"""
        base_name = original_path.stem
        
        # Archivo de texto
        txt_path = output_dir / f"{base_name}_lyrics.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        
        # Archivo JSON
        json_path = output_dir / f"{base_name}_timed.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result['segments'], f, ensure_ascii=False, indent=2)