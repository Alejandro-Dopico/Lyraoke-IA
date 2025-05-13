import torchaudio
import torch
from pydub import AudioSegment
import numpy as np
import warnings
from pathlib import Path
from typing import Union, Tuple
import os

def safe_audio_load(path: Union[str, Path]) -> AudioSegment:
    """Carga completamente segura de archivos de audio"""
    path = str(Path(path).resolve())
    
    # Primero cargamos con torchaudio para decodificación precisa
    try:
        tensor, sr = torchaudio.load(path)
        return tensor_to_audio_segment(tensor, sr)
    except:
        # Fallback a Pydub si torchaudio falla
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            audio = AudioSegment.from_file(path)
            return audio._spawn(audio.raw_data)

def safe_audio_export(
    audio: AudioSegment, 
    output_path: Union[str, Path],
    format: str = None,
    bitrate: str = None
) -> None:
    """Exportación ultra-segura de audio"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    format = format or output_path.suffix[1:]
    if format == 'mp3' and not bitrate:
        bitrate = '320k'
    
    # Crear copia completamente limpia
    clean_audio = audio._spawn(audio.raw_data)
    clean_audio.frame_rate = audio.frame_rate
    clean_audio.sample_width = audio.sample_width
    clean_audio.channels = audio.channels
    
    # Exportar con manejo de errores
    try:
        args = {'format': format}
        if bitrate:
            args['bitrate'] = bitrate
            
        clean_audio.export(str(output_path), **args)
    except Exception as e:
        raise RuntimeError(f"Error exporting audio: {str(e)}")

def tensor_to_audio_segment(
    tensor: torch.Tensor,
    sample_rate: int
) -> AudioSegment:
    """Conversión segura de tensor a AudioSegment"""
    np_audio = tensor.squeeze().numpy()
    
    # Normalización adicional
    if np_audio.max() > 1.0 or np_audio.min() < -1.0:
        np_audio = np.clip(np_audio, -1.0, 1.0)
    
    return AudioSegment(
        np_audio.tobytes(),
        frame_rate=sample_rate,
        sample_width=np_audio.dtype.itemsize,
        channels=1 if len(np_audio.shape) == 1 else 2
    )

def convert_to_wav(input_path: Union[str, Path]) -> Tuple[str, str]:
    """Conversión a WAV con manejo completo de errores"""
    input_path = Path(input_path)
    temp_file = f"/tmp/{input_path.stem}_temp_{os.getpid()}.wav"
    
    try:
        audio = safe_audio_load(input_path)
        safe_audio_export(audio, temp_file, format='wav')
        return temp_file, temp_file
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise RuntimeError(f"Error converting to WAV: {str(e)}")

def normalize_audio(tensor: torch.Tensor) -> torch.Tensor:
    """Normalización segura del tensor de audio"""
    max_val = tensor.abs().max()
    return tensor / max_val if max_val > 0 else tensor