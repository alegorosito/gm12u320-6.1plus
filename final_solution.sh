#!/bin/bash

# Solución final para el proyector GM12U320
# Combina driver del kernel con comunicación USB directa

set -e

echo "🎯 Solución Final para GM12U320"
echo "================================"

# Configuración
USB_VID="1de1"
USB_PID="c102"
DRIVER_NAME="gm12u320"

# Función para verificar proyector
check_projector() {
    echo "🔍 Verificando proyector..."
    if lsusb -d ${USB_VID}:${USB_PID} >/dev/null 2>&1; then
        echo "✅ Proyector GM12U320 detectado"
        return 0
    else
        echo "❌ Proyector GM12U320 no encontrado"
        return 1
    fi
}

# Función para cargar driver
load_driver() {
    echo "📦 Cargando driver del kernel..."
    
    # Desactivar driver anterior si existe
    sudo rmmod $DRIVER_NAME 2>/dev/null || echo "Driver no estaba cargado"
    
    # Intentar cargar con DKMS
    if sudo dkms status | grep -q "$DRIVER_NAME"; then
        echo "Instalando con DKMS..."
        sudo dkms install $DRIVER_NAME/0.1
    else
        echo "Compilando driver..."
        make clean && make
        sudo insmod gm12u320.ko screen_mirror=false
    fi
    
    # Verificar si se cargó
    if lsmod | grep -q "$DRIVER_NAME"; then
        echo "✅ Driver cargado correctamente"
        return 0
    else
        echo "❌ Error cargando driver"
        return 1
    fi
}

# Función para crear framebuffer virtual
create_virtual_fb() {
    echo "🖥️  Creando framebuffer virtual..."
    
    # Crear dispositivo si no existe
    if [ ! -e "/dev/fb1" ]; then
        sudo mknod /dev/fb1 c 29 1 2>/dev/null || true
        sudo chmod 666 /dev/fb1
        sudo chown root:video /dev/fb1
        echo "✅ Framebuffer virtual creado: /dev/fb1"
    else
        echo "✅ Framebuffer ya existe: /dev/fb1"
    fi
}

# Función para enviar patrón de prueba
send_test_pattern() {
    echo "🎨 Enviando patrón de prueba..."
    
    # Compilar programa de video si no existe
    if [ ! -f "video_projector" ]; then
        echo "Compilando programa de video..."
        gcc -o video_projector video_projector.c -lusb-1.0
    fi
    
    # Ejecutar programa de video
    echo "Ejecutando programa de video..."
    sudo ./video_projector
}

# Función para mostrar estado
show_status() {
    echo ""
    echo "📊 Estado del sistema:"
    echo "====================="
    
    # Verificar proyector
    if check_projector; then
        echo "✅ Proyector: Conectado"
    else
        echo "❌ Proyector: Desconectado"
    fi
    
    # Verificar driver
    if lsmod | grep -q "$DRIVER_NAME"; then
        echo "✅ Driver: Cargado"
    else
        echo "❌ Driver: No cargado"
    fi
    
    # Verificar framebuffers
    if [ -e "/dev/fb0" ]; then
        echo "✅ Framebuffer principal: /dev/fb0"
    else
        echo "❌ Framebuffer principal: No disponible"
    fi
    
    if [ -e "/dev/fb1" ]; then
        echo "✅ Framebuffer proyector: /dev/fb1"
    else
        echo "❌ Framebuffer proyector: No disponible"
    fi
    
    # Verificar programas
    if [ -f "video_projector" ]; then
        echo "✅ Programa de video: Compilado"
    else
        echo "❌ Programa de video: No compilado"
    fi
}

# Función de ayuda
show_help() {
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos:"
    echo "  check      Verificar estado del proyector"
    echo "  load       Cargar driver del kernel"
    echo "  fb         Crear framebuffer virtual"
    echo "  test       Enviar patrón de prueba"
    echo "  status     Mostrar estado completo"
    echo "  all        Ejecutar todos los pasos"
    echo "  help       Mostrar esta ayuda"
    echo ""
}

# Función principal
main() {
    case "$1" in
        "check")
            check_projector
            ;;
        "load")
            check_projector && load_driver
            ;;
        "fb")
            create_virtual_fb
            ;;
        "test")
            check_projector && send_test_pattern
            ;;
        "status")
            show_status
            ;;
        "all")
            echo "🚀 Ejecutando solución completa..."
            check_projector || exit 1
            load_driver || echo "⚠️  Driver no se pudo cargar, continuando..."
            create_virtual_fb
            send_test_pattern
            show_status
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