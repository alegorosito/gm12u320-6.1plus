#!/bin/bash

# Script standalone de espejo sin driver del kernel
# Desactiva el driver y usa solo copia de framebuffer

set -e

echo "Configurando espejo standalone..."

# Desactivar driver del kernel si está cargado
if lsmod | grep -q gm12u320; then
    echo "Desactivando driver del kernel..."
    sudo rmmod gm12u320
    sleep 2
fi

# Cargar driver sin workqueue
echo "Cargando driver sin workqueue..."
sudo insmod gm12u320.ko screen_mirror=false

# Esperar a que se cree el framebuffer
sleep 3

# Verificar framebuffers
if [ ! -r "/dev/fb0" ]; then
    echo "Error: No se puede leer /dev/fb0"
    exit 1
fi

if [ ! -w "/dev/fb1" ]; then
    echo "Error: No se puede escribir en /dev/fb1"
    exit 1
fi

echo "Framebuffers disponibles:"
echo "Fuente: /dev/fb0"
echo "Destino: /dev/fb1"

# Función de limpieza
cleanup() {
    echo "Deteniendo espejo..."
    kill $MIRROR_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Iniciando copia de framebuffer..."

# Bucle principal
while true; do
    # Copiar framebuffer con dd para mejor control
    dd if="/dev/fb0" of="/dev/fb1" bs=1M count=1 2>/dev/null || true
    sleep 0.1  # 10 FPS
done &

MIRROR_PID=$!

echo "Espejo iniciado con PID: $MIRROR_PID"
echo "Presiona Ctrl+C para detener"

wait $MIRROR_PID 