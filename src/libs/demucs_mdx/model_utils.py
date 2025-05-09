import torch
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_pretrained_htdemucs(device, focus='instrumental'):
    """Versión alternativa que descarga los pesos directamente"""
    try:
        from demucs.pretrained import get_model
        model = get_model('htdemucs')
        
        # Configuración de enfoque
        if focus == 'instrumental':
            for name, param in model.named_parameters():
                param.requires_grad = 'decoder' in name and '3' not in name
        else:
            for param in model.parameters():
                param.requires_grad = True
        
        model.to(device)
        return model
    except Exception as e:
        logger.error(f"Error alternativa: {e}")
        raise RuntimeError("Falló la carga alternativa del modelo")

def load_model(model_path, device, weights_only=False, focus='instrumental'):
    """Versión mejorada que maneja diferentes formatos de checkpoint"""
    try:
        # Primero intenta cargar como checkpoint completo
        checkpoint = torch.load(model_path, map_location=device)
        
        # Caso 1: Es un checkpoint completo (como lo guarda save_checkpoint)
        if 'model_state_dict' in checkpoint:
            model = load_pretrained_htdemucs(device, focus)
            model.load_state_dict(checkpoint['model_state_dict'])
            return model, checkpoint
        
        # Caso 2: Es solo el state_dict del modelo
        elif 'state_dict' in checkpoint:
            model = load_pretrained_htdemucs(device, focus)
            model.load_state_dict(checkpoint['state_dict'])
            return model, checkpoint
            
        # Caso 3: El archivo es directamente el state_dict
        else:
            model = load_pretrained_htdemucs(device, focus)
            model.load_state_dict(checkpoint)
            return model, None
            
    except Exception as e:
        logger.error(f"Error cargando modelo: {str(e)}")
        # Fallback a modelo preentrenado si hay error
        logger.warning("Usando modelo preentrenado como fallback")
        return load_pretrained_htdemucs(device, focus), None

def save_best_model(model, optimizer, epoch, metric, path):
    """Guarda el mejor modelo con toda la metadata relevante"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'metric': metric,
        'config': {
            'focus': 'instrumental',
            'architecture': 'htdemucs'
        }
    }, path)
    logger.info(f"Mejor modelo guardado en {path} (Métrica: {metric:.2f})")

def save_checkpoint(model, optimizer, epoch, loss, path):
    """Guarda el estado del entrenamiento"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'loss': loss,
    }, path)
    logger.info(f"Checkpoint guardado en {path}")

    # En model_utils.py añade:
def load_checkpoint(path, device):
    checkpoint = torch.load(path, map_location=device)
    model = load_pretrained_htdemucs(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    return model, checkpoint