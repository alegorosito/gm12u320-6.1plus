#!/bin/bash

# Script de espejo directo al framebuffer (Kernel 6.8)
# Escribe directamente sin usar mplayer/ffplay

set -e

# Configuración
RES=$(xrandr | grep '*' | awk '{print $1}' | head -1)
DSTXRES=800
DSTYRES=600
FBDEV="/dev/fb1"
FPS=10
FRAME_DELAY=$((1000 / FPS))  # en milisegundos

# Verificar que el proyector esté disponible
if [ ! -w "$FBDEV" ]; then
    echo "Error: No se puede escribir en $FBDEV"
    echo "Asegúrate de que el driver GM12U320 esté cargado"
    exit 1
fi

# Verificar que X11 esté disponible
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0.0
fi

echo "Iniciando espejo directo al framebuffer..."
echo "Resolución fuente: $RES"
echo "Resolución destino: ${DSTXRES}x${DSTYRES}"
echo "FPS: $FPS (${FRAME_DELAY}ms por frame)"
echo "Framebuffer: $FBDEV"

# Función de limpieza
cleanup() {
    echo "Deteniendo espejo de pantalla..."
    kill $FFMPEG_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Crear pipe temporal
PIPE=$(mktemp -u)
mkfifo "$PIPE"

# FFmpeg que escribe directamente al framebuffer
ffmpeg \
    -f x11grab \
    -s "$RES" \
    -r "$FPS" \
    -i "$DISPLAY" \
    -f rawvideo \
    -vcodec rawvideo \
    -pix_fmt bgr24 \
    -s "${DSTXRES}x${DSTYRES}" \
    -vf "scale=${DSTXRES}:${DSTYRES}:flags=fast_bilinear" \
    -y \
    "$PIPE" &

FFMPEG_PID=$!

echo "FFmpeg iniciado con PID: $FFMPEG_PID"

# Leer del pipe y escribir al framebuffer
while true; do
    if [ -p "$PIPE" ]; then
        # Leer frame y escribir al framebuffer
        dd if="$PIPE" of="$FBDEV" bs=1M count=1 2>/dev/null || break
        usleep $((FRAME_DELAY * 1000))  # Convertir a microsegundos
    else
        break
    fi
done &

DD_PID=$!

echo "Escritura al framebuffer iniciada con PID: $DD_PID"
echo "Presiona Ctrl+C para detener"

# Esperar a que termine
wait $FFMPEG_PID

# Limpiar
rm -f "$PIPE" 