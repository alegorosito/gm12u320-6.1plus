#!/bin/bash

# Script que usa el driver del kernel para espejo
# El driver ya está capturando la pantalla, solo necesitamos verificar

set -e

echo "Verificando estado del driver GM12U320..."

# Verificar que el driver esté cargado
if ! lsmod | grep -q gm12u320; then
    echo "Error: Driver GM12U320 no está cargado"
    echo "Cargando driver..."
    sudo insmod gm12u320.ko screen_mirror=true
fi

# Verificar framebuffers
if [ ! -e "/dev/fb1" ]; then
    echo "Error: /dev/fb1 no existe"
    exit 1
fi

echo "Driver GM12U320 cargado correctamente"
echo "Framebuffer /dev/fb1 disponible"

# Verificar logs del driver
echo "Logs del driver:"
dmesg | grep -i gm12u320 | tail -10

# Verificar workqueue
echo "Procesos del driver:"
ps aux | grep -i gm12u320

# Verificar que está capturando
echo "Verificando captura de pantalla..."
dmesg | grep "Captured main screen" | tail -3

echo ""
echo "El driver debería estar proyectando automáticamente."
echo "Si no ves la pantalla en el proyector, verifica:"
echo "1. Que el proyector esté conectado"
echo "2. Que el proyector esté encendido"
echo "3. Que la entrada USB esté seleccionada"
echo ""
echo "Para ver logs en tiempo real:"
echo "sudo dmesg -w | grep gm12u320" 