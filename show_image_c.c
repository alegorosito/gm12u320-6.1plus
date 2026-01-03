/*
 * GM12U320 Projector Screen Capture - Optimized C Version
 * 
 * Captures screen and writes to /tmp/gm12u320_image.rgb
 * Usage: show_image_c <fps> screen
 * 
 * Compile: gcc -O3 -o show_image_c show_image_c.c -lX11 -lXext -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <sys/time.h>
#include <sys/shm.h>
#include <math.h>
#include <signal.h>

// Global flag for clean shutdown
static volatile int running = 1;

// Projector specifications (800x600)
#define PROJECTOR_WIDTH  800
#define PROJECTOR_HEIGHT 600
#define BYTES_PER_PIXEL  3
#define DATA_BYTES_PER_LINE  (PROJECTOR_WIDTH * BYTES_PER_PIXEL)  // 2400
#define STRIDE_BYTES_PER_LINE 2562  // 2400 data + 162 padding
#define PADDING_BYTES_PER_LINE (STRIDE_BYTES_PER_LINE - DATA_BYTES_PER_LINE)  // 162
#define TOTAL_FILE_SIZE (STRIDE_BYTES_PER_LINE * PROJECTOR_HEIGHT)  // 1,537,200

#define OUTPUT_FILE "/tmp/gm12u320_image.rgb"

// Global variables
static Display *display = NULL;
static Window root;
static XShmSegmentInfo shminfo;
static XImage *ximage = NULL;
static int screen_width, screen_height;
static int use_shm = 0;

// Function prototypes
static int init_x11(void);
static void cleanup_x11(void);
static int capture_screen(unsigned char *output_buffer);
static void resize_and_convert(unsigned char *src, int src_w, int src_h,
                               unsigned char *dst, int dst_w, int dst_h);
static void write_buffer_to_file(unsigned char *buffer, size_t size);
static double get_time(void);

// Initialize X11 and Shared Memory
static int init_x11(void) {
    int major, minor;
    Bool pixmaps;
    
    display = XOpenDisplay(NULL);
    if (!display) {
        fprintf(stderr, "Error: No se pudo abrir el display X11\n");
        return 0;
    }
    
    root = DefaultRootWindow(display);
    screen_width = DisplayWidth(display, DefaultScreen(display));
    screen_height = DisplayHeight(display, DefaultScreen(display));
    
    // Check for XShm extension
    if (!XShmQueryExtension(display)) {
        fprintf(stderr, "Warning: XShm no disponible, usando método más lento\n");
        use_shm = 0;
    } else {
        use_shm = 1;
    }
    
    if (use_shm) {
        // Create shared memory image
        ximage = XShmCreateImage(display, DefaultVisual(display, DefaultScreen(display)),
                                 DefaultDepth(display, DefaultScreen(display)),
                                 ZPixmap, NULL, &shminfo,
                                 screen_width, screen_height);
        
        if (!ximage) {
            fprintf(stderr, "Error: No se pudo crear XImage\n");
            use_shm = 0;
        } else {
            shminfo.shmid = shmget(IPC_PRIVATE, ximage->bytes_per_line * ximage->height,
                                   IPC_CREAT | 0777);
            if (shminfo.shmid < 0) {
                fprintf(stderr, "Warning: No se pudo crear shared memory, usando método normal\n");
                XDestroyImage(ximage);
                ximage = NULL;
                use_shm = 0;
            } else {
                shminfo.shmaddr = ximage->data = (char *)shmat(shminfo.shmid, 0, 0);
                shminfo.readOnly = False;
                
                if (!XShmAttach(display, &shminfo)) {
                    fprintf(stderr, "Warning: No se pudo adjuntar shared memory\n");
                    shmdt(shminfo.shmaddr);
                    shmctl(shminfo.shmid, IPC_RMID, 0);
                    XDestroyImage(ximage);
                    ximage = NULL;
                    use_shm = 0;
                }
            }
        }
    }
    
    printf("✅ X11 inicializado: %dx%d\n", screen_width, screen_height);
    if (use_shm) {
        printf("✅ Usando XShm para captura rápida\n");
    }
    
    return 1;
}

// Cleanup X11 resources
static void cleanup_x11(void) {
    if (use_shm && ximage) {
        XShmDetach(display, &shminfo);
        XDestroyImage(ximage);
        shmdt(shminfo.shmaddr);
        shmctl(shminfo.shmid, IPC_RMID, 0);
        ximage = NULL;
    }
    
    if (display) {
        XCloseDisplay(display);
        display = NULL;
    }
}

// Capture screen and convert to projector format
static int capture_screen(unsigned char *output_buffer) {
    XImage *img = NULL;
    
    if (use_shm && ximage) {
        // Fast capture using shared memory
        if (!XShmGetImage(display, root, ximage, 0, 0, AllPlanes)) {
            return 0;
        }
        img = ximage;
    } else {
        // Fallback: regular XGetImage (slower)
        img = XGetImage(display, root, 0, 0, screen_width, screen_height,
                       AllPlanes, ZPixmap);
        if (!img) {
            return 0;
        }
    }
    
    // Update global ximage pointer for resize function
    XImage *old_ximage = ximage;
    ximage = img;
    
    // Resize and convert RGB->BGR with stride
    resize_and_convert(NULL, img->width, img->height,
                      output_buffer, PROJECTOR_WIDTH, PROJECTOR_HEIGHT);
    
    // Restore ximage pointer
    ximage = old_ximage;
    
    // Only destroy if it's not the shared memory image
    if (!use_shm && img) {
        XDestroyImage(img);
    }
    
    return 1;
}

// Fast resize and convert RGB to BGR with stride
static void resize_and_convert(unsigned char *dst) {
    unsigned char *src = (unsigned char *)ximage->data;
    int src_stride = ximage->bytes_per_line;

    double scale_x = (double)ximage->width / PROJECTOR_WIDTH;
    double scale_y = (double)ximage->height / PROJECTOR_HEIGHT;

    for (int y = 0; y < PROJECTOR_HEIGHT; y++) {
        int src_y = (int)(y * scale_y);
        unsigned char *dst_row = dst + y * STRIDE_BYTES_PER_LINE;

        unsigned char *src_row =
            src + src_y * src_stride;

        for (int x = 0; x < PROJECTOR_WIDTH; x++) {
            int src_x = (int)(x * scale_x);
            unsigned char *p = src_row + src_x * 4;

            dst_row[x * 3 + 0] = p[0]; // B
            dst_row[x * 3 + 1] = p[1]; // G
            dst_row[x * 3 + 2] = p[2]; // R
        }
    }
}

// Write buffer to file
static void write_buffer_to_file(unsigned char *buffer, size_t size) {
    FILE *f = fopen(OUTPUT_FILE, "wb");
    if (!f) {
        perror("Error abriendo archivo");
        return;
    }
    
    size_t written = fwrite(buffer, 1, size, f);
    fclose(f);
    
    if (written != size) {
        fprintf(stderr, "Warning: Solo se escribieron %zu de %zu bytes\n", written, size);
    }
}

// Get current time in seconds (high precision)
static double get_time(void) {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return tv.tv_sec + tv.tv_usec / 1000000.0;
}

// Signal handler for clean shutdown
static void signal_handler(int sig) {
    running = 0;
}

int main(int argc, char *argv[]) {
    double fps = 10.0;
    double frame_interval;
    double start_time, frame_start, current_time;
    unsigned long frame_count = 0;
    unsigned char *output_buffer;
    
    // Parse arguments
    if (argc < 3) {
        fprintf(stderr, "Uso: %s <fps> screen\n", argv[0]);
        fprintf(stderr, "Ejemplo: %s 24 screen\n", argv[0]);
        return 1;
    }
    
    if (strcmp(argv[2], "screen") != 0) {
        fprintf(stderr, "Error: Solo se soporta el modo 'screen'\n");
        return 1;
    }
    
    fps = atof(argv[1]);
    if (fps <= 0 || fps > 60) {
        fprintf(stderr, "Error: FPS debe estar entre 0.1 y 60\n");
        return 1;
    }
    
    frame_interval = 1.0 / fps;
    
    printf("GM12U320 Screen Capture (C - Optimizado)\n");
    printf("==========================================\n");
    printf("FPS: %.2f\n", fps);
    printf("Intervalo: %.3f segundos\n", frame_interval);
    printf("Resolución: %dx%d\n", PROJECTOR_WIDTH, PROJECTOR_HEIGHT);
    printf("Presiona Ctrl+C para detener\n\n");
    
    // Allocate output buffer
    output_buffer = (unsigned char *)calloc(TOTAL_FILE_SIZE, 1);
    if (!output_buffer) {
        fprintf(stderr, "Error: No se pudo asignar memoria\n");
        return 1;
    }
    
    // Initialize X11
    if (!init_x11()) {
        free(output_buffer);
        return 1;
    }
    
    // Setup signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    start_time = get_time();
    
    // Main capture loop
    while (running) {
        frame_start = get_time();
        
        // Capture screen
        if (capture_screen(output_buffer)) {
            // Write to file
            write_buffer_to_file(output_buffer, TOTAL_FILE_SIZE);
            frame_count++;
            
            // Print stats every 10 frames
            if (frame_count % 10 == 0) {
                current_time = get_time();
                double elapsed = current_time - start_time;
                double actual_fps = frame_count / elapsed;
                printf("Frame %lu | FPS: %.1f | Tiempo: %.1fs\n",
                       frame_count, actual_fps, elapsed);
            }
        } else {
            fprintf(stderr, "⚠️  Error capturando pantalla\n");
        }
        
        // Sleep to maintain FPS
        current_time = get_time();
        double frame_time = current_time - frame_start;
        double sleep_time = frame_interval - frame_time;
        
        if (sleep_time > 0) {
            usleep((unsigned int)(sleep_time * 1000000));
        }
    }
    
    // Cleanup
    printf("\n⏹️  Deteniendo...\n");
    cleanup_x11();
    free(output_buffer);
    
    // Final stats
    double total_time = get_time() - start_time;
    double final_fps = frame_count / total_time;
    printf("📊 Estadísticas finales:\n");
    printf("   Frames: %lu\n", frame_count);
    printf("   Tiempo: %.1fs\n", total_time);
    printf("   FPS promedio: %.1f\n", final_fps);
    
    return 0;
}

