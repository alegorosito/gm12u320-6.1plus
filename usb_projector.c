#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libusb-1.0/libusb.h>

#define VENDOR_ID  0x1de1
#define PRODUCT_ID 0xc102
#define TIMEOUT    5000

int main() {
    libusb_context *ctx = NULL;
    libusb_device_handle *handle = NULL;
    int result;
    
    printf("🔌 Inicializando comunicación USB con proyector GM12U320...\n");
    
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
    
    // Reclamar interfaz
    result = libusb_claim_interface(handle, 0);
    if (result < 0) {
        fprintf(stderr, "⚠️  Warning: No se pudo reclamar interfaz: %s\n", libusb_error_name(result));
    }
    
    printf("🔧 Intentando enviar comando de prueba...\n");
    
    // Comando de prueba (esto es un ejemplo, necesitamos el protocolo real)
    unsigned char test_cmd[] = {0x01, 0x02, 0x03, 0x04};
    int bytes_transferred;
    
    result = libusb_bulk_transfer(handle, 0x01, test_cmd, sizeof(test_cmd), 
                                 &bytes_transferred, TIMEOUT);
    
    if (result == 0) {
        printf("✅ Comando enviado: %d bytes\n", bytes_transferred);
    } else {
        printf("⚠️  Error enviando comando: %s\n", libusb_error_name(result));
    }
    
    // Leer respuesta
    unsigned char response[64];
    result = libusb_bulk_transfer(handle, 0x81, response, sizeof(response), 
                                 &bytes_transferred, TIMEOUT);
    
    if (result == 0) {
        printf("✅ Respuesta recibida: %d bytes\n", bytes_transferred);
        printf("Datos: ");
        for (int i = 0; i < bytes_transferred && i < 16; i++) {
            printf("%02x ", response[i]);
        }
        printf("\n");
    } else {
        printf("⚠️  Error leyendo respuesta: %s\n", libusb_error_name(result));
    }
    
    // Información del dispositivo
    printf("\n📊 Información del dispositivo:\n");
    
    unsigned char manufacturer[256];
    result = libusb_get_string_descriptor_ascii(handle, 1, manufacturer, sizeof(manufacturer));
    if (result > 0) {
        manufacturer[result] = '\0';
        printf("Fabricante: %s\n", manufacturer);
    }
    
    unsigned char product[256];
    result = libusb_get_string_descriptor_ascii(handle, 9, product, sizeof(product));
    if (result > 0) {
        product[result] = '\0';
        printf("Producto: %s\n", product);
    }
    
    // Limpiar
    libusb_release_interface(handle, 0);
    libusb_close(handle);
    libusb_exit(ctx);
    
    printf("✅ Comunicación USB finalizada\n");
    return 0;
} 