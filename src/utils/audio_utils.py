import torchaudio
import torch
from pathlib import Path
import tempfile
import logging
from typing import Tuple
import numpy as np

logger = logging.getLogger(__name__)

def convert_to_wav(input_path: str, target_sr: int = 44100) -> Tuple[str, int]:
    """
    Convierte cualquier archivo de audio a WAV con la frecuencia objetivo.
    Devuelve la ruta temporal del archivo convertido y la frecuencia real.
    """
    input_path = Path(input_path)
    temp_wav = f"{tempfile.gettempdir()}/{input_path.stem}_converted.wav"
    
    try:
        # Intenta con torchaudio primero
        audio, sr = torchaudio.load(input_path)
        if sr != target_sr:
            audio = torchaudio.functional.resample(audio, sr, target_sr)
        torchaudio.save(temp_wav, audio, target_sr)
        return temp_wav, target_sr
        
    except RuntimeError:
        # Fallback a FFMPEG para formatos complejos
        try:
            import ffmpeg
            (
                ffmpeg.input(str(input_path))
                .output(temp_wav, ar=target_sr, ac=2, acodec='pcm_s16le')
                .run(quiet=True, overwrite_output=True)
            )
            return temp_wav, target_sr
        except Exception as e:
            logger.error(f"No se pudo convertir {input_path}: {str(e)}")
            raise

def normalize_audio(audio: torch.Tensor) -> torch.Tensor:
    """Normaliza el audio a [-1, 1]"""
    return audio / (1.1 * audio.abs().max())

def ensure_2d(audio: torch.Tensor) -> torch.Tensor:
    """Garantiza formato [canales, muestras]"""
    if audio.ndim == 1:
        return audio.unsqueeze(0)
    elif audio.ndim == 3:
        return audio.squeeze(0)
    return audio