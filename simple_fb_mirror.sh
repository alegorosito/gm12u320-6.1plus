#!/bin/bash

# Script simple de espejo de framebuffer
# Usa cat para copiar de /dev/fb0 a /dev/fb1

set -e

# Configuración
SRC_FB="/dev/fb0"
DST_FB="/dev/fb1"
FPS=10
DELAY=$((1000000 / FPS))  # microsegundos

echo "Iniciando espejo simple de framebuffer..."
echo "Fuente: $SRC_FB"
echo "Destino: $DST_FB"
echo "FPS: $FPS"

# Verificar framebuffers
if [ ! -r "$SRC_FB" ]; then
    echo "Error: No se puede leer $SRC_FB"
    exit 1
fi

if [ ! -w "$DST_FB" ]; then
    echo "Error: No se puede escribir en $DST_FB"
    exit 1
fi

# Función de limpieza
cleanup() {
    echo "Deteniendo espejo..."
    kill $MIRROR_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Iniciando copia..."

# Bucle principal usando cat
while true; do
    cat "$SRC_FB" > "$DST_FB" 2>/dev/null || true
    usleep "$DELAY"
done &

MIRROR_PID=$!

echo "Espejo iniciado con PID: $MIRROR_PID"
echo "Presiona Ctrl+C para detener"

wait $MIRROR_PID 