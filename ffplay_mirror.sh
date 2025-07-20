#!/bin/bash

# Script de espejo de pantalla usando FFplay (Kernel 6.8)
# Alternativa más compatible que mplayer

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

echo "Iniciando espejo de pantalla con FFplay..."
echo "Resolución fuente: $RES"
echo "Resolución destino: ${DSTXRES}x${DSTYRES}"
echo "FPS: $FPS"
echo "Framebuffer: $FBDEV"

# Función de limpieza
cleanup() {
    echo "Deteniendo espejo de pantalla..."
    kill $FFPLAY_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Comando FFplay optimizado para Kernel 6.8
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
ffplay \
    -f rawvideo \
    -pix_fmt bgr24 \
    -s "${DSTXRES}x${DSTYRES}" \
    -fps "$FPS" \
    -v quiet \
    -window_title "GM12U320 Mirror" \
    - &

FFPLAY_PID=$!

echo "FFplay iniciado con PID: $FFPLAY_PID"
echo "Presiona Ctrl+C para detener"

# Esperar a que termine
wait $FFPLAY_PID 