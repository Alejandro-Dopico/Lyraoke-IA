import whisper
from whisper.utils import get_writer
import json
import os
from pathlib import Path
from core.file_manager import FileManager

class LyricsTranscriber:
    def __init__(self, model_size="medium"):
        """
        :param model_size: tiny, base, small, medium, large
        """
        self.model = whisper.load_model(model_size)
    
    def transcribe_audio(self, audio_path, output_dir=None, language=None):
        """
        Transcribe audio y guarda resultados en varios formatos
        """
        # Asegurar que el directorio de salida existe
        if output_dir:
            FileManager.prepare_output_dirs(os.path.dirname(output_dir))
        
        # Transcribir con Whisper
        result = self.model.transcribe(
            audio_path,
            language=language,
            word_timings=True
        )
        
        # Guardar resultados si se especifica output_dir
        if output_dir:
            self._save_results(result, audio_path, output_dir)
        
        return result
    
    def _save_results(self, result, audio_path, output_dir):
        """Guarda resultados en múltiples formatos"""
        base_name = Path(audio_path).stem
        
        # 1. Texto plano
        txt_path = os.path.join(output_dir, f"{base_name}_lyrics.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        
        # 2. JSON con temporizaciones
        json_path = os.path.join(output_dir, f"{base_name}_timed.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 3. Archivo SRT (subtítulos)
        srt_path = os.path.join(output_dir, f"{base_name}.srt")
        writer = get_writer("srt", output_dir)
        writer(result, audio_path)
        
        return {
            'txt': txt_path,
            'json': json_path,
            'srt': srt_path
        }