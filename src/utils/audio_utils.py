import torchaudio
import torch
import numpy as np
from typing import Union
from pathlib import Path
from typing import Tuple, Optional
import tempfile
import os
from pydub import AudioSegment
import warnings

def convert_to_wav(input_path: Union[str, Path]) -> Tuple[str, Optional[str]]:
    """Conversión robusta a WAV usando torchaudio"""
    input_path = Path(input_path)
    temp_file = f"{tempfile.gettempdir()}/{input_path.stem}_temp_{os.getpid()}.wav"
    
    try:
        # Cargar con torchaudio que maneja mejor los formatos
        waveform, sample_rate = torchaudio.load(input_path)
        
        # Asegurar formato float32 y rango [-1, 1]
        waveform = waveform.float()
        max_val = waveform.abs().max()
        if max_val > 0:
            waveform /= max_val
        
        # Guardar con torchaudio que garantiza WAV válido
        torchaudio.save(temp_file, waveform, sample_rate, encoding="PCM_S", bits_per_sample=16)
        return temp_file, temp_file
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise RuntimeError(f"Error converting to WAV: {str(e)}")

def normalize_audio(tensor: torch.Tensor) -> torch.Tensor:
    """Normalización profesional del tensor de audio"""
    tensor = tensor.float()  # Asegurar float32
    
    # Normalización espectral para mejor calidad
    max_val = tensor.abs().max()
    if max_val > 1e-7:  # Evitar división por cero
        tensor /= max_val
    
    # Protección contra clipping
    return torch.clamp(tensor, -1.0, 1.0)

def safe_tensor_to_audio(tensor: torch.Tensor, sample_rate: int) -> torch.Tensor:
    """Prepara tensor para guardado seguro"""
    tensor = tensor.detach().cpu()
    
    # Asegurar shape (channels, samples)
    if tensor.dim() == 1:
        tensor = tensor.unsqueeze(0)
    elif tensor.dim() == 3:
        tensor = tensor.squeeze(0)
    
    # Normalización final
    tensor = normalize_audio(tensor)
    
    # Conversión a int16 para compatibilidad universal
    if tensor.dtype != torch.float32:
        tensor = tensor.float()
    
    return tensor

def save_audio(tensor: torch.Tensor, path: Union[str, Path], sample_rate: int):
    """Guarda audio con todas las protecciones"""
    path = Path(path)
    tensor = safe_tensor_to_audio(tensor, sample_rate)
    
    # Guardado temporal primero
    temp_path = f"{tempfile.gettempdir()}/temp_{os.getpid()}_{path.name}"
    torchaudio.save(temp_path, tensor, sample_rate, encoding="PCM_S", bits_per_sample=16)
    
    # Mover al destino final
    os.replace(temp_path, str(path))

def safe_audio_load(path: Union[str, Path]) -> AudioSegment:
    """Carga ultra-segura de audio"""
    path = str(Path(path).resolve())
    try:
        # Primero con torchaudio
        tensor, sr = torchaudio.load(path)
        audio = AudioSegment(
            tensor.numpy().tobytes(),
            frame_rate=sr,
            sample_width=tensor.element_size(),
            channels=tensor.shape[0]
        )
    except Exception as e:
        # Fallback a Pydub con protección
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        audio = AudioSegment.from_file(path)
    
    return _create_clean_audio_segment(audio)

def _create_clean_audio_segment(audio: AudioSegment) -> AudioSegment:
    """Crea una copia completamente limpia de un AudioSegment"""
    clean = audio._spawn(audio.raw_data)
    clean._orig_src = None
    clean.hash = None
    return clean

def save_temp_audio(audio: Union[torch.Tensor, AudioSegment], sample_rate: Optional[int] = None) -> Path:
    """
    Guarda audio en un archivo temporal seguro, manejando ambos tipos (Tensor y AudioSegment)
    Devuelve la ruta al archivo temporal creado
    """
    temp_path = f"{tempfile.gettempdir()}/temp_audio_{os.getpid()}.wav"
    
    if isinstance(audio, torch.Tensor):
        if sample_rate is None:
            raise ValueError("Se requiere sample_rate para tensores")
        save_audio(audio, temp_path, sample_rate)
    elif isinstance(audio, AudioSegment):
        audio.export(temp_path, format="wav")
    else:
        raise TypeError("Tipo de audio no soportado. Debe ser Tensor o AudioSegment")
    
    return Path(temp_path)
