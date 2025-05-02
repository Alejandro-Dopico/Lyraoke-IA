import torch
import torchaudio
from pathlib import Path
import random
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

class KaraokeDataset:
    def __init__(self, root_dir, chunk_size=44100*10, sample_rate=44100):
        self.root_dir = Path(root_dir)
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.audio_files = self._find_audio_files()
        self.cache = {}
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def _find_audio_files(self):
        files = []
        for track_dir in self.root_dir.iterdir():
            if track_dir.is_dir():
                required_files = {'mixture.wav', 'vocals.wav', 'drums.wav', 'bass.wav', 'other.wav'}
                if all((track_dir / f).exists() for f in required_files):
                    files.append(track_dir)
        return files

    def _load_audio(self, path):
        try:
            audio, sr = torchaudio.load(path, normalize=True)
            if sr != self.sample_rate:
                audio = torchaudio.functional.resample(audio, sr, self.sample_rate)
            return audio
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return None

    def __len__(self):
        return len(self.audio_files)

    def __getitem__(self, idx):
        track_dir = self.audio_files[idx]
        
        # Cargar todos los stems en paralelo
        futures = {}
        for stem in ['mixture', 'vocals', 'drums', 'bass', 'other']:
            path = track_dir / f"{stem}.wav"
            futures[stem] = self.executor.submit(self._load_audio, path)
        
        stems = {}
        for stem, future in futures.items():
            audio = future.result()
            if audio is None:
                return self._get_dummy_item()
            stems[stem] = audio

        # Selección aleatoria del chunk
        total_frames = stems['mixture'].shape[1]
        start = random.randint(0, max(0, total_frames - self.chunk_size))
        
        return {
            'mix': stems['mixture'][:, start:start+self.chunk_size],
            'stems': torch.stack([
                stems['drums'][:, start:start+self.chunk_size],
                stems['bass'][:, start:start+self.chunk_size],
                stems['other'][:, start:start+self.chunk_size],
                stems['vocals'][:, start:start+self.chunk_size]
            ])
        }
    
    def _get_dummy_item(self):
        dummy = torch.zeros(2, self.chunk_size)
        return {
            'mix': dummy,
            'stems': torch.stack([dummy]*4)
        }

def get_dataloader(root_dir, batch_size=1, num_workers=4):
    dataset = KaraokeDataset(root_dir)
    return torch.utils.data.DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=min(4, num_workers),
        pin_memory=True,
        persistent_workers=True,
        prefetch_factor=2
    )