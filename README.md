#!/bin/bash

################################################################
# Lyraoke - Karaoke con IA en Tiempo Real 🎤🤖
# 
# Automatiza la instalación y ejecución del sistema Lyraoke
# GitHub: https://github.com/Alejandro-Dopico/Lyraoke-IA
################################################################

echo -e "\n\033[1;34m=== Lyraoke - Instalador y Ejecutor ===\033[0m"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo -e "\033[1;31m✖ Python 3 no está instalado\033[0m"
    echo "Instala Python 3.9+ primero y luego vuelve a ejecutar este script"
    exit 1
fi

# Clonar repositorio
echo -e "\n\033[1;32m✔ Clonando repositorio...\033[0m"
git clone https://github.com/Alejandro-Dopico/Lyraoke-IA.git
cd Lyraoke-IA || exit

# Instalar dependencias
echo -e "\n\033[1;32m✔ Instalando dependencias...\033[0m"
pip install -r requirements.txt

# Descargar modelos (se ejecuta automáticamente al correr)
echo -e "\n\033[1;32m✔ Los modelos se descargarán automáticamente al ejecutar\033[0m"

# Ejecutar Lyraoke
echo -e "\n\033[1;34m=== Ejecución ===\033[0m"
echo "Opciones:"
echo "1. Procesar archivo de audio"
echo "2. Modo tiempo real (experimental)"
echo "3. Salir"

read -rp "Seleccione una opción (1-3): " choice

case $choice in
    1)
        read -rp "Introduce la ruta del archivo de audio: " audio_file
        python lyraoke.py --input "$audio_file"
        ;;
    2)
        echo -e "\033[1;33m⚠ Modo experimental: Requiere GPU potente\033[0m"
        read -rp "Introduce la ruta del archivo de audio: " audio_file
        python lyraoke.py --input "$audio_file" --real-time
        ;;
    3)
        echo "Saliendo..."
        exit 0
        ;;
    *)
        echo "Opción no válida"
        exit 1
        ;;
esac

echo -e "\n\033[1;32m✔ Proceso completado!\033[0m"
echo "Resultados guardados en el directorio 'output'"
echo -e "\nVisita el repositorio para más información:"
echo -e "\033[1;34mhttps://github.com/Alejandro-Dopico/Lyraoke-IA\033[0m"