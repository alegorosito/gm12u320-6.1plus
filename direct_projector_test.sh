#!/bin/bash

# Script para probar el proyector directamente via USB
# Bypass completo del sistema de framebuffers

set -e

# Configuración USB
USB_VID="1de1"
USB_PID="c102"

echo "🔍 Buscando proyector GM12U320..."

# Buscar dispositivo USB
USB_DEVICE=$(lsusb -d ${USB_VID}:${USB_PID} | awk '{print $2 ":" $4}' | sed 's/://')

if [ -z "$USB_DEVICE" ]; then
    echo "❌ Error: No se encontró el proyector GM12U320"
    echo "Dispositivos USB disponibles:"
    lsusb
    exit 1
fi

echo "✅ Proyector encontrado: $USB_DEVICE"

# Buscar dispositivo en /dev
USB_DEV_PATH=""
for dev in /dev/usb* /dev/bus/usb/*/*; do
    if [ -e "$dev" ]; then
        echo "Verificando: $dev"
        # Aquí podríamos verificar si es nuestro dispositivo
    fi
done

echo ""
echo "📊 Información del dispositivo:"
lsusb -d ${USB_VID}:${USB_PID} -v | head -20

echo ""
echo "🔧 Intentando comunicación directa..."

# Crear un patrón de prueba simple
echo "Generando patrón de prueba..."

# Usar Python para generar datos de prueba
python3 -c "
import numpy as np
import time

print('Generando patrón de prueba RGB...')

# Crear patrón de barras de colores 800x600
width, height = 800, 600
data = np.zeros((height, width, 3), dtype=np.uint8)

# Patrón de barras verticales
bar_width = width // 8
colors = [
    [255, 0, 0],    # Rojo
    [0, 255, 0],    # Verde
    [0, 0, 255],    # Azul
    [255, 255, 0],  # Amarillo
    [255, 0, 255],  # Magenta
    [0, 255, 255],  # Cyan
    [255, 255, 255], # Blanco
    [0, 0, 0]       # Negro
]

for i, color in enumerate(colors):
    start_x = i * bar_width
    end_x = min((i + 1) * bar_width, width)
    data[:, start_x:end_x] = color

# Guardar como archivo raw
data.tofile('test_pattern.raw')
print(f'Patrón guardado: test_pattern.raw ({data.nbytes} bytes)')
print(f'Resolución: {width}x{height} @ 24bpp')
"

echo ""
echo "📁 Archivos generados:"
ls -la test_pattern.raw 2>/dev/null || echo "No se pudo generar el archivo"

echo ""
echo "🎯 Próximos pasos:"
echo "1. El proyector está conectado y detectado"
echo "2. Se generó un patrón de prueba"
echo "3. Necesitamos implementar la comunicación USB directa"
echo ""
echo "💡 Sugerencia: Usar libusb para comunicación directa" 