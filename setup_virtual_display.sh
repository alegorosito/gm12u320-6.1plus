#!/bin/bash

# Script para configurar pantalla virtual con xrandr
# Esto permite enviar contenido al proyector sin bloquear la GUI principal

set -e

echo "Configurando pantalla virtual para GM12U320..."

# Verificar que X11 esté disponible
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0.0
fi

# Configuración de la pantalla virtual
VIRTUAL_WIDTH=800
VIRTUAL_HEIGHT=600
VIRTUAL_NAME="VIRTUAL1"

echo "Creando pantalla virtual ${VIRTUAL_WIDTH}x${VIRTUAL_HEIGHT}..."

# Crear modo virtual
xrandr --newmode "${VIRTUAL_WIDTH}x${VIRTUAL_HEIGHT}" \
    $(cvt ${VIRTUAL_WIDTH} ${VIRTUAL_HEIGHT} 60 | grep Modeline | cut -d' ' -f3-)

# Agregar modo a la pantalla virtual
xrandr --addmode ${VIRTUAL_NAME} "${VIRTUAL_WIDTH}x${VIRTUAL_HEIGHT}"

# Activar pantalla virtual
xrandr --output ${VIRTUAL_NAME} --mode "${VIRTUAL_WIDTH}x${VIRTUAL_HEIGHT}" --right-of eDP-1

echo "Pantalla virtual configurada."
echo "Ahora puedes mover ventanas a la pantalla virtual para proyectarlas."

# Mostrar configuración actual
echo "Configuración actual:"
xrandr | grep -A 5 ${VIRTUAL_NAME}

echo ""
echo "Para usar la pantalla virtual:"
echo "1. Mueve ventanas a la pantalla virtual"
echo "2. El driver GM12U320 capturará automáticamente"
echo "3. El contenido se proyectará sin bloquear la GUI principal" 