import torch
import torchaudio
from pathlib import Path
import logging
import os
import shutil
from typing import Dict, Optional, Union, Tuple
from src.libs.demucs_mdx.model_utils import load_model
from demucs.apply import apply_model
from src.utils.audio_utils import (
    convert_to_wav,
    normalize_audio,
    save_audio  # Nueva función importada
)

# Configuración básica
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rutas fijas
BASE_DIR = Path(__file__).parent.parent.parent
SONGS_DIR = BASE_DIR / "output" / "original"
OUTPUT_DIR = BASE_DIR / "output" / "stems"
MODEL_PATH = BASE_DIR / "models" / "final_model" / "best_model.pth"

def get_first_song() -> str:
    """Obtiene el primer archivo de audio de la carpeta songs"""
    for ext in ['*.wav', '*.mp3', '*.flac']:
        songs = list(SONGS_DIR.glob(ext))
        if songs:
            return songs[0].name
    raise FileNotFoundError(f"No se encontraron archivos de audio en {SONGS_DIR}")

def ensure_proper_shape(audio: torch.Tensor) -> torch.Tensor:
    """
    Garantiza que el tensor de audio tenga la forma correcta (2D: canales × muestras)
    - Elimina dimensión batch si existe
    - Convierte mono a estéreo si es necesario
    """
    if audio.dim() == 3:  # (batch, channels, samples)
        audio = audio.squeeze(0)
    elif audio.dim() == 1:  # (samples)
        audio = audio.unsqueeze(0)
    
    # Convertir mono a estéreo si es necesario
    if audio.shape[0] == 1:
        audio = torch.cat([audio, audio])
    
    return audio

def separate_audio(
    input_path: Optional[Union[str, Path]] = None,
    output_dir: Union[str, Path] = OUTPUT_DIR,
    model_path: Union[str, Path] = MODEL_PATH
) -> Dict[str, str]:
    """
    Versión corregida con manejo robusto de rutas y procesamiento de audio
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Convertir todas las rutas a objetos Path
    input_path = Path(input_path) if input_path else None
    output_dir = Path(output_dir)
    model_path = Path(model_path)
    
    temp_file = None
    try:
        # 1. Manejo de la ruta de entrada
        if input_path is None:
            input_filename = get_first_song()
            input_path = SONGS_DIR / input_filename
        elif not input_path.is_absolute():
            if str(input_path).startswith("songs/"):
                input_path = BASE_DIR / input_path
            else:
                input_path = SONGS_DIR / input_path.name
        
        # Verificación final de la ruta
        if not input_path.exists():
            available_files = "\n".join(f"- {f.name}" for f in SONGS_DIR.iterdir() if f.is_file())
            raise FileNotFoundError(
                f"Archivo no encontrado: {input_path}\n"
                f"Archivos disponibles en {SONGS_DIR}:\n{available_files}"
            )

        original_name = input_path.stem
        logger.info(f"Procesando archivo: {input_path}")

        # 2. Conversión a WAV si es necesario
        if input_path.suffix.lower() != '.wav':
            logger.info("Convirtiendo a WAV...")
            try:
                audio_path_str, temp_file = convert_to_wav(input_path)
                audio_path = Path(audio_path_str)
                logger.info(f"Archivo WAV temporal creado: {temp_file}")
            except Exception as e:
                raise RuntimeError(f"Error en conversión a WAV: {str(e)}")
        else:
            audio_path = input_path

        # 3. Carga del archivo de audio
        logger.info("Cargando archivo de audio...")
        try:
            if audio_path.suffix.lower() == '.wav':
                mix, sr = torchaudio.load(str(audio_path), backend="soundfile")
            else:
                mix, sr = torchaudio.load(str(audio_path))
        except Exception as e:
            raise RuntimeError(f"Error al cargar el audio: {str(e)}")

        # 4. Preprocesamiento
        logger.info("Preprocesando audio...")
        target_sr = 44100
        
        if sr != target_sr:
            logger.info(f"Resampleando de {sr}Hz a {target_sr}Hz...")
            mix = torchaudio.functional.resample(mix, sr, target_sr)
        
        mix = normalize_audio(mix)
        mix = ensure_proper_shape(mix).unsqueeze(0)  # Añadir dimensión batch

        # 5. Carga del modelo
        logger.info(f"Cargando modelo: {model_path}")
        try:
            model = load_model(str(model_path), device)
            if isinstance(model, tuple):
                model = model[0]
        except Exception as e:
            logger.warning(f"Intento alternativo de carga del modelo: {str(e)}")
            model = load_model(str(model_path), device)
            if isinstance(model, tuple):
                model = model[0]

        # Mover modelo al dispositivo
        model.to(device)

        # 6. Separación
        logger.info("Separando pistas...")
        stems = apply_model(model, mix.to(device), split=True, overlap=0.25)

        # 7. Preparar stems para guardar
        instrumental = stems[:, :3].sum(1)  # Sumar primeros 3 stems
        vocals = stems[:, 3]  # Tomar stem de vocales

        # Asegurar formas correctas
        instrumental = ensure_proper_shape(instrumental.cpu())
        vocals = ensure_proper_shape(vocals.cpu())

        # 8. Guardar resultados usando la función segura de audio_utils
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Limpiar archivos antiguos
        for old_file in output_dir.glob("*.wav"):
            old_file.unlink(missing_ok=True)

        # Rutas de salida
        instrumental_path = output_dir / "instrumental.wav"
        vocals_path = output_dir / "vocals.wav"

        # Usar la nueva función save_audio de audio_utils
        save_audio(instrumental, instrumental_path, target_sr)
        save_audio(vocals, vocals_path, target_sr)

        logger.info(f"★ Separación completada ★\n"
                   f"- Vocales: {vocals_path}\n"
                   f"- Instrumental: {instrumental_path}")
        
        return {
            "vocals": str(vocals_path),
            "instrumental": str(instrumental_path),
            "output_dir": str(output_dir),
            "sample_rate": target_sr,
            "original_name": original_name,
            "input_path": str(input_path)
        }

    except Exception as e:
        logger.error(f"Error durante la separación: {str(e)}", exc_info=True)
        raise

    finally:
        # Limpieza segura de archivos temporales
        if temp_file and os.path.exists(temp_file):
            try:
                if os.path.isfile(temp_file):
                    os.remove(temp_file)
                elif os.path.isdir(temp_file):
                    shutil.rmtree(temp_file)
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo temporal: {str(e)}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description='Separación automática de la primera canción encontrada en /songs',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Nombre específico del archivo en /songs (opcional)"
    )
    parser.add_argument(
        "--output",
        default=OUTPUT_DIR,
        type=Path,
        help="Carpeta de salida (por defecto /output/stems)"
    )
    parser.add_argument(
        "--model",
        default=MODEL_PATH,
        type=Path,
        help="Ruta al modelo preentrenado"
    )
    
    args = parser.parse_args()
    
    try:
        result = separate_audio(args.input, args.output, args.model)
        print("Procesamiento exitoso. Resultados:")
        print(f"Vocales: {result['vocals']}")
        print(f"Instrumental: {result['instrumental']}")
        exit(0)
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)