import os
import shutil
from pathlib import Path
import glob

class FileManager:
    @staticmethod
    def clear_directory(directory):
        """Elimina todos los archivos en un directorio"""
        for filename in glob.glob(os.path.join(directory, '*')):
            try:
                if os.path.isfile(filename):
                    os.unlink(filename)
                elif os.path.isdir(filename):
                    shutil.rmtree(filename)
            except Exception as e:
                print(f"Error deleting {filename}: {e}")

    @staticmethod
    def save_uploaded_file(file_path, target_dir="songs"):
        """Guarda un archivo subido y limpia el directorio primero"""
        os.makedirs(target_dir, exist_ok=True)
        FileManager.clear_directory(target_dir)
        
        # Generar nombre único para evitar colisiones
        ext = Path(file_path).suffix
        new_filename = f"uploaded_song{ext}"
        target_path = os.path.join(target_dir, new_filename)
        
        shutil.copy(file_path, target_path)
        return target_path

    @staticmethod
    def prepare_output_dirs(base_dir="output"):
        """Crea la estructura de directorios de salida"""
        dirs = {
            'stems': os.path.join(base_dir, 'stems'),
            'lyrics': os.path.join(base_dir, 'lyrics')
        }
        
        for dir_path in dirs.values():
            os.makedirs(dir_path, exist_ok=True)
            FileManager.clear_directory(dir_path)
        
        return dirs