#!/bin/bash

# Script para crear un framebuffer virtual para el proyector
# Esto simula el /dev/fb1 que debería crear el driver

set -e

# Configuración
FB_DEVICE="/dev/fb1"
FB_WIDTH=800
FB_HEIGHT=600
FB_BPP=24
FB_SIZE=$((FB_WIDTH * FB_HEIGHT * FB_BPP / 8))

echo "Creando framebuffer virtual para proyector..."
echo "Resolución: ${FB_WIDTH}x${FB_HEIGHT} @ ${FB_BPP}bpp"
echo "Tamaño: ${FB_SIZE} bytes"

# Crear dispositivo de framebuffer virtual
if [ ! -e "$FB_DEVICE" ]; then
    echo "Creando dispositivo $FB_DEVICE..."
    
    # Crear archivo de datos
    sudo dd if=/dev/zero of=/tmp/fb1_data bs=1 count=$FB_SIZE 2>/dev/null
    
    # Crear dispositivo de bloque
    sudo mknod $FB_DEVICE c 29 1 2>/dev/null || true
    
    # Establecer permisos
    sudo chmod 666 $FB_DEVICE
    sudo chown root:video $FB_DEVICE
    
    echo "Framebuffer virtual creado: $FB_DEVICE"
else
    echo "Framebuffer ya existe: $FB_DEVICE"
fi

# Verificar que existe
if [ -e "$FB_DEVICE" ]; then
    echo "✅ Framebuffer virtual listo: $FB_DEVICE"
    ls -la $FB_DEVICE
else
    echo "❌ Error: No se pudo crear el framebuffer virtual"
    exit 1
fi

echo ""
echo "Ahora puedes ejecutar:"
echo "  sudo ./fbmirror/fbmirror"
echo ""
echo "O usar el script de prueba:"
echo "  ./test_projector.sh" 