import torch
import torchaudio
from torch.utils.data import Dataset, DataLoader
import random
import os
from pathlib import Path
import numpy as np

class InstrumentalDataset(Dataset):
    def __init__(self, root_dir, segment_samples=264600, augment=True):
        self.segment_samples = segment_samples
        self.augment = augment
        
        # Cargar lista de archivos
        self.file_paths = []
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(('.wav', '.mp3')):
                    self.file_paths.append(os.path.join(root, file))
        
        if not self.file_paths:
            raise ValueError(f"No se encontraron archivos de audio en {root_dir}")

    def __len__(self):
        return len(self.file_paths)

    def _load_audio(self, path):
        waveform, sr = torchaudio.load(path)
        if waveform.shape[0] == 1:  # Mono a stereo
            waveform = torch.cat([waveform, waveform], dim=0)
        if sr != 44100:
            waveform = torchaudio.functional.resample(waveform, sr, 44100)
        return waveform

    def __getitem__(self, idx):
        try:
            waveform = self._load_audio(self.file_paths[idx])
            total_samples = waveform.shape[1]
            
            # Seleccionar segmento aleatorio
            if total_samples > self.segment_samples:
                start = random.randint(0, total_samples - self.segment_samples)
                waveform = waveform[:, start:start+self.segment_samples]
            else:
                # Padding si es necesario
                padsize = self.segment_samples - total_samples
                waveform = torch.nn.functional.pad(waveform, (0, padsize))
            
            # Simular stems (en tu implementación real carga los stems reales)
            stems = torch.stack([
                waveform * 0.3,  # bass
                waveform * 0.2,  # drums
                waveform * 0.4,  # other
                waveform * 0.1   # vocals
            ])
            
            if self.augment:
                stems = self._augment_audio(stems)
            
            return {
                'mix': stems.sum(dim=0),
                'stems': stems
            }
            
        except Exception as e:
            print(f"Error cargando {self.file_paths[idx]}: {str(e)}")
            # Devolver datos dummy
            dummy_wave = torch.randn(2, self.segment_samples) * 0.01
            stems = torch.stack([dummy_wave * 0.3, dummy_wave * 0.2, 
                               dummy_wave * 0.4, dummy_wave * 0.1])
            return {
                'mix': stems.sum(dim=0),
                'stems': stems
            }

    def _augment_audio(self, stems):
        """Aumentaciones básicas sin dependencia de torchaudio.filters"""
        # 1. Modificación de ganancia
        if random.random() > 0.5:
            gain = random.uniform(0.8, 1.2)
            stems[:3] *= gain  # Solo instrumental
            
        # 2. Cambio de tono simple
        if random.random() > 0.5:
            shift = random.choice([-1, 0, 1])
            stems = torch.roll(stems, shifts=shift, dims=-1)
            
        return stems

def get_dataloader(data_dir, batch_size=4, segment_samples=264600, num_workers=2):
    """Crea el DataLoader con segmentos de tamaño fijo"""
    dataset = InstrumentalDataset(data_dir, segment_samples=segment_samples)
    
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=min(num_workers, os.cpu_count() - 1),
        pin_memory=torch.cuda.is_available(),
        drop_last=True,
        persistent_workers=num_workers > 0
    )