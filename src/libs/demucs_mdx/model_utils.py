import torch
from demucs.pretrained import get_model as get_pretrained_model
from demucs.htdemucs import HTDemucs
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_pretrained_htdemucs(device='cuda'):
    """Carga el modelo pre-entrenado HTDemucs"""
    try:
        model = get_pretrained_model('htdemucs')
        
        if hasattr(model, 'models'):
            logger.info("Modelo BagOfModels - Usando primer submodelo")
            model = model.models[0]
        
        # Configuración personalizada
        model.samplerate = 44100
        model.audio_channels = 2
        model.wiener_iters = 0
        
        model.to(device)
        logger.info(f"Modelo cargado en {device}")
        return model
        
    except Exception as e:
        logger.error(f"Error cargando modelo: {str(e)}")
        raise

def save_checkpoint(model, optimizer=None, epoch=None, loss=None, path='checkpoint.pth'):
    """Guarda el estado del modelo"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    torch.save({
        'state_dict': model.state_dict(),
        'optimizer': optimizer.state_dict() if optimizer else None,
        'epoch': epoch,
        'loss': loss,
        'config': {
            'sources': model.sources,
            'samplerate': model.samplerate,
            'audio_channels': model.audio_channels
        }
    }, path)
    logger.info(f"Checkpoint guardado en {path}")

def load_model(model_path, device='cuda'):
    """Carga un modelo desde checkpoint"""
    try:
        # Cargar modelo base
        base_model = get_pretrained_model('htdemucs')
        if hasattr(base_model, 'models'):
            model = base_model.models[0]
        else:
            model = base_model
        
        # Cargar estado
        state = torch.load(model_path, map_location='cpu')
        
        # Cargar pesos
        if 'state_dict' in state:
            model.load_state_dict(state['state_dict'])
        else:  # Compatibilidad con checkpoints antiguos
            model.load_state_dict(state)
        
        model.to(device)
        model.eval()
        
        logger.info(f"Modelo cargado desde {model_path}")
        return model
        
    except Exception as e:
        logger.error(f"Error cargando modelo: {str(e)}")
        raise