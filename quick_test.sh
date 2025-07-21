#!/bin/bash

# Script de prueba rápida del proyector
# Genera contenido sin archivos externos

set -e

echo "Prueba rápida del proyector GM12U320..."

# Verificar framebuffer
if [ ! -w "/dev/fb1" ]; then
    echo "Error: No se puede escribir en /dev/fb1"
    exit 1
fi

# Función para generar color sólido
generate_solid_color() {
    local r=$1
    local g=$2
    local b=$3
    local name="$4"
    
    echo "Generando color $name (R:$r G:$g B:$b)..."
    
    python3 -c "
import numpy as np

width, height = 800, 600
data = np.full((height, width, 3), [$r, $g, $b], dtype=np.uint8)

with open('/dev/fb1', 'wb') as f:
    f.write(data.tobytes())
"
    
    echo "Color $name enviado al proyector"
    sleep 2
}

# Función para generar patrón animado
generate_animation() {
    echo "Generando animación de colores..."
    
    for i in {0..10}; do
        r=$((i * 25))
        g=$(((10-i) * 25))
        b=$((i * 20))
        
        python3 -c "
import numpy as np

width, height = 800, 600
data = np.full((height, width, 3), [$r, $g, $b], dtype=np.uint8)

with open('/dev/fb1', 'wb') as f:
    f.write(data.tobytes())
"
        
        echo "Frame $i/10 enviado"
        sleep 0.5
    done
}

# Función de limpieza
cleanup() {
    echo "Deteniendo prueba..."
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Iniciando secuencia de prueba..."

# Secuencia de colores
generate_solid_color 255 0 0 "ROJO"
generate_solid_color 0 255 0 "VERDE"
generate_solid_color 0 0 255 "AZUL"
generate_solid_color 255 255 0 "AMARILLO"
generate_solid_color 255 0 255 "MAGENTA"
generate_solid_color 0 255 255 "CYAN"
generate_solid_color 255 255 255 "BLANCO"
generate_solid_color 0 0 0 "NEGRO"

echo "Generando animación..."
generate_animation

echo "Prueba completada."
echo "Si viste los colores en el proyector, el sistema funciona correctamente." 