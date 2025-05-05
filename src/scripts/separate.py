import torch
import torchaudio
from pathlib import Path
import logging
import os
from src.libs.demucs_mdx.model_utils import load_model
from demucs.apply import apply_model
from src.utils.audio_utils import convert_to_wav, normalize_audio, ensure_2d

# Configuración básica
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rutas fijas
BASE_DIR = Path(__file__).parent.parent.parent
SONGS_DIR = BASE_DIR / "songs"
OUTPUT_DIR = BASE_DIR / "output"
MODEL_PATH = BASE_DIR / "models" / "final_model" / "best_model.pth"

def get_first_song():
    """Obtiene el primer archivo de audio de la carpeta songs"""
    for ext in ['*.wav', '*.mp3', '*.flac']:
        songs = list(SONGS_DIR.glob(ext))
        if songs:
            return songs[0].name
    raise FileNotFoundError(f"No se encontraron archivos de audio en {SONGS_DIR}")

def separate_audio(input_filename: str = None, output_dir: Path = OUTPUT_DIR, model_path: Path = MODEL_PATH) -> bool:
    """
    Procesa automáticamente el primer archivo de la carpeta songs
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    try:
        # 1. Obtener archivo a procesar
        input_filename = input_filename or get_first_song()
        input_path = SONGS_DIR / input_filename
        
        logger.info(f"Procesando: {input_path.name}")
        
        # 2. Conversión a WAV si es necesario
        temp_file = None
        if not input_path.suffix.lower() == '.wav':
            input_path, temp_file = convert_to_wav(input_path)
            logger.info(f"Convertido a WAV temporal: {temp_file}")

        # 3. Carga y preprocesamiento
        mix, sr = torchaudio.load(input_path)
        target_sr = 44100  # Frecuencia fija requerida por el modelo
        
        if sr != target_sr:
            mix = torchaudio.functional.resample(mix, sr, target_sr)
            logger.info(f"Resampleado de {sr}Hz a {target_sr}Hz")

        mix = ensure_2d(mix)
        if mix.shape[0] == 1:  # Conversión mono → estéreo
            mix = torch.cat([mix, mix])
        mix = normalize_audio(mix).unsqueeze(0)

        # 4. Cargar modelo con seguridad
        logger.info(f"Cargando modelo: {model_path}")
        try:
            model = load_model(str(model_path), device, weights_only=True)  # Modo seguro
        except:
            logger.warning("Fallando a carga estándar (sin weights_only)")
            model = load_model(str(model_path), device)

        # 5. Separación
        logger.info("Separando pistas...")
        stems = apply_model(model, mix.to(device), split=True, overlap=0.25)

        # 6. Guardar resultados
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Instrumental (drums + bass + other)
        torchaudio.save(
            str(output_dir / "instrumental.wav"),
            ensure_2d(stems[:, :3].sum(1).cpu()),
            target_sr  # Frecuencia consistente
        )
        
        # Vocals
        torchaudio.save(
            str(output_dir / "vocals.wav"),
            ensure_2d(stems[:, 3].cpu()),
            target_sr
        )

        logger.info(f"★ Separación completada ★\n"
                   f"- Entrada: {input_filename}\n"
                   f"- Salida: {output_dir}\n"
                   f"- Instrumental: {output_dir/'instrumental.wav'}\n"
                   f"- Vocales: {output_dir/'vocals.wav'}")
        return True

    except Exception as e:
        logger.error(f"Error durante la separación: {str(e)}", exc_info=True)
        return False
        
    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)

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
        help="Carpeta de salida (por defecto /output)"
    )
    parser.add_argument(
        "--model",
        default=MODEL_PATH,
        type=Path,
        help="Ruta al modelo preentrenado"
    )
    
    args = parser.parse_args()
    
    success = separate_audio(args.input, args.output, args.model)
    exit(0 if success else 1)