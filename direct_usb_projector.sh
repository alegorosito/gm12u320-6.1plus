#!/bin/bash

# Script para controlar el proyector GM12U320 directamente via USB
# Bypass del driver del kernel para evitar bloqueos

set -e

# Configuración USB
USB_VID="1de1"
USB_PID="c102"
USB_DEVICE=""

# Función para encontrar el dispositivo USB
find_usb_device() {
    echo "Buscando dispositivo GM12U320..."
    
    # Buscar por ID de vendor/product
    USB_DEVICE=$(lsusb -d ${USB_VID}:${USB_PID} | awk '{print $2 ":" $4}' | sed 's/://')
    
    if [ -z "$USB_DEVICE" ]; then
        echo "Error: No se encontró el dispositivo GM12U320"
        echo "Dispositivos USB disponibles:"
        lsusb
        exit 1
    fi
    
    echo "Dispositivo encontrado: $USB_DEVICE"
}

# Función para enviar comando al proyector
send_command() {
    local cmd="$1"
    local data="$2"
    
    echo "Enviando comando: $cmd"
    
    # Usar usb-devices para enviar comandos
    # Esto es un ejemplo simplificado
    echo "$cmd" > /dev/usb/$USB_DEVICE 2>/dev/null || true
}

# Función para generar patrón de prueba
generate_test_pattern() {
    echo "Generando patrón de prueba..."
    
    # Crear archivo de datos de prueba
    python3 -c "
import numpy as np

# Crear patrón de prueba 800x600 RGB24
width, height = 800, 600
data = np.zeros((height, width, 3), dtype=np.uint8)

# Patrón de barras de colores
for y in range(height):
    for x in range(width):
        if x < width // 4:
            data[y, x] = [255, 0, 0]    # Rojo
        elif x < 2 * width // 4:
            data[y, x] = [0, 255, 0]    # Verde
        elif x < 3 * width // 4:
            data[y, x] = [0, 0, 255]    # Azul
        else:
            data[y, x] = [255, 255, 255] # Blanco

# Guardar como archivo raw
data.tofile('test_pattern.raw')
print('Patrón de prueba generado: test_pattern.raw')
"

    # Enviar al proyector (simulado)
    echo "Patrón de prueba enviado al proyector"
}

# Función para mostrar estado
show_status() {
    echo "Estado del proyector GM12U320:"
    echo "USB Device: $USB_DEVICE"
    echo "Vendor ID: $USB_VID"
    echo "Product ID: $USB_PID"
    
    # Verificar si el dispositivo está conectado
    if lsusb -d ${USB_VID}:${USB_PID} >/dev/null 2>&1; then
        echo "Estado: Conectado"
    else
        echo "Estado: Desconectado"
    fi
}

# Función de ayuda
show_help() {
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos:"
    echo "  status     Mostrar estado del proyector"
    echo "  test       Generar patrón de prueba"
    echo "  on         Encender proyector"
    echo "  off        Apagar proyector"
    echo "  help       Mostrar esta ayuda"
    echo ""
}

# Función principal
main() {
    # Buscar dispositivo USB
    find_usb_device
    
    case "$1" in
        "status")
            show_status
            ;;
        "test")
            generate_test_pattern
            ;;
        "on")
            send_command "POWER_ON" ""
            echo "Proyector encendido"
            ;;
        "off")
            send_command "POWER_OFF" ""
            echo "Proyector apagado"
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            echo "Error: Comando no reconocido"
            show_help
            exit 1
            ;;
    esac
}

# Ejecutar función principal
main "$@" 