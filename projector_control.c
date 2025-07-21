#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libusb-1.0/libusb.h>

#define VENDOR_ID  0x1de1
#define PRODUCT_ID 0xc102
#define TIMEOUT    5000

// Endpoints identificados
#define EP_OUT_1   0x03  // Interfaz 0, Bulk OUT
#define EP_IN_1    0x82  // Interfaz 0, Bulk IN
#define EP_OUT_2   0x04  // Interfaz 1, Bulk OUT
#define EP_IN_2    0x81  // Interfaz 1, Bulk IN

int main() {
    libusb_context *ctx = NULL;
    libusb_device_handle *handle = NULL;
    int result;
    
    printf("🎯 Control del proyector GM12U320 usando endpoints identificados...\n");
    
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
    
    // Configurar dispositivo
    result = libusb_set_configuration(handle, 1);
    if (result < 0) {
        fprintf(stderr, "⚠️  Warning: No se pudo configurar dispositivo: %s\n", libusb_error_name(result));
    }
    
    // Reclamar ambas interfaces
    result = libusb_claim_interface(handle, 0);
    if (result < 0) {
        fprintf(stderr, "⚠️  Warning: No se pudo reclamar interfaz 0: %s\n", libusb_error_name(result));
    }
    
    result = libusb_claim_interface(handle, 1);
    if (result < 0) {
        fprintf(stderr, "⚠️  Warning: No se pudo reclamar interfaz 1: %s\n", libusb_error_name(result));
    }
    
    printf("🔧 Probando comunicación con endpoints...\n");
    
    // Comando de prueba para interfaz 0
    printf("\n📡 Interfaz 0 - Endpoint 0x%02x (OUT):\n", EP_OUT_1);
    unsigned char cmd1[] = {0x01, 0x02, 0x03, 0x04, 0x05};
    int bytes_transferred;
    
    result = libusb_bulk_transfer(handle, EP_OUT_1, cmd1, sizeof(cmd1), 
                                 &bytes_transferred, TIMEOUT);
    if (result == 0) {
        printf("✅ Comando enviado: %d bytes\n", bytes_transferred);
    } else {
        printf("⚠️  Error enviando comando: %s\n", libusb_error_name(result));
    }
    
    // Leer respuesta de interfaz 0
    printf("📡 Interfaz 0 - Endpoint 0x%02x (IN):\n", EP_IN_1);
    unsigned char response1[64];
    result = libusb_bulk_transfer(handle, EP_IN_1, response1, sizeof(response1), 
                                 &bytes_transferred, TIMEOUT);
    if (result == 0) {
        printf("✅ Respuesta recibida: %d bytes\n", bytes_transferred);
        printf("  Datos: ");
        for (int i = 0; i < bytes_transferred && i < 16; i++) {
            printf("%02x ", response1[i]);
        }
        printf("\n");
    } else {
        printf("⚠️  Error leyendo respuesta: %s\n", libusb_error_name(result));
    }
    
    // Comando de prueba para interfaz 1
    printf("\n📡 Interfaz 1 - Endpoint 0x%02x (OUT):\n", EP_OUT_2);
    unsigned char cmd2[] = {0xAA, 0xBB, 0xCC, 0xDD};
    
    result = libusb_bulk_transfer(handle, EP_OUT_2, cmd2, sizeof(cmd2), 
                                 &bytes_transferred, TIMEOUT);
    if (result == 0) {
        printf("✅ Comando enviado: %d bytes\n", bytes_transferred);
    } else {
        printf("⚠️  Error enviando comando: %s\n", libusb_error_name(result));
    }
    
    // Leer respuesta de interfaz 1
    printf("📡 Interfaz 1 - Endpoint 0x%02x (IN):\n", EP_IN_2);
    unsigned char response2[64];
    result = libusb_bulk_transfer(handle, EP_IN_2, response2, sizeof(response2), 
                                 &bytes_transferred, TIMEOUT);
    if (result == 0) {
        printf("✅ Respuesta recibida: %d bytes\n", bytes_transferred);
        printf("  Datos: ");
        for (int i = 0; i < bytes_transferred && i < 16; i++) {
            printf("%02x ", response2[i]);
        }
        printf("\n");
    } else {
        printf("⚠️  Error leyendo respuesta: %s\n", libusb_error_name(result));
    }
    
    // Probar comando de control específico
    printf("\n🎮 Probando comandos de control específicos...\n");
    
    // Comando de control SET_FEATURE
    unsigned char control_data[1] = {0x00};
    result = libusb_control_transfer(handle, 0x21, 0x03, 0x0000, 0x0000, 
                                   control_data, sizeof(control_data), TIMEOUT);
    if (result >= 0) {
        printf("✅ SET_FEATURE exitoso: %d bytes\n", result);
    } else {
        printf("⚠️  SET_FEATURE falló: %s\n", libusb_error_name(result));
    }
    
    // Limpiar
    libusb_release_interface(handle, 1);
    libusb_release_interface(handle, 0);
    libusb_close(handle);
    libusb_exit(ctx);
    
    printf("\n✅ Control del proyector completado\n");
    return 0;
} 