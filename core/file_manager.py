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
        """Guarda un archivo subido manteniendo su nombre original y limpia el directorio primero"""
        os.makedirs(target_dir, exist_ok=True)
        FileManager.clear_directory(target_dir)

        # Mantener el nombre original del archivo
        original_filename = Path(file_path).name
        target_path = os.path.join(target_dir, original_filename)

        shutil.copy(file_path, target_path)
        return target_path
