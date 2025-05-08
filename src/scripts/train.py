import torch
import torch.nn.functional as F
from tqdm import tqdm
from src.libs.demucs_mdx.data_loader import get_dataloader
from src.libs.demucs_mdx.model_utils import load_pretrained_htdemucs, save_checkpoint
import logging
from pathlib import Path
import gc
import yaml
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '../../config/training_params.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_grad_scaler(device_type):
    if device_type == 'cuda':
        try:
            return torch.cuda.amp.GradScaler()
        except Exception:
            return None
    return None

def train():
    # 1. Cargar configuración
    config = load_config()

    # 2. Configuración inicial
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Usando dispositivo: {device}")
    
    # 3. Cargar modelo
    model = load_pretrained_htdemucs(device)
    logger.info(f"Total parámetros: {sum(p.numel() for p in model.parameters()):,}")
    
    for name, param in model.named_parameters():
        param.requires_grad = 'decoder' in name or 'decoders' in name
    logger.info(f"Parámetros entrenables: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    # 4. AMP
    use_amp = config['training'].get('amp', True)
    use_scaler = config['training'].get('use_scaler', True)
    scaler = get_grad_scaler(device.type) if use_amp and use_scaler else None
    logger.info(f"Usando AMP: {use_amp}, Scaler: {scaler is not None}")

    # 5. Optimizer (desde config)
    optimizer_cfg = config['optimizer']
    optimizer_class = getattr(torch.optim, optimizer_cfg['type'])
    optimizer = optimizer_class(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=optimizer_cfg['lr'],
        weight_decay=optimizer_cfg['weight_decay']
    )

    # 6. Scheduler (opcional)
    scheduler = None
    if config['scheduler'].get('enabled', False):
        scheduler_cfg = config['scheduler']
        scheduler_class = getattr(torch.optim.lr_scheduler, scheduler_cfg['type'])
        scheduler = scheduler_class(
            optimizer,
            step_size=scheduler_cfg['step_size'],
            gamma=scheduler_cfg['gamma']
        )

    # 7. DataLoader
    batch_size = config['training']['batch_size']
    train_loader = get_dataloader("data/musdb18hq/train", batch_size=batch_size, num_workers=4)

    # 8. Training loop
    epochs = config['training']['epochs']
    best_loss = float('inf')
    
    for epoch in range(epochs):
        model.train()
        epoch_loss = 0
        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")

        for batch in progress_bar:
            try:
                with torch.autocast(device_type=device.type, enabled=use_amp, dtype=torch.float16):
                    mix = batch['mix'].to(device, non_blocking=True)
                    stems = batch['stems'].to(device, non_blocking=True)
                    
                    optimizer.zero_grad(set_to_none=True)
                    pred_stems = model(mix)
                    
                    loss = 0.7 * F.l1_loss(pred_stems[:,3], stems[:,3]) + \
                           0.3 * F.l1_loss(pred_stems[:,:3].sum(1), stems[:,:3].sum(1))

                if scaler:
                    scaler.scale(loss).backward()
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    loss.backward()
                    optimizer.step()

                epoch_loss += loss.item()
                progress_bar.set_postfix(loss=f"{loss.item():.4f}")

                del mix, stems, pred_stems
                gc.collect()
                torch.cuda.empty_cache()

            except RuntimeError as e:
                if 'CUDA out of memory' in str(e):
                    logger.warning("OOM - Saltando batch")
                    torch.cuda.empty_cache()
                    continue
                raise

        avg_loss = epoch_loss / len(train_loader)
        logger.info(f"Época {epoch+1} - Loss: {avg_loss:.4f}")

        if avg_loss < best_loss:
            best_loss = avg_loss
            save_checkpoint(model, optimizer, epoch+1, avg_loss, "models/fine_tuned/best_model.pth")
            logger.info("¡Nuevo mejor modelo guardado!")

        save_checkpoint(model, optimizer, epoch+1, avg_loss, f"models/fine_tuned/epoch_{epoch+1}.pth")

        if scheduler:
            scheduler.step()

if __name__ == "__main__":
    train()
