#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libusb-1.0/libusb.h>

#define VENDOR_ID  0x1de1
#define PRODUCT_ID 0xc102
#define TIMEOUT    1000

// Endpoints identificados
#define EP_OUT_1   0x03
#define EP_IN_1    0x82
#define EP_OUT_2   0x04
#define EP_IN_2    0x81

void print_hex(const char *prefix, unsigned char *data, int len) {
    printf("%s", prefix);
    for (int i = 0; i < len && i < 32; i++) {
        printf("%02x ", data[i]);
    }
    if (len > 32) printf("...");
    printf(" (%d bytes)\n", len);
}

int main() {
    libusb_context *ctx = NULL;
    libusb_device_handle *handle = NULL;
    int result;
    
    printf("🔍 Monitoreando tráfico USB del proyector GM12U320...\n");
    printf("💡 Conecta el proyector y observa los logs del kernel\n");
    printf("💡 Usa: sudo dmesg | grep -i usb\n");
    printf("💡 O: sudo journalctl -f | grep -i usb\n\n");
    
    // Inicializar libusb
    result = libusb_init(&ctx);
    if (result < 0) {
        fprintf(stderr, "❌ Error inicializando libusb: %s\n", libusb_error_name(result));
        return 1;
    }
    
    // Buscar dispositivo
    handle = libusb_open_device_with_vid_pid(ctx, VENDOR_ID, PRODUCT_ID);
    if (handle == NULL) {
        fprintf(stderr, "❌ Error: No se pudo abrir el dispositivo USB\n");
        libusb_exit(ctx);
        return 1;
    }
    
    printf("✅ Dispositivo USB abierto correctamente\n");
    
    // Obtener información del dispositivo
    struct libusb_device *device = libusb_get_device(handle);
    struct libusb_device_descriptor desc;
    result = libusb_get_device_descriptor(device, &desc);
    
    if (result == 0) {
        printf("📋 Información del dispositivo:\n");
        printf("  Fabricante ID: 0x%04x\n", desc.idVendor);
        printf("  Producto ID: 0x%04x\n", desc.idProduct);
        printf("  Versión USB: 0x%04x\n", desc.bcdUSB);
        printf("  Versión dispositivo: 0x%04x\n", desc.bcdDevice);
        printf("  Clase: %d\n", desc.bDeviceClass);
        printf("  Subclase: %d\n", desc.bDeviceSubClass);
        printf("  Protocolo: %d\n", desc.bDeviceProtocol);
    }
    
    // Configurar dispositivo
    result = libusb_set_configuration(handle, 1);
    if (result < 0) {
        printf("⚠️  Configuración falló: %s\n", libusb_error_name(result));
    } else {
        printf("✅ Configuración exitosa\n");
    }
    
    // Reclamar interfaces
    result = libusb_claim_interface(handle, 0);
    if (result < 0) {
        printf("⚠️  Interfaz 0 falló: %s\n", libusb_error_name(result));
    } else {
        printf("✅ Interfaz 0 reclamada\n");
    }
    
    result = libusb_claim_interface(handle, 1);
    if (result < 0) {
        printf("⚠️  Interfaz 1 falló: %s\n", libusb_error_name(result));
    } else {
        printf("✅ Interfaz 1 reclamada\n");
    }
    
    printf("\n🔧 Probando diferentes comandos...\n");
    
    // Probar diferentes comandos de control
    unsigned char control_commands[][8] = {
        {0x00, 0x00, 0x00, 0x00}, // GET_STATUS
        {0x01, 0x00, 0x00, 0x00}, // SET_FEATURE
        {0x02, 0x00, 0x00, 0x00}, // CLEAR_FEATURE
        {0x03, 0x00, 0x00, 0x00}, // SET_ADDRESS
        {0x04, 0x00, 0x00, 0x00}, // GET_DESCRIPTOR
        {0x05, 0x00, 0x00, 0x00}, // SET_DESCRIPTOR
        {0x06, 0x00, 0x00, 0x00}, // GET_CONFIGURATION
        {0x07, 0x00, 0x00, 0x00}, // SET_CONFIGURATION
        {0x08, 0x00, 0x00, 0x00}, // GET_INTERFACE
        {0x09, 0x00, 0x00, 0x00}, // SET_INTERFACE
    };
    
    for (int i = 0; i < 10; i++) {
        printf("Probando comando 0x%02x... ", i);
        result = libusb_control_transfer(handle, 0x21, i, 0x0000, 0x0000, 
                                       control_commands[i], sizeof(control_commands[i]), TIMEOUT);
        if (result >= 0) {
            printf("✅ (%d bytes)\n", result);
            print_hex("  Datos: ", control_commands[i], result);
        } else {
            printf("❌ (%s)\n", libusb_error_name(result));
        }
        usleep(100000); // 100ms
    }
    
    printf("\n📡 Probando endpoints bulk...\n");
    
    // Probar endpoints con datos pequeños
    unsigned char test_data[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF};
    int bytes_transferred;
    
    // Endpoint 0x03 (OUT)
    printf("Endpoint 0x03 (OUT): ");
    result = libusb_bulk_transfer(handle, EP_OUT_1, test_data, sizeof(test_data), 
                                 &bytes_transferred, TIMEOUT);
    if (result == 0) {
        printf("✅ (%d bytes)\n", bytes_transferred);
    } else {
        printf("❌ (%s)\n", libusb_error_name(result));
    }
    
    // Endpoint 0x82 (IN)
    printf("Endpoint 0x82 (IN): ");
    unsigned char response[64];
    result = libusb_bulk_transfer(handle, EP_IN_1, response, sizeof(response), 
                                 &bytes_transferred, TIMEOUT);
    if (result == 0) {
        printf("✅ (%d bytes)\n", bytes_transferred);
        print_hex("  Respuesta: ", response, bytes_transferred);
    } else {
        printf("❌ (%s)\n", libusb_error_name(result));
    }
    
    // Endpoint 0x04 (OUT)
    printf("Endpoint 0x04 (OUT): ");
    result = libusb_bulk_transfer(handle, EP_OUT_2, test_data, sizeof(test_data), 
                                 &bytes_transferred, TIMEOUT);
    if (result == 0) {
        printf("✅ (%d bytes)\n", bytes_transferred);
    } else {
        printf("❌ (%s)\n", libusb_error_name(result));
    }
    
    // Endpoint 0x81 (IN)
    printf("Endpoint 0x81 (IN): ");
    result = libusb_bulk_transfer(handle, EP_IN_2, response, sizeof(response), 
                                 &bytes_transferred, TIMEOUT);
    if (result == 0) {
        printf("✅ (%d bytes)\n", bytes_transferred);
        print_hex("  Respuesta: ", response, bytes_transferred);
    } else {
        printf("❌ (%s)\n", libusb_error_name(result));
    }
    
    printf("\n💡 Consejos para investigar el protocolo:\n");
    printf("1. Ejecuta: sudo dmesg | grep -i usb\n");
    printf("2. Ejecuta: sudo journalctl -f | grep -i usb\n");
    printf("3. Usa Wireshark para capturar tráfico USB\n");
    printf("4. Busca drivers existentes para GM12U320\n");
    printf("5. Revisa documentación del fabricante\n");
    
    // Limpiar
    libusb_release_interface(handle, 1);
    libusb_release_interface(handle, 0);
    libusb_close(handle);
    libusb_exit(ctx);
    
    printf("\n✅ Monitoreo completado\n");
    return 0;
} 