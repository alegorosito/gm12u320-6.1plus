#!/bin/bash

# Script para enviar imágenes estáticas o videos al proyector GM12U320
# Usa el framebuffer /dev/fb1 para enviar contenido

set -e

# Configuración
FBDEV="/dev/fb1"
TARGET_WIDTH=800
TARGET_HEIGHT=600
FPS=10

# Función de ayuda
show_help() {
    echo "Uso: $0 [OPCIÓN] [ARCHIVO]"
    echo ""
    echo "Opciones:"
    echo "  -i, --image ARCHIVO    Enviar imagen estática"
    echo "  -v, --video ARCHIVO    Enviar video"
    echo "  -p, --pattern TIPO     Generar patrón (gradient, solid, test)"
    echo "  -h, --help            Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 -i imagen.jpg"
    echo "  $0 -v video.mp4"
    echo "  $0 -p gradient"
    echo ""
}

# Verificar framebuffer
check_fb() {
    if [ ! -w "$FBDEV" ]; then
        echo "Error: No se puede escribir en $FBDEV"
        echo "Asegúrate de que el driver GM12U320 esté cargado"
        exit 1
    fi
}

# Enviar imagen estática
send_image() {
    local image_file="$1"
    echo "Enviando imagen: $image_file"
    
    # Convertir imagen a formato raw RGB24
    ffmpeg -i "$image_file" \
        -f rawvideo \
        -vcodec rawvideo \
        -pix_fmt rgb24 \
        -s "${TARGET_WIDTH}x${TARGET_HEIGHT}" \
        -y \
        - | \
    dd of="$FBDEV" bs=1M 2>/dev/null
    
    echo "Imagen enviada al proyector"
}

# Enviar video
send_video() {
    local video_file="$1"
    echo "Enviando video: $video_file"
    
    # Función de limpieza
    cleanup() {
        echo "Deteniendo video..."
        kill $FFMPEG_PID 2>/dev/null || true
        exit 0
    }
    trap cleanup SIGINT SIGTERM
    
    # Enviar video al framebuffer
    ffmpeg -i "$video_file" \
        -f rawvideo \
        -vcodec rawvideo \
        -pix_fmt rgb24 \
        -s "${TARGET_WIDTH}x${TARGET_HEIGHT}" \
        -r "$FPS" \
        -y \
        - | \
    dd of="$FBDEV" bs=1M 2>/dev/null &
    
    FFMPEG_PID=$!
    echo "Video iniciado con PID: $FFMPEG_PID"
    echo "Presiona Ctrl+C para detener"
    
    wait $FFMPEG_PID
}

# Generar patrón
generate_pattern() {
    local pattern_type="$1"
    echo "Generando patrón: $pattern_type"
    
    case "$pattern_type" in
        "gradient")
            # Patrón de gradiente
            python3 -c "
import numpy as np
import struct

width, height = $TARGET_WIDTH, $TARGET_HEIGHT
data = np.zeros((height, width, 3), dtype=np.uint8)

for y in range(height):
    for x in range(width):
        data[y, x, 0] = int((x * 255) / width)  # Red
        data[y, x, 1] = int((y * 255) / height) # Green
        data[y, x, 2] = 128                      # Blue

with open('$FBDEV', 'wb') as f:
    f.write(data.tobytes())
"
            ;;
        "solid")
            # Color sólido
            python3 -c "
import numpy as np

width, height = $TARGET_WIDTH, $TARGET_HEIGHT
data = np.full((height, width, 3), [255, 0, 0], dtype=np.uint8)  # Rojo

with open('$FBDEV', 'wb') as f:
    f.write(data.tobytes())
"
            ;;
        "test")
            # Patrón de prueba
            python3 -c "
import numpy as np

width, height = $TARGET_WIDTH, $TARGET_HEIGHT
data = np.zeros((height, width, 3), dtype=np.uint8)

# Crear patrón de barras
for y in range(height):
    for x in range(width):
        if x < width // 3:
            data[y, x] = [255, 0, 0]    # Rojo
        elif x < 2 * width // 3:
            data[y, x] = [0, 255, 0]    # Verde
        else:
            data[y, x] = [0, 0, 255]    # Azul

with open('$FBDEV', 'wb') as f:
    f.write(data.tobytes())
"
            ;;
        *)
            echo "Error: Patrón '$pattern_type' no reconocido"
            echo "Patrones disponibles: gradient, solid, test"
            exit 1
            ;;
    esac
    
    echo "Patrón enviado al proyector"
}

# Función principal
main() {
    check_fb
    
    case "$1" in
        -i|--image)
            if [ -z "$2" ]; then
                echo "Error: Debes especificar un archivo de imagen"
                exit 1
            fi
            send_image "$2"
            ;;
        -v|--video)
            if [ -z "$2" ]; then
                echo "Error: Debes especificar un archivo de video"
                exit 1
            fi
            send_video "$2"
            ;;
        -p|--pattern)
            if [ -z "$2" ]; then
                echo "Error: Debes especificar un tipo de patrón"
                exit 1
            fi
            generate_pattern "$2"
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Error: Opción no reconocida"
            show_help
            exit 1
            ;;
    esac
}

# Ejecutar función principal
main "$@" 