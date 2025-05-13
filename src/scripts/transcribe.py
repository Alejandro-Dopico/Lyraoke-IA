import whisper
from whisper.utils import get_writer
import json
import os
from pathlib import Path
from typing import Dict, Optional, Union
from core.file_manager import FileManager

class LyricsTranscriber:
    def __init__(self, model_size: str = "medium"):
        """
        :param model_size: tiny, base, small, medium, large
        """
        self.model = whisper.load_model(model_size)
    
    def transcribe_audio(
        self,
        audio_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        language: Optional[str] = None
    ) -> Dict:
        """
        Transcribe audio y guarda resultados en varios formatos
        
        Args:
            audio_path: Ruta al archivo de audio
            output_dir: Directorio para guardar resultados (opcional)
            language: Idioma para transcripción (opcional)
            
        Returns:
            Dict con resultados de la transcripción y rutas de archivos
        """
        # Convertir a Path y asegurar directorios
        audio_path = Path(audio_path)
        if output_dir:
            output_dir = Path(output_dir)
            FileManager.prepare_output_dirs(output_dir)
        
        # Transcribir con Whisper (API actualizada)
        result = self.model.transcribe(
            str(audio_path),  # Asegurar string para Whisper
            language=language,
            verbose=None,
            word_timestamps=True  # Parámetro actualizado
        )
        
        # Procesar resultados para mantener compatibilidad
        processed_result = {
            'text': result['text'],
            'segments': self._process_segments(result.get('segments', []))
        }
        
        # Guardar resultados si se especifica output_dir
        output_files = {}
        if output_dir:
            output_files = self._save_results(processed_result, audio_path, output_dir)
            processed_result.update({'files': output_files})
        
        return processed_result
    
    def _process_segments(self, segments: list) -> list:
        """Procesa segmentos para mantener estructura consistente"""
        processed = []
        for segment in segments:
            processed_segment = {
                'start': segment['start'],
                'end': segment['end'],
                'text': segment['text'],
                'words': segment.get('words', [])
            }
            processed.append(processed_segment)
        return processed
    
    def _save_results(
        self,
        result: Dict,
        audio_path: Path,
        output_dir: Path
    ) -> Dict[str, str]:
        """Guarda resultados en múltiples formatos"""
        base_name = audio_path.stem
        
        # 1. Texto plano
        txt_path = output_dir / f"{base_name}_lyrics.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        
        # 2. JSON con temporizaciones
        json_path = output_dir / f"{base_name}_timed.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result['segments'], f, ensure_ascii=False, indent=2)
        
        # 3. Archivo SRT (subtítulos)
        srt_path = output_dir / f"{base_name}.srt"
        writer = get_writer("srt", str(output_dir))  # Whisper espera string
        writer(result, str(audio_path))  # Asegurar string para Whisper
        
        return {
            'txt': str(txt_path),
            'json': str(json_path),
            'srt': str(srt_path)
        }