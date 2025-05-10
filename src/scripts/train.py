import torch
import torch.nn.functional as F
from tqdm import tqdm
import logging
from pathlib import Path
import yaml
import os
from src.libs.demucs_mdx.model_utils import load_pretrained_htdemucs, save_checkpoint
from src.libs.demucs_mdx.data_loader import get_dataloader
from src.libs.demucs_mdx.audio_metrics import AudioMetricsLoss
from demucs.apply import apply_model


# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '../../config/training_params.yaml')
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Asegurar que los valores sean números
    config['optimizer']['lr'] = float(config['optimizer']['lr'])
    config['optimizer']['weight_decay'] = float(config['optimizer']['weight_decay'])
    
    return config

def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    try:
        # Cargar parámetros desde el archivo YAML
        config = load_config()

        # 1. Cargar modelo preentrenado
        model = load_pretrained_htdemucs(device)
        logger.info("Modelo HTDemucs cargado exitosamente")
        
        # 2. Configurar función de pérdida mejorada
        loss_fn = AudioMetricsLoss(device=device)
        
        # 3. Preparar DataLoader con tamaño fijo
        segment_samples = 44100 * 6  # 6 segundos
        train_loader = get_dataloader(
            "data/musdb18hq/train",
            batch_size=config['training']['batch_size'],
            segment_samples=segment_samples
        )
        
        # 4. Configurar optimizador
        optimizer = torch.optim.AdamW(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=config['optimizer']['lr'],
            weight_decay=config['optimizer']['weight_decay']
        )
        
        # 5. Bucle de entrenamiento
        best_loss = float('inf')
        for epoch in range(config['training']['epochs']):
            model.train()
            epoch_loss = 0
            progress = tqdm(train_loader, desc=f"Epoch {epoch+1}/{config['training']['epochs']}")
            
            for batch_idx, batch in enumerate(progress):
                try:
                    # Cargar y preparar datos
                    mix = batch['mix'].to(device)
                    stems = batch['stems'].to(device)
                    
                    # Forward pass usando apply_model
                    pred_stems = apply_model(model, mix, device=device)
                    
                    # Calcular pérdida
                    loss = loss_fn(pred_stems, stems)
                    
                    # Backward pass
                    optimizer.zero_grad()
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                    optimizer.step()
                    
                    # Monitoreo
                    epoch_loss += loss.item()
                    progress.set_postfix(loss=f"{loss.item():.4f}")
                    
                except RuntimeError as e:
                    if 'CUDA out of memory' in str(e):
                        logger.warning("OOM - Saltando batch")
                        torch.cuda.empty_cache()
                        continue
                    raise
                except Exception as e:
                    logger.error(f"Error en batch {batch_idx}: {str(e)}")
                    continue
            
            # Guardar checkpoints
            avg_loss = epoch_loss / len(train_loader)
            
            if avg_loss < best_loss:
                best_loss = avg_loss
                save_path = Path("models/fine_tuned/best_model.pth")
                save_checkpoint(
                    model=model,
                    optimizer=optimizer,
                    epoch=epoch,
                    loss=avg_loss,
                    path=save_path
                )
                logger.info(f"¡Nuevo mejor modelo guardado! Loss: {avg_loss:.4f}")
            
            logger.info(f"Época {epoch+1} completada. Loss promedio: {avg_loss:.4f}")
            
    except Exception as e:
        logger.error(f"Error fatal en entrenamiento: {str(e)}")
        raise
    finally:
        torch.cuda.empty_cache()

if __name__ == "__main__":
    train()
