import os
from pathlib import Path
from src.scripts.separate import separate_audio
from src.scripts.transcribe import LyricsTranscriber
from core.file_manager import FileManager

class AudioProcessor:
    def __init__(self, model_size="medium"):
        self.transcriber = LyricsTranscriber(model_size=model_size)
        self.file_manager = FileManager()
    
    def process_audio(self, input_path, output_base_dir="output"):
        """
        Procesamiento completo con manejo correcto de rutas
        """
        try:
            # Normalizar la ruta de entrada
            input_path = str(Path(input_path).resolve())  # Convierte a ruta absoluta
            
            # Verificar existencia del archivo
            if not Path(input_path).exists():
                available_files = "\n".join(
                    f"- {f.name}" for f in Path("songs").iterdir() if f.is_file()
                )
                raise FileNotFoundError(
                    f"Archivo no encontrado: {input_path}\n"
                    f"Archivos disponibles en 'songs/':\n{available_files}"
                )

            # 1. Separación de stems
            stems_result = separate_audio(
                input_path=input_path,  # Cambiado a input_path
                output_dir=Path(output_base_dir) / "stems"
            )
            
            # 2. Transcripción de letras
            lyrics_dir = Path(output_base_dir) / "lyrics"
            lyrics_dir.mkdir(exist_ok=True)
            
            lyrics_result = self.transcriber.transcribe_audio(
                stems_result["vocals"],
                output_dir=lyrics_dir
            )
            
            return {
                'original': input_path,
                'original_name': Path(input_path).stem,
                'stems': stems_result,
                'lyrics': {
                    'text': lyrics_result['text'],
                    'timed_segments': lyrics_result['segments'],
                    'files': {
                        'txt': str(lyrics_dir / f"{Path(input_path).stem}_lyrics.txt"),
                        'json': str(lyrics_dir / f"{Path(input_path).stem}_timed.json"),
                        'srt': str(lyrics_dir / f"{Path(input_path).stem}.srt")
                    }
                }
            }
            
        except Exception as e:
            print(f"Error en el procesamiento de audio: {str(e)}")
            raise