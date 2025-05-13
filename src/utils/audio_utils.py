import os
import tempfile
import torchaudio
import torch
import ffmpeg
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def convert_to_wav(input_path: Path) -> tuple[str, str]:
    """Convierte cualquier archivo de audio a WAV temporal"""
    try:
        # Verificar que es un archivo, no directorio
        if not input_path.is_file():
            raise ValueError(f"La ruta no es un archivo: {input_path}")
        
        # Crear archivo temporal
        temp_dir = tempfile.mkdtemp()
        output_path = os.path.join(temp_dir, f"temp_{input_path.stem}.wav")
        
        # Conversión con ffmpeg
        (
            ffmpeg.input(str(input_path))
            .output(output_path, acodec='pcm_s16le', ar='44100', ac=2)
            .run(quiet=True, overwrite_output=True)
        )
        
        return output_path, temp_dir
    except Exception as e:
        logger.error(f"Error al convertir {input_path} a WAV: {str(e)}")
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        raise

def normalize_audio(audio: torch.Tensor) -> torch.Tensor:
    """Normaliza el audio a rango [-1, 1]"""
    return audio / audio.abs().max()

def ensure_2d(audio: torch.Tensor) -> torch.Tensor:
    """Asegura que el audio sea 2D (canales, muestras)"""
    if audio.dim() == 1:
        return audio.unsqueeze(0)
    return audio