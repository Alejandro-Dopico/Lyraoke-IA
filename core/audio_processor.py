import os
from pathlib import Path
from typing import Dict, Union
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

            # 2. Transcripción directa del archivo vocals.wav generado
            vocals_path = Path(stems_result["vocals"])
            lyrics_result = self.transcriber.transcribe_audio(
                str(vocals_path),
                output_dir=Path(output_base_dir) / "lyrics"
            )
            
            return {
                'original': str(input_path),
                'stems': stems_result,
                'lyrics': lyrics_result
            }
        except Exception as e:
            print(f"Error en procesamiento: {str(e)}")
            raise