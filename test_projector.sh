#!/bin/bash

# Script de prueba del proyector sin dependencias de X11
# Usa el driver modificado para generar patrones

set -e

echo "Probando proyector GM12U320..."

# Verificar que el driver esté cargado
if ! lsmod | grep -q gm12u320; then
    echo "Cargando driver GM12U320..."
    sudo insmod gm12u320.ko screen_mirror=true
    sleep 2
fi

# Verificar framebuffer
if [ ! -w "/dev/fb1" ]; then
    echo "Error: No se puede escribir en /dev/fb1"
    echo "Verificando logs del driver..."
    dmesg | grep -i gm12u320 | tail -5
    exit 1
fi

echo "Driver cargado correctamente"
echo "Framebuffer /dev/fb1 disponible"

# Verificar logs del driver
echo "Logs del driver:"
dmesg | grep -i gm12u320 | tail -5

# Verificar workqueue
echo "Procesos del driver:"
ps aux | grep -i gm12u320 | grep -v grep

echo ""
echo "El driver debería estar generando un patrón de gradiente."
echo "Si ves el patrón en el proyector, el sistema funciona correctamente."
echo ""
echo "Para ver logs en tiempo real:"
echo "sudo dmesg -w | grep gm12u320" 