import os
from pathlib import Path
from src.scripts.separate import separate_audio
from src.scripts.transcribe import LyricsTranscriber
from core.file_manager import FileManager

class AudioProcessor:
    def __init__(self, model_size="medium"):
        self.transcriber = LyricsTranscriber(model_size=model_size)
    
    def process_audio(self, input_path, output_base_dir="output"):
        """
        Procesamiento completo:
        1. Gestiona archivos de entrada/salida
        2. Separa stems
        3. Transcribe letras
        """
        try:
            # 1. Separación de stems
            stems_result = separate_audio(input_path, os.path.join(output_base_dir, "stems"))
            if not stems_result:  # Esto no debería ocurrir ya que ahora lanza excepciones
                raise RuntimeError("Error en la separación de stems")
            
            # 2. Transcripción de letras
            lyrics_dir = os.path.join(output_base_dir, "lyrics")
            os.makedirs(lyrics_dir, exist_ok=True)
            
            lyrics_result = self.transcriber.transcribe_audio(
                stems_result["vocals"],
                output_dir=lyrics_dir
            )
            
            return {
                'original': input_path,
                'original_name': stems_result.get("original_name", Path(input_path).stem),
                'stems': stems_result,
                'lyrics': {
                    'text': lyrics_result['text'],
                    'timed_segments': lyrics_result['segments'],
                    'files': {
                        'txt': os.path.join(lyrics_dir, f"{Path(input_path).stem}_lyrics.txt"),
                        'json': os.path.join(lyrics_dir, f"{Path(input_path).stem}_timed.json"),
                        'srt': os.path.join(lyrics_dir, f"{Path(input_path).stem}.srt")
                    }
                }
            }
            
        except Exception as e:
            print(f"Error en el procesamiento de audio: {str(e)}")
            raise