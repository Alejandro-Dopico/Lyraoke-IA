import torch
import torchaudio
from pathlib import Path
import logging
import os
import shutil
from typing import Dict, Union
from src.libs.demucs_mdx.model_utils import load_model
from demucs.apply import apply_model
from src.utils.audio_utils import convert_to_wav, normalize_audio, ensure_2d

# Configuración básica
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rutas fijas
BASE_DIR = Path(__file__).parent.parent.parent
SONGS_DIR = BASE_DIR / "songs"
OUTPUT_DIR = BASE_DIR / "output" / "stems"
MODEL_PATH = BASE_DIR / "models" / "final_model" / "best_model.pth"

def get_first_song() -> str:
    """Obtiene el primer archivo de audio de la carpeta songs"""
    for ext in ['*.wav', '*.mp3', '*.flac']:
        songs = list(SONGS_DIR.glob(ext))
        if songs:
            return songs[0].name
    raise FileNotFoundError(f"No se encontraron archivos de audio en {SONGS_DIR}")

def separate_audio(
    input_filename: str = None,
    output_dir: Path = OUTPUT_DIR,
    model_path: Path = MODEL_PATH
) -> Union[Dict[str, str], bool]:
    """
    Versión mejorada que combina lo mejor de ambos scripts y soluciona los errores
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    try:
        # 1. Obtener archivo a procesar (corregido path duplicado)
        input_filename = input_filename or get_first_song()
        input_path = Path(input_filename)
        if not input_path.is_absolute():
            input_path = SONGS_DIR / input_path.name
        original_name = input_path.stem
        
        # Verificar que el archivo existe
        if not input_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {input_path}")
        
        logger.info(f"Procesando: {input_path.name}")
        
        # 2. Conversión a WAV solo si es necesario (versión robusta)
        temp_file = None
        audio_path = input_path  # Usaremos esta variable para el archivo a procesar
        
        if input_path.suffix.lower() != '.wav':
            try:
                audio_path_str, temp_file = convert_to_wav(input_path)
                audio_path = Path(audio_path_str)

                logger.info(f"Convertido a WAV temporal: {temp_file}")
            except Exception as e:
                raise RuntimeError(f"Error al convertir a WAV: {str(e)}")
        
        # 3. Carga y preprocesamiento (con manejo de errores mejorado)
        try:
            # Usar el backend adecuado según el tipo de archivo
            if audio_path.suffix.lower() == '.wav':
                mix, sr = torchaudio.load(str(audio_path), backend="soundfile")
            else:
                mix, sr = torchaudio.load(str(audio_path))
        except Exception as e:
            raise RuntimeError(f"Error al cargar el archivo de audio: {str(e)}")

        target_sr = 44100
        
        if sr != target_sr:
            mix = torchaudio.functional.resample(mix, sr, target_sr)
            logger.info(f"Resampleado de {sr}Hz a {target_sr}Hz")

        mix = ensure_2d(mix)
        if mix.shape[0] == 1:
            mix = torch.cat([mix, mix])
        mix = normalize_audio(mix).unsqueeze(0)

        # 4. Cargar modelo (versión compatible)
        logger.info(f"Cargando modelo: {model_path}")
        try:
            model = load_model(str(model_path), device)
            # Manejar caso donde devuelve tupla (modelo, otros_datos)
            if isinstance(model, tuple):
                model = model[0]
        except Exception as e:
            logger.warning(f"Intento alternativo de carga del modelo: {str(e)}")
            model = load_model(str(model_path), device)
            if isinstance(model, tuple):
                model = model[0]

        # 5. Separación
        logger.info("Separando pistas...")
        stems = apply_model(model.to(device), mix.to(device), split=True, overlap=0.25)

        # 6. Guardar resultados
        output_dir = Path(output_dir)  # Asegurarse de que output_dir sea un Path
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Limpiar solo archivos WAV antiguos
        for old_file in output_dir.glob("*.wav"):
            try:
                old_file.unlink()
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo antiguo: {str(e)}")
        
        # Rutas de salida con nombre original
        instrumental_path = output_dir / "instrumental.wav"
        vocals_path = output_dir / "vocals.wav"
        
        # Instrumental
        torchaudio.save(
            str(instrumental_path),
            ensure_2d(stems[:, :3].sum(1).cpu()),
            target_sr
        )
        
        # Vocals
        torchaudio.save(
            str(vocals_path),
            ensure_2d(stems[:, 3].cpu()),
            target_sr
        )

        logger.info(f"★ Separación completada ★\n"
                   f"- Entrada: {input_filename}\n"
                   f"- Salida: {output_dir}\n"
                   f"- Instrumental: {instrumental_path}\n"
                   f"- Vocales: {vocals_path}")
        
        # Retorno estructurado para integración
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
        raise  # Re-lanzamos la excepción para manejo externo

    finally:
        # Limpieza segura de archivos temporales
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
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
        type=Path,  # Asegurarse de que esto sea de tipo Path
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
