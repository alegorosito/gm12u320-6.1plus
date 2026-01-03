/*
 * GM12U320 Projector Screen Mirror - mmap optimized (simple)
 *
 * Captura el desktop X11 y escribe el framebuffer directamente
 * en memoria RAM mediante mmap.
 *
 * Uso:
 *   ./show_image_c 24 screen
 *
 * Compilar:
 *   gcc -O3 -o show_image_c show_image_c.c \
 *     $(pkg-config --cflags --libs x11 xext) -lm
 */

 #define _GNU_SOURCE

 #include <stdio.h>
 #include <stdlib.h>
 #include <string.h>
 #include <unistd.h>
 #include <fcntl.h>
 #include <sys/mman.h>
 #include <sys/time.h>
 #include <sys/shm.h>
 #include <signal.h>
 #include <errno.h>
 
 #include <X11/Xlib.h>
 #include <X11/Xutil.h>
 #include <X11/extensions/XShm.h>
 
 static volatile int running = 1;
 
 /* Proyector */
 #define PROJECTOR_WIDTH   800
 #define PROJECTOR_HEIGHT  600
 #define BYTES_PER_PIXEL   3
 #define DATA_BYTES_PER_LINE  (PROJECTOR_WIDTH * BYTES_PER_PIXEL)
 #define STRIDE_BYTES_PER_LINE 2562
 #define TOTAL_FILE_SIZE (STRIDE_BYTES_PER_LINE * PROJECTOR_HEIGHT)
 
 #define OUTPUT_FILE "/tmp/gm12u320_image.rgb"
 
 /* X11 */
 static Display *display = NULL;
 static Window root;
 static XImage *ximage = NULL;
 static XShmSegmentInfo shminfo;
 static int screen_w = 0, screen_h = 0;
 static int use_shm = 0;
 
 /* mmap */
 static int fb_fd = -1;
 static unsigned char *fb_map = NULL;
 
 /* timing */
 static double now_sec(void) {
     struct timeval tv;
     gettimeofday(&tv, NULL);
     return tv.tv_sec + tv.tv_usec / 1000000.0;
 }
 
 static void on_signal(int sig) {
     (void)sig;
     running = 0;
 }
 
 /* ---------------- X11 ---------------- */
 
 static int init_x11(void) {
     display = XOpenDisplay(NULL);
     if (!display) {
         fprintf(stderr, "❌ No se pudo abrir display X11\n");
         return 0;
     }
 
     root = DefaultRootWindow(display);
     screen_w = DisplayWidth(display, DefaultScreen(display));
     screen_h = DisplayHeight(display, DefaultScreen(display));
 
     if (XShmQueryExtension(display)) {
         use_shm = 1;
         ximage = XShmCreateImage(
             display,
             DefaultVisual(display, DefaultScreen(display)),
             DefaultDepth(display, DefaultScreen(display)),
             ZPixmap,
             NULL,
             &shminfo,
             screen_w,
             screen_h
         );
 
         if (!ximage) {
             fprintf(stderr, "⚠️ XShmCreateImage falló, fallback\n");
             use_shm = 0;
         } else {
             shminfo.shmid = shmget(
                 IPC_PRIVATE,
                 ximage->bytes_per_line * ximage->height,
                 IPC_CREAT | 0777
             );
 
             if (shminfo.shmid < 0) {
                 fprintf(stderr, "⚠️ shmget falló, fallback\n");
                 use_shm = 0;
             } else {
                 shminfo.shmaddr = ximage->data = shmat(shminfo.shmid, 0, 0);
                 if (shminfo.shmaddr == (char*)-1) {
                     fprintf(stderr, "⚠️ shmat falló, fallback\n");
                     shmctl(shminfo.shmid, IPC_RMID, 0);
                     use_shm = 0;
                 } else {
                     shminfo.readOnly = False;
                     if (!XShmAttach(display, &shminfo)) {
                         fprintf(stderr, "⚠️ XShmAttach falló, fallback\n");
                         shmdt(shminfo.shmaddr);
                         shmctl(shminfo.shmid, IPC_RMID, 0);
                         use_shm = 0;
                     }
                 }
             }
         }
     }
 
     if (!use_shm) {
         ximage = XGetImage(
             display, root, 0, 0,
             screen_w, screen_h,
             AllPlanes, ZPixmap
         );
         if (!ximage) {
             fprintf(stderr, "❌ XGetImage falló\n");
             return 0;
         }
     }
 
     printf("✅ X11 %dx%d (%s)\n", screen_w, screen_h, use_shm ? "XShm" : "XGetImage");
     return 1;
 }
 
 static void cleanup_x11(void) {
     if (use_shm && ximage) {
         XShmDetach(display, &shminfo);
         XDestroyImage(ximage);            // también libera ximage->data (pero shm se maneja aparte)
         shmdt(shminfo.shmaddr);
         shmctl(shminfo.shmid, IPC_RMID, 0);
         ximage = NULL;
     } else if (ximage) {
         XDestroyImage(ximage);
         ximage = NULL;
     }
 
     if (display) {
         XCloseDisplay(display);
         display = NULL;
     }
 }
 
 /* ---------------- mmap ---------------- */
 
 static int init_mmap(void) {
     fb_fd = open(OUTPUT_FILE, O_RDWR | O_CREAT, 0666);
     if (fb_fd < 0) {
         perror("open");
         return 0;
     }
 
     if (ftruncate(fb_fd, TOTAL_FILE_SIZE) < 0) {
         perror("ftruncate");
         close(fb_fd);
         fb_fd = -1;
         return 0;
     }
 
     fb_map = mmap(
         NULL,
         TOTAL_FILE_SIZE,
         PROT_READ | PROT_WRITE,
         MAP_SHARED,
         fb_fd,
         0
     );
 
     if (fb_map == MAP_FAILED) {
         perror("mmap");
         fb_map = NULL;
         close(fb_fd);
         fb_fd = -1;
         return 0;
     }
 
     memset(fb_map, 0, TOTAL_FILE_SIZE);
     return 1;
 }
 
 static void cleanup_mmap(void) {
     if (fb_map) {
         munmap(fb_map, TOTAL_FILE_SIZE);
         fb_map = NULL;
     }
     if (fb_fd >= 0) {
         close(fb_fd);
         fb_fd = -1;
     }
 }
 
 /* -------- resize + BGR copy -------- */
 
 static void convert_frame(void) {
     unsigned char *src = (unsigned char *)ximage->data;
     int src_stride = ximage->bytes_per_line;
 
     double sx = (double)ximage->width  / PROJECTOR_WIDTH;
     double sy = (double)ximage->height / PROJECTOR_HEIGHT;
 
     for (int y = 0; y < PROJECTOR_HEIGHT; y++) {
         int syy = (int)(y * sy);
         unsigned char *dst_row = fb_map + y * STRIDE_BYTES_PER_LINE;
         unsigned char *src_row = src + syy * src_stride;
 
         for (int x = 0; x < PROJECTOR_WIDTH; x++) {
             int sxx = (int)(x * sx);
             unsigned char *p = src_row + sxx * 4;  // asumimos X11 32bpp
 
             dst_row[x*3 + 0] = p[0]; // B
             dst_row[x*3 + 1] = p[1]; // G
             dst_row[x*3 + 2] = p[2]; // R
         }
     }
 }
 
 /* ---------------- main ---------------- */
 
 int main(int argc, char **argv) {
     if (argc != 3 || strcmp(argv[2], "screen") != 0) {
         return 1;
     }
 
     double fps = atof(argv[1]);
     if (fps <= 0.0 || fps > 60.0) {
         return 1;
     }
 
     double interval = 1.0 / fps;
 
     signal(SIGINT, on_signal);
     signal(SIGTERM, on_signal);
 
     if (!init_x11()) return 1;
     if (!init_mmap()) return 1;
 
     // printf("▶ Mirror activo (%.1f FPS)\n", fps);
 
     while (running) {
         double t0 = now_sec();
 
         if (use_shm) {
             XShmGetImage(display, root, ximage, 0, 0, AllPlanes);
         } else {
             XGetSubImage(display, root, 0, 0,
                          screen_w, screen_h,
                          AllPlanes, ZPixmap,
                          ximage, 0, 0);
         }
 
         convert_frame();
 
         double dt = now_sec() - t0;
         double sleep_s = interval - dt;
         if (sleep_s > 0) {
             usleep((useconds_t)(sleep_s * 1e6));
         }
     }
 
     cleanup_mmap();
     cleanup_x11();
     return 0;
 }