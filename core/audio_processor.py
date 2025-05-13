import os
from pathlib import Path
from typing import Dict, Union
from src.scripts.separate import separate_audio
from src.scripts.transcribe import LyricsTranscriber
from src.utils.audio_utils import safe_audio_load, safe_audio_export  # Nueva importación

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

            # 2. Carga segura para transcripción
            from src.utils.audio_utils import safe_audio_load
            vocals_audio = safe_audio_load(stems_result["vocals"])
            
            # 3. Guardado temporal seguro si es necesario
            temp_vocals = Path(output_base_dir) / "temp_vocals.wav"
            safe_audio_export(vocals_audio, temp_vocals)
            
            # 4. Transcripción
            lyrics_result = self.transcriber.transcribe_audio(
                str(temp_vocals),
                output_dir=Path(output_base_dir) / "lyrics"
            )

            # Limpieza
            temp_vocals.unlink(missing_ok=True)
            
            return {
                'original': str(input_path),
                'stems': stems_result,
                'lyrics': lyrics_result
            }
        except Exception as e:
            print(f"Error en procesamiento: {str(e)}")
            raise