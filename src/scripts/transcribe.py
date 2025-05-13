import whisper
from whisper.utils import get_writer
import json
import os
from pathlib import Path
from typing import Dict, Optional, Union
import tempfile
from src.utils.audio_utils import load_audio_secure, export_audio_secure  # Nuevas importaciones

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
        Transcribe audio de forma segura y guarda resultados
        
        Args:
            audio_path: Ruta al archivo de audio
            output_dir: Directorio para guardar resultados
            language: Idioma para transcripción
            
        Returns:
            Dict con resultados y rutas de archivos
        """
        audio_path = Path(audio_path)
        temp_file = None
        
        try:
            # 1. Carga segura del audio
            audio = load_audio_secure(audio_path)
            
            # 2. Crear archivo temporal seguro para Whisper
            temp_file = f"{tempfile.gettempdir()}/whisper_input_{os.getpid()}.wav"
            export_audio_secure(audio, temp_file)
            
            # 3. Transcripción
            result = self._safe_whisper_transcribe(temp_file, language)
            
            # 4. Procesamiento de resultados
            processed_result = {
                'text': result['text'],
                'segments': self._process_segments(result.get('segments', []))
            }
            
            # 5. Guardar resultados si hay output_dir
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                processed_result['files'] = self._save_results(
                    processed_result, 
                    audio_path, 
                    output_dir
                )
            
            return processed_result
            
        finally:
            # Limpieza segura del temporal
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    def _safe_whisper_transcribe(self, audio_path: str, language: str) -> Dict:
        """Wrapper seguro para la transcripción de Whisper"""
        return self.model.transcribe(
            audio_path,
            language=language,
            verbose=None,
            word_timestamps=True
        )
    
    def _process_segments(self, segments: list) -> list:
        """Procesa segmentos para mantener estructura consistente"""
        return [{
            'start': s['start'],
            'end': s['end'],
            'text': s['text'],
            'words': s.get('words', [])
        } for s in segments]
    
    def _save_results(
        self,
        result: Dict,
        original_path: Path,
        output_dir: Path
    ) -> Dict[str, str]:
        """Guarda resultados en múltiples formatos de forma segura"""
        base_name = original_path.stem
        output_files = {}
        
        # 1. Texto plano
        txt_path = output_dir / f"{base_name}_lyrics.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(result['text'])
        output_files['txt'] = str(txt_path)
        
        # 2. JSON con temporizaciones
        json_path = output_dir / f"{base_name}_timed.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result['segments'], f, ensure_ascii=False, indent=2)
        output_files['json'] = str(json_path)
        
        # 3. Archivo SRT (subtítulos)
        srt_path = output_dir / f"{base_name}.srt"
        try:
            writer = get_writer("srt", str(output_dir))
            writer(result, str(original_path))
            output_files['srt'] = str(srt_path)
        except Exception as e:
            print(f"Warning: Error generando SRT: {str(e)}")
        
        return output_files