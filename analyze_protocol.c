#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libusb-1.0/libusb.h>

#define VENDOR_ID  0x1de1
#define PRODUCT_ID 0xc102
#define TIMEOUT    1000

void print_endpoint_info(libusb_device *device) {
    struct libusb_config_descriptor *config;
    int result = libusb_get_config_descriptor(device, 0, &config);
    if (result < 0) {
        printf("Error obteniendo descriptor de configuración\n");
        return;
    }
    
    printf("📊 Información de endpoints:\n");
    for (int i = 0; i < config->bNumInterfaces; i++) {
        const libusb_interface *interface = &config->interface[i];
        printf("Interfaz %d:\n", i);
        
        for (int j = 0; j < interface->num_altsetting; j++) {
            const libusb_interface_descriptor *altsetting = &interface->altsetting[j];
            printf("  Configuración alternativa %d:\n", j);
            printf("    Número de endpoints: %d\n", altsetting->bNumEndpoints);
            
            for (int k = 0; k < altsetting->bNumEndpoints; k++) {
                const libusb_endpoint_descriptor *endpoint = &altsetting->endpoint[k];
                printf("    Endpoint 0x%02x:\n", endpoint->bEndpointAddress);
                printf("      Dirección: 0x%02x\n", endpoint->bEndpointAddress);
                printf("      Atributos: 0x%02x\n", endpoint->bmAttributes);
                printf("      Tamaño máximo: %d\n", endpoint->wMaxPacketSize);
                printf("      Intervalo: %d\n", endpoint->bInterval);
                
                // Determinar tipo de endpoint
                int endpoint_type = endpoint->bmAttributes & 0x03;
                switch (endpoint_type) {
                    case 0: printf("      Tipo: Control\n"); break;
                    case 1: printf("      Tipo: Isochronous\n"); break;
                    case 2: printf("      Tipo: Bulk\n"); break;
                    case 3: printf("      Tipo: Interrupt\n"); break;
                }
                
                // Determinar dirección
                if (endpoint->bEndpointAddress & 0x80) {
                    printf("      Dirección: IN (dispositivo -> host)\n");
                } else {
                    printf("      Dirección: OUT (host -> dispositivo)\n");
                }
            }
        }
    }
    
    libusb_free_config_descriptor(config);
}

int main() {
    libusb_context *ctx = NULL;
    libusb_device_handle *handle = NULL;
    libusb_device *device = NULL;
    int result;
    
    printf("🔍 Analizando protocolo del proyector GM12U320...\n");
    
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
    
    device = libusb_get_device(handle);
    printf("✅ Dispositivo USB abierto correctamente\n");
    
    // Obtener información del dispositivo
    libusb_device_descriptor desc;
    result = libusb_get_device_descriptor(device, &desc);
    if (result == 0) {
        printf("📋 Descriptor del dispositivo:\n");
        printf("  bcdUSB: 0x%04x\n", desc.bcdUSB);
        printf("  bDeviceClass: %d\n", desc.bDeviceClass);
        printf("  bDeviceSubClass: %d\n", desc.bDeviceSubClass);
        printf("  bDeviceProtocol: %d\n", desc.bDeviceProtocol);
        printf("  bMaxPacketSize0: %d\n", desc.bMaxPacketSize0);
        printf("  idVendor: 0x%04x\n", desc.idVendor);
        printf("  idProduct: 0x%04x\n", desc.idProduct);
        printf("  bcdDevice: 0x%04x\n", desc.bcdDevice);
        printf("  bNumConfigurations: %d\n", desc.bNumConfigurations);
    }
    
    // Analizar endpoints
    print_endpoint_info(device);
    
    // Probar diferentes comandos
    printf("\n🔧 Probando comandos de control...\n");
    
    // Comando de control GET_STATUS
    unsigned char status_data[2];
    result = libusb_control_transfer(handle, 0x80, 0x00, 0x0000, 0x0000, 
                                   status_data, sizeof(status_data), TIMEOUT);
    if (result >= 0) {
        printf("✅ GET_STATUS exitoso: %d bytes\n", result);
        printf("  Datos: %02x %02x\n", status_data[0], status_data[1]);
    } else {
        printf("⚠️  GET_STATUS falló: %s\n", libusb_error_name(result));
    }
    
    // Comando de control GET_DESCRIPTOR
    unsigned char descriptor_data[64];
    result = libusb_control_transfer(handle, 0x80, 0x06, 0x0100, 0x0000, 
                                   descriptor_data, sizeof(descriptor_data), TIMEOUT);
    if (result >= 0) {
        printf("✅ GET_DESCRIPTOR exitoso: %d bytes\n", result);
        printf("  Datos: ");
        for (int i = 0; i < result && i < 16; i++) {
            printf("%02x ", descriptor_data[i]);
        }
        printf("\n");
    } else {
        printf("⚠️  GET_DESCRIPTOR falló: %s\n", libusb_error_name(result));
    }
    
    // Limpiar
    libusb_close(handle);
    libusb_exit(ctx);
    
    printf("\n✅ Análisis completado\n");
    return 0;
} 