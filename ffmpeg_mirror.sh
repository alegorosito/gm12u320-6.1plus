#!/bin/bash

# Script de espejo de pantalla optimizado para Kernel 6.8
# Usa FFmpeg para capturar X11 y enviar al proyector GM12U320

set -e

# Configuración
RES=$(xrandr | grep '*' | awk '{print $1}' | head -1)
DSTXRES=800
DSTYRES=600
FBDEV="/dev/fb1"
FPS=10

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

echo "Iniciando espejo de pantalla..."
echo "Resolución fuente: $RES"
echo "Resolución destino: ${DSTXRES}x${DSTYRES}"
echo "FPS: $FPS"
echo "Framebuffer: $FBDEV"

# Función de limpieza
cleanup() {
    echo "Deteniendo espejo de pantalla..."
    kill $FFMPEG_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Comando FFmpeg optimizado para Kernel 6.8
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
    - | \
mplayer \
    -demuxer rawvideo \
    -rawvideo "w=${DSTXRES}:h=${DSTYRES}:format=bgr24" \
    -vo "fbdev:${FBDEV}" \
    -fps "$FPS" \
    -quiet \
    - &

FFMPEG_PID=$!

echo "FFmpeg iniciado con PID: $FFMPEG_PID"
echo "Presiona Ctrl+C para detener"

# Esperar a que termine
wait $FFMPEG_PID 