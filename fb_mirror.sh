#!/bin/bash

# Script de espejo de framebuffer sin X11 (Kernel 6.8)
# Copia directamente de /dev/fb0 a /dev/fb1

set -e

# Configuración
SRC_FB="/dev/fb0"
DST_FB="/dev/fb1"
FPS=10
FRAME_DELAY=$((1000000 / FPS))  # en microsegundos

# Verificar que los framebuffers estén disponibles
if [ ! -r "$SRC_FB" ]; then
    echo "Error: No se puede leer $SRC_FB"
    exit 1
fi

if [ ! -w "$DST_FB" ]; then
    echo "Error: No se puede escribir en $DST_FB"
    echo "Asegúrate de que el driver GM12U320 esté cargado"
    exit 1
fi

# Obtener información del framebuffer fuente
SRC_INFO=$(fbset -fb "$SRC_FB" 2>/dev/null | grep geometry | awk '{print $2, $3, $6}')
if [ -z "$SRC_INFO" ]; then
    echo "Error: No se puede obtener información de $SRC_FB"
    exit 1
fi

SRC_WIDTH=$(echo $SRC_INFO | awk '{print $1}')
SRC_HEIGHT=$(echo $SRC_INFO | awk '{print $2}')
SRC_BPP=$(echo $SRC_INFO | awk '{print $3}')

echo "Iniciando espejo de framebuffer..."
echo "Fuente: $SRC_FB (${SRC_WIDTH}x${SRC_HEIGHT}, ${SRC_BPP}bpp)"
echo "Destino: $DST_FB"
echo "FPS: $FPS (${FRAME_DELAY}μs por frame)"

# Función de limpieza
cleanup() {
    echo "Deteniendo espejo de framebuffer..."
    kill $MIRROR_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Función para copiar framebuffer con escalado simple
copy_framebuffer() {
    local src="$1"
    local dst="$2"
    local src_width="$3"
    local src_height="$4"
    local src_bpp="$5"
    
    # Calcular tamaños
    local src_bytes_per_pixel=$((src_bpp / 8))
    local src_line_size=$((src_width * src_bytes_per_pixel))
    local src_total_size=$((src_height * src_line_size))
    
    # Para el destino, usar 800x600x3 (RGB24)
    local dst_width=800
    local dst_height=600
    local dst_bytes_per_pixel=3
    local dst_line_size=$((dst_width * dst_bytes_per_pixel))
    local dst_total_size=$((dst_height * dst_line_size))
    
    # Crear buffer temporal
    local temp_file=$(mktemp)
    
    # Leer framebuffer fuente
    dd if="$src" of="$temp_file" bs=1M count=1 2>/dev/null
    
    # Escalar y convertir (simplificado)
    # Por ahora, solo copiamos los primeros bytes
    dd if="$temp_file" of="$dst" bs="$dst_total_size" count=1 2>/dev/null
    
    # Limpiar
    rm -f "$temp_file"
}

echo "Iniciando copia de framebuffer..."

# Bucle principal
while true; do
    copy_framebuffer "$SRC_FB" "$DST_FB" "$SRC_WIDTH" "$SRC_HEIGHT" "$SRC_BPP"
    usleep "$FRAME_DELAY"
done &

MIRROR_PID=$!

echo "Espejo iniciado con PID: $MIRROR_PID"
echo "Presiona Ctrl+C para detener"

# Esperar a que termine
wait $MIRROR_PID 