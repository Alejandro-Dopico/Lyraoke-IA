import torch
import torchaudio
import torch.nn.functional as F
from torchaudio.functional import lfilter

class AudioMetricsLoss(torch.nn.Module):
    def __init__(self, sample_rate=44100, device='cuda'):
        super().__init__()
        self.sample_rate = sample_rate
        self.device = device
        
        # Coeficientes para filtro de énfasis vocal (pre-énfasis)
        self.pre_emphasis = torch.tensor([1.0, -0.97], device=device)
        
    def si_snr_loss(self, pred, target):
        """Scale-Invariant Signal-to-Noise Ratio Loss (negativo para minimizar)"""
        eps = 1e-8
        pred_mean = pred.mean(dim=-1, keepdim=True)
        target_mean = target.mean(dim=-1, keepdim=True)
        
        pred_centered = pred - pred_mean
        target_centered = target - target_mean
        
        # Calcular coeficiente de escala
        scale = (pred_centered * target_centered).sum(dim=-1, keepdim=True) / \
                (target_centered ** 2).sum(dim=-1, keepdim=True).clamp(min=eps)
        
        # Calcular SI-SNR
        si_snr = 20 * torch.log10(eps + torch.norm(scale * target_centered, dim=-1) / 
                             torch.norm(scale * target_centered - pred_centered, dim=-1).clamp(min=eps))
        
        return -si_snr.mean()  # Negativo para minimizar

    def spectral_convergence(self, pred, target, n_fft=2048):
        """Pérdida de convergencia espectral"""
        # Asegurar que tengan forma (batch * stems, time)
        if pred.dim() > 2:
            pred = pred.reshape(-1, pred.shape[-1])
            target = target.reshape(-1, target.shape[-1])

        # Crear una ventana de Hann
        window = torch.hann_window(n_fft, device=pred.device)

        # Aplicar STFT con la ventana de Hann
        pred_spec = torch.stft(pred, n_fft=n_fft, return_complex=True, window=window)
        target_spec = torch.stft(target, n_fft=n_fft, return_complex=True, window=window)

        return torch.norm(target_spec - pred_spec, p='fro') / torch.norm(target_spec, p='fro').clamp(min=1e-8)

    def vocal_emphasis(self, audio):
        if audio.dim() == 2:
            audio = audio.unsqueeze(1)  # [batch, 1, time]

        b_coeffs = torch.tensor([1.0, -0.97], device=self.device)
        a_coeffs = torch.tensor([1.0, -0.97], device=self.device)  # Mismo tamaño que b_coeffs

        return torchaudio.functional.lfilter(audio, b_coeffs, a_coeffs)

    def forward(self, pred_stems, true_stems):
        """Pérdida compuesta para separación de stems"""
        
        # Asegúrate de que los tensores tengan gradientes habilitados
        pred_stems = pred_stems.requires_grad_()
        true_stems = true_stems.requires_grad_()

        # 1. Pérdida para instrumental (stems 0-2)
        inst_loss = 0.7 * self.si_snr_loss(pred_stems[:,:3], true_stems[:,:3]) + \
                   0.3 * self.spectral_convergence(pred_stems[:,:3], true_stems[:,:3])
        
        # 2. Pérdida para voces (stem 3) con pre-énfasis
        pred_vocals = self.vocal_emphasis(pred_stems[:,3])
        true_vocals = self.vocal_emphasis(true_stems[:,3])

        vocal_loss = self.si_snr_loss(pred_vocals, true_vocals)
        
        # 3. Pérdida cruzada para evitar "fugas" entre stems
        leakage_loss = torch.mean(torch.abs(pred_stems[:,:3] * pred_stems[:,3].unsqueeze(1)))
        
        return 0.6 * inst_loss + 0.3 * vocal_loss + 0.1 * leakage_loss
