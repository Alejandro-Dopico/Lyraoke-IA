import os
from pathlib import Path
from typing import Dict, Union
import json
from src.scripts.separate import separate_audio
from src.scripts.transcribe import LyricsTranscriber

class AudioProcessor:
    def __init__(self, model_size="medium"):
        self.transcriber = LyricsTranscriber(model_size=model_size)

    def process_audio(self, input_path: Union[str, Path], output_base_dir: str = "output") -> Dict:
        try:
            input_path = Path(input_path).resolve()
            
            # 1. Separación de stems
            stems_result = separate_audio(
                input_path=input_path,
                output_dir=Path(output_base_dir) / "stems"
            )

            # 2. Transcripción de letras
            vocals_path = Path(stems_result["vocals"])
            lyrics_dir = Path(output_base_dir) / "lyrics"
            lyrics_dir.mkdir(parents=True, exist_ok=True)
            
            # Procesar letras
            lyrics_result = self.transcriber.transcribe_audio(
                str(vocals_path),
                output_dir=lyrics_dir
            )
            
            # Rutas de los archivos de letras generados
            lyrics_files = {
                'raw_text': lyrics_dir / "vocals_lyrics.txt",
                'timed_json': lyrics_dir / "vocals_timed.json"
            }
            
            return {
                'original': str(input_path),
                'stems': stems_result,
                'lyrics': {
                    'text_path': str(lyrics_files['raw_text']),
                    'timed_path': str(lyrics_files['timed_json']),
                    'data': lyrics_result
                }
            }
        except Exception as e:
            print(f"Error en procesamiento: {str(e)}")
            raise