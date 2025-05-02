import torch
import torchaudio
from src.libs.demucs_mdx.model_utils import load_model
from demucs.apply import apply_model
import logging
from pathlib import Path
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_2d_audio(tensor):
    """Garantiza que el tensor de audio sea 2D [canales, muestras]"""
    if tensor.ndim == 1:
        return tensor.unsqueeze(0)  # Convierte a [1, muestras] (mono)
    elif tensor.ndim == 3:
        return tensor.squeeze(0)  # Elimina dimensión batch [1, canales, muestras] -> [canales, muestras]
    return tensor

def separate_audio(input_path, output_dir="output", model_path="models/final/best_model.pth"):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    try:
        # 1. Cargar modelo
        logger.info(f"Cargando modelo desde {model_path}")
        model = load_model(model_path, device)
        
        # 2. Cargar audio
        logger.info(f"Procesando archivo: {input_path}")
        mix, sr = torchaudio.load(input_path)
        
        # 3. Preprocesamiento
        # Convertir a estéreo si es mono
        if mix.ndim == 1:
            mix = torch.stack([mix, mix])  # [2, muestras]
        elif mix.shape[0] == 1:  # Mono con dimensión channel
            mix = torch.cat([mix, mix])  # [2, muestras]
        
        # Normalizar
        mix = mix / (1.1 * mix.abs().max())
        
        # Añadir dimensión batch [1, canales, muestras]
        mix = mix.unsqueeze(0)
        
        # 4. Separación
        logger.info("Separando pistas...")
        stems = apply_model(
            model,
            mix.to(device),
            split=True,
            overlap=0.25,
            progress=True
        )  # Devuelve [1, 4, canales, muestras]
        
        # 5. Guardar resultados
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Instrumental (suma de drums, bass y other)
        instrumental = stems[:, :3].sum(1)  # [1, canales, muestras]
        instrumental = ensure_2d_audio(instrumental.cpu())
        torchaudio.save(
            str(output_dir/"instrumental.wav"),
            instrumental,
            model.samplerate,
            bits_per_sample=16
        )
        
        # Vocales
        vocals = stems[:, 3]  # [1, canales, muestras]
        vocals = ensure_2d_audio(vocals.cpu())
        torchaudio.save(
            str(output_dir/"vocals.wav"),
            vocals,
            model.samplerate,
            bits_per_sample=16
        )
        
        logger.info(f"Separación completada. Resultados guardados en: {output_dir}")
        logger.info(f"- Pista instrumental: {output_dir/'instrumental.wav'}")
        logger.info(f"- Pista vocal: {output_dir/'vocals.wav'}")
        return True
    
    except Exception as e:
        logger.error(f"Error durante la separación: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Separar audio en instrumental y vocales')
    parser.add_argument("--input", required=True, help="Archivo de audio a separar")
    parser.add_argument("--output", default="output", help="Directorio de salida")
    parser.add_argument("--model", default="models/final_model/best_model.pth", 
                       help="Ruta al modelo entrenado")
    args = parser.parse_args()
    
    success = separate_audio(args.input, args.output, args.model)
    exit(0 if success else 1)