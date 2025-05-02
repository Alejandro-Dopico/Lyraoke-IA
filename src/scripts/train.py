import torch
import torch.nn.functional as F
from tqdm import tqdm
from src.libs.demucs_mdx.data_loader import get_dataloader
from src.libs.demucs_mdx.model_utils import load_pretrained_htdemucs, save_checkpoint
import logging
from pathlib import Path
import gc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_grad_scaler(device_type):
    """Versión compatible de GradScaler para todas versiones de PyTorch"""
    if device_type == 'cuda':
        try:
            # Para PyTorch 1.9.0+
            return torch.cuda.amp.GradScaler()
        except Exception:
            # Fallback para versiones muy antiguas
            return None
    return None

def train():
    # 1. Configuración inicial
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Usando dispositivo: {device}")
    
    # 2. Cargar modelo
    model = load_pretrained_htdemucs(device)
    logger.info(f"Total parámetros: {sum(p.numel() for p in model.parameters()):,}")
    
    # 3. Congelar capas (excepto decoders)
    for name, param in model.named_parameters():
        param.requires_grad = 'decoder' in name or 'decoders' in name
    logger.info(f"Parámetros entrenables: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    # 4. Configurar precisión mixta
    use_amp = device.type == 'cuda'
    scaler = get_grad_scaler(device.type)
    logger.info(f"Usando AMP: {use_amp}, Scaler: {scaler is not None}")

    # 5. Optimizador
    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=1e-5,
        weight_decay=1e-6
    )

    # 6. DataLoader
    train_loader = get_dataloader("data/musdb18hq/train", batch_size=1, num_workers=4)

    # 7. Entrenamiento
    best_loss = float('inf')
    for epoch in range(10):  # 10 épocas
        model.train()
        epoch_loss = 0
        
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}")
        for batch in progress_bar:
            try:
                # Forward pass con autocast
                with torch.autocast(device_type=device.type, enabled=use_amp, dtype=torch.float16):
                    mix = batch['mix'].to(device, non_blocking=True)
                    stems = batch['stems'].to(device, non_blocking=True)
                    
                    optimizer.zero_grad(set_to_none=True)
                    pred_stems = model(mix)
                    
                    # Pérdida compuesta
                    loss = 0.7 * F.l1_loss(pred_stems[:,3], stems[:,3]) + \
                           0.3 * F.l1_loss(pred_stems[:,:3].sum(1), stems[:,:3].sum(1))

                # Backward pass
                if scaler:
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    optimizer.step()
                
                epoch_loss += loss.item()
                progress_bar.set_postfix(loss=f"{loss.item():.4f}")
                
                # Limpieza de memoria
                del mix, stems, pred_stems
                gc.collect()
                torch.cuda.empty_cache()
                    
            except RuntimeError as e:
                if 'CUDA out of memory' in str(e):
                    logger.warning("OOM - Saltando batch")
                    torch.cuda.empty_cache()
                    continue
                raise

        # Guardar checkpoint
        avg_loss = epoch_loss / len(train_loader)
        logger.info(f"Época {epoch+1} - Loss: {avg_loss:.4f}")
        
        # Guardar mejor modelo
        if avg_loss < best_loss:
            best_loss = avg_loss
            save_checkpoint(model, optimizer, epoch+1, avg_loss, "models/fine_tuned/best_model.pth")
            logger.info("¡Nuevo mejor modelo guardado!")
        
        save_checkpoint(model, optimizer, epoch+1, avg_loss, f"models/fine_tuned/epoch_{epoch+1}.pth")

if __name__ == "__main__":
    train()