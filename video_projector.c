#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <libusb-1.0/libusb.h>

#define VENDOR_ID  0x1de1
#define PRODUCT_ID 0xc102
#define TIMEOUT    1000

// Endpoints para video (basado en análisis)
#define EP_VIDEO_OUT   0x03  // Interfaz 0, Bulk OUT para video
#define EP_VIDEO_IN    0x82  // Interfaz 0, Bulk IN para control

// Configuración de video
#define VIDEO_WIDTH    800
#define VIDEO_HEIGHT   600
#define BYTES_PER_PIXEL 3
#define FRAME_SIZE     (VIDEO_WIDTH * VIDEO_HEIGHT * BYTES_PER_PIXEL)

// Comandos del proyector (basados en protocolos similares)
#define CMD_INIT       0x01
#define CMD_START      0x02
#define CMD_STOP       0x03
#define CMD_FRAME      0x04

int send_command(libusb_device_handle *handle, unsigned char cmd, unsigned char *data, int data_len) {
    unsigned char buffer[64];
    int bytes_transferred;
    
    // Construir comando
    buffer[0] = cmd;
    buffer[1] = data_len;
    if (data && data_len > 0) {
        memcpy(&buffer[2], data, data_len);
    }
    
    int result = libusb_bulk_transfer(handle, EP_VIDEO_OUT, buffer, 2 + data_len, 
                                     &bytes_transferred, TIMEOUT);
    if (result == 0) {
        printf("✅ Comando 0x%02x enviado: %d bytes\n", cmd, bytes_transferred);
        return 1;
    } else {
        printf("⚠️  Error enviando comando 0x%02x: %s\n", cmd, libusb_error_name(result));
        return 0;
    }
}

int send_frame(libusb_device_handle *handle, unsigned char *frame_data, int frame_size) {
    int bytes_transferred;
    int result;
    
    // Enviar comando de frame
    unsigned char cmd[] = {CMD_FRAME, (frame_size >> 16) & 0xFF, (frame_size >> 8) & 0xFF, frame_size & 0xFF};
    result = libusb_bulk_transfer(handle, EP_VIDEO_OUT, cmd, sizeof(cmd), &bytes_transferred, TIMEOUT);
    if (result != 0) {
        printf("⚠️  Error enviando comando de frame: %s\n", libusb_error_name(result));
        return 0;
    }
    
    // Enviar datos de frame en chunks
    int chunk_size = 1024; // Tamaño máximo del endpoint
    int sent = 0;
    
    while (sent < frame_size) {
        int to_send = (frame_size - sent < chunk_size) ? frame_size - sent : chunk_size;
        
        result = libusb_bulk_transfer(handle, EP_VIDEO_OUT, &frame_data[sent], to_send, 
                                     &bytes_transferred, TIMEOUT);
        if (result != 0) {
            printf("⚠️  Error enviando chunk de frame: %s\n", libusb_error_name(result));
            return 0;
        }
        
        sent += bytes_transferred;
        printf("📡 Frame: %d/%d bytes enviados\n", sent, frame_size);
    }
    
    printf("✅ Frame completo enviado: %d bytes\n", sent);
    return 1;
}

int main() {
    libusb_context *ctx = NULL;
    libusb_device_handle *handle = NULL;
    int result;
    
    printf("🎬 Enviando video al proyector GM12U320...\n");
    
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
    
    printf("🎮 Inicializando proyector...\n");
    
    // Comando de inicialización
    send_command(handle, CMD_INIT, NULL, 0);
    usleep(100000); // 100ms
    
    // Comando de inicio
    send_command(handle, CMD_START, NULL, 0);
    usleep(100000); // 100ms
    
    printf("🎨 Generando frame de prueba...\n");
    
    // Generar frame de prueba (patrón de barras de colores)
    unsigned char *frame_data = malloc(FRAME_SIZE);
    if (!frame_data) {
        fprintf(stderr, "❌ Error: No se pudo asignar memoria para el frame\n");
        libusb_release_interface(handle, 0);
        libusb_close(handle);
        libusb_exit(ctx);
        return 1;
    }
    
    // Crear patrón de barras verticales
    int bar_width = VIDEO_WIDTH / 8;
    for (int y = 0; y < VIDEO_HEIGHT; y++) {
        for (int x = 0; x < VIDEO_WIDTH; x++) {
            int pixel_offset = (y * VIDEO_WIDTH + x) * BYTES_PER_PIXEL;
            int bar_index = x / bar_width;
            
            // Colores: Rojo, Verde, Azul, Amarillo, Magenta, Cyan, Blanco, Negro
            unsigned char colors[8][3] = {
                {255, 0, 0},    // Rojo
                {0, 255, 0},    // Verde
                {0, 0, 255},    // Azul
                {255, 255, 0},  // Amarillo
                {255, 0, 255},  // Magenta
                {0, 255, 255},  // Cyan
                {255, 255, 255}, // Blanco
                {0, 0, 0}       // Negro
            };
            
            frame_data[pixel_offset] = colors[bar_index][0];     // R
            frame_data[pixel_offset + 1] = colors[bar_index][1]; // G
            frame_data[pixel_offset + 2] = colors[bar_index][2]; // B
        }
    }
    
    printf("📡 Enviando frame al proyector...\n");
    
    // Enviar frame
    if (send_frame(handle, frame_data, FRAME_SIZE)) {
        printf("✅ Frame enviado exitosamente\n");
    } else {
        printf("❌ Error enviando frame\n");
    }
    
    // Mantener frame por un momento
    usleep(2000000); // 2 segundos
    
    // Comando de parada
    send_command(handle, CMD_STOP, NULL, 0);
    
    // Limpiar
    free(frame_data);
    libusb_release_interface(handle, 0);
    libusb_close(handle);
    libusb_exit(ctx);
    
    printf("✅ Video enviado al proyector\n");
    return 0;
} 