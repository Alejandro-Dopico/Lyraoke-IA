import torch
import torchaudio
from pathlib import Path
import logging
import os
import shutil
from typing import Dict, Optional, Union
from demucs.pretrained import get_model  # Para el modelo preentrenado
from demucs.apply import apply_model
from src.utils.audio_utils import (
    convert_to_wav,
    normalize_audio,
    save_audio
)

# Configuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.parent
SONGS_DIR = BASE_DIR / "output" / "original"
OUTPUT_DIR = BASE_DIR / "output" / "stems"
MODEL_PATH = BASE_DIR / "models" / "final_model" / "best_model.pth"

def load_custom_model(model_path: Union[str, Path], device: torch.device):
    """Carga el modelo custom manteniendo compatibilidad con diferentes formatos de state_dict"""
    try:
        logger.info(f"Intentando cargar modelo custom: {model_path}")
        
        # 1. Cargar state_dict
        state_dict = torch.load(model_path, map_location=device)
        
        # 2. Cargar arquitectura base
        model = get_model('htdemucs').models[0]
        
        # 3. Compatibilidad con nombres de parámetros
        # Caso 1: State_dict con prefijo 'models.0.' (BagOfModels)
        if any(k.startswith('models.0.') for k in state_dict.keys()):
            state_dict = {k.replace('models.0.', ''): v for k, v in state_dict.items()}
        
        # Caso 2: State_dict con prefijo 'model.' (algunas versiones)
        elif any(k.startswith('model.') for k in state_dict.keys()):
            state_dict = {k.replace('model.', ''): v for k, v in state_dict.items()}
        
        # 4. Cargar pesos (con manejo de errores detallado)
        missing_keys, unexpected_keys = model.load_state_dict(state_dict, strict=False)
        
        if missing_keys:
            logger.warning(f"Claves faltantes en state_dict: {missing_keys[:3]}... (total: {len(missing_keys)})")
        if unexpected_keys:
            logger.warning(f"Claves inesperadas en state_dict: {unexpected_keys[:3]}... (total: {len(unexpected_keys)})")
        
        model.to(device)
        
        # Verificación final
        if len(missing_keys) > len(model.state_dict().keys()) / 2:  # Si faltan más del 50%
            raise ValueError("El state_dict no coincide con la arquitectura del modelo")
            
        logger.info("✅ Modelo custom cargado correctamente")
        return model
        
    except Exception as e:
        logger.error(f"Error al cargar modelo custom: {str(e)}")
        logger.info("🔄 Cargando modelo preentrenado como fallback...")
        
        model = get_model('htdemucs')
        if hasattr(model, 'models'):
            model = model.models[0]
        model.to(device)
        
        return model

def get_first_song() -> str:
    """Obtiene el primer archivo de audio disponible"""
    for ext in ['*.wav', '*.mp3', '*.flac']:
        songs = list(SONGS_DIR.glob(ext))
        if songs:
            return songs[0].name
    raise FileNotFoundError(f"No se encontraron archivos en {SONGS_DIR}")

def ensure_proper_shape(audio: torch.Tensor) -> torch.Tensor:
    """Garantiza la forma correcta del tensor de audio"""
    if audio.dim() == 3:
        audio = audio.squeeze(0)
    elif audio.dim() == 1:
        audio = audio.unsqueeze(0)
    if audio.shape[0] == 1:
        audio = torch.cat([audio, audio])
    return audio

def separate_audio(
    input_path: Optional[Union[str, Path]] = None,
    output_dir: Union[str, Path] = OUTPUT_DIR,
    model_path: Union[str, Path] = MODEL_PATH
) -> Dict[str, str]:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    output_dir = Path(output_dir)
    model_path = Path(model_path)
    
    temp_file = None
    try:
        # Manejo de la ruta de entrada
        if input_path is None:
            input_filename = get_first_song()
            input_path = SONGS_DIR / input_filename
        else:
            input_path = Path(input_path)
            if not input_path.is_absolute():
                input_path = SONGS_DIR / input_path.name

        if not input_path.exists():
            available = "\n".join(f"- {f.name}" for f in SONGS_DIR.iterdir() if f.is_file())
            raise FileNotFoundError(f"Archivo no encontrado. Disponibles:\n{available}")

        original_name = input_path.stem
        logger.info(f"Procesando: {input_path}")

        # Conversión a WAV si es necesario
        if input_path.suffix.lower() != '.wav':
            logger.info("Convirtiendo a WAV...")
            audio_path_str, temp_file = convert_to_wav(input_path)
            audio_path = Path(audio_path_str)
        else:
            audio_path = input_path

        # Carga del audio
        logger.info("Cargando audio...")
        try:
            mix, sr = torchaudio.load(str(audio_path), backend="soundfile")
        except Exception as e:
            raise RuntimeError(f"Error al cargar audio: {str(e)}")

        # Preprocesamiento
        logger.info("Preprocesando...")
        target_sr = 44100
        
        if sr != target_sr:
            logger.info(f"Resampleando de {sr}Hz a {target_sr}Hz...")
            mix = torchaudio.functional.resample(mix, sr, target_sr)
        
        mix = normalize_audio(mix)
        mix = ensure_proper_shape(mix).unsqueeze(0)

        # Carga del modelo (primero custom, luego preentrenado como fallback)
        model = load_custom_model(model_path, device)
        model.to(device)

        # Separación
        logger.info("Separando pistas...")
        stems = apply_model(model, mix.to(device), split=True, overlap=0.25)

        # Preparar stems
        instrumental = stems[:, :3].sum(1)  # Sumar drums, bass, other
        vocals = stems[:, 3]  # Vocales

        # Asegurar formas
        instrumental = ensure_proper_shape(instrumental.cpu())
        vocals = ensure_proper_shape(vocals.cpu())

        # Guardar resultados
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Limpiar archivos antiguos
        for old_file in output_dir.glob("*.wav"):
            old_file.unlink(missing_ok=True)

        # Rutas de salida con nombre original
        instrumental_path = output_dir / "instrumental.wav"
        vocals_path = output_dir / "vocals.wav"

        save_audio(instrumental, instrumental_path, target_sr)
        save_audio(vocals, vocals_path, target_sr)

        logger.info(f"★ Separación completada ★\n"
                   f"- Vocales: {vocals_path}\n"
                   f"- Instrumental: {instrumental_path}")
        
        return {
            "vocals": str(vocals_path),
            "instrumental": str(instrumental_path),
            "output_dir": str(output_dir),
            "model_used": "custom" if "custom" in str(model_path) else "pretrained"
        }

    except Exception as e:
        logger.error(f"Error durante la separación: {str(e)}", exc_info=True)
        raise

    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                logger.warning(f"No se pudo eliminar temporal: {str(e)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='Separador de audio con prioridad a modelo fine-tuned',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Ruta al archivo de entrada (opcional)"
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_DIR,
        type=Path,
        help="Directorio de salida"
    )
    parser.add_argument(
        "--model",
        default=MODEL_PATH,
        type=Path,
        help="Ruta al modelo fine-tuned (por defecto best_model.pth)"
    )
    
    args = parser.parse_args()
    
    try:
        result = separate_audio(args.input, args.output, args.model)
        print(f"Procesamiento exitoso (modelo: {result['model_used']})")
        print(f"Vocales: {result['vocals']}")
        print(f"Instrumental: {result['instrumental']}")
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)