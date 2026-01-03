/*
 * GM12U320 Projector Screen Capture
 * Stable version with DOUBLE BUFFER + ATOMIC SWAP
 *
 * Usage:
 *   ./show_image_c <fps> screen
 *
 * Compile:
 *   gcc -O3 -o show_image_c show_image_c.c \
 *       $(pkg-config --cflags --libs x11 xext) -lm
 */

 #include <stdio.h>
 #include <stdlib.h>
 #include <string.h>
 #include <unistd.h>
 #include <time.h>
 #include <sys/time.h>
 #include <fcntl.h>
 #include <sys/stat.h>
 #include <X11/Xlib.h>
 #include <X11/Xutil.h>
 #include <X11/extensions/XShm.h>
 #include <sys/shm.h>
 #include <signal.h>
 
 /* ================= CONFIG ================= */
 
 #define PROJECTOR_WIDTH   800
 #define PROJECTOR_HEIGHT  600
 #define BYTES_PER_PIXEL   3
 #define DATA_BYTES_PER_LINE (PROJECTOR_WIDTH * BYTES_PER_PIXEL)
 #define STRIDE_BYTES_PER_LINE 2562
 #define TOTAL_FILE_SIZE (STRIDE_BYTES_PER_LINE * PROJECTOR_HEIGHT)
 
 /* Double buffer files */
 #define FILE_A "/tmp/gm12u320_A.rgb"
 #define FILE_B "/tmp/gm12u320_B.rgb"
 #define FILE_ACTIVE "/tmp/gm12u320_image.rgb"
 
 /* ========================================== */
 
 static volatile int running = 1;
 
 /* X11 globals */
 static Display *display;
 static Window root;
 static XImage *ximage;
 static XShmSegmentInfo shminfo;
 static int screen_w, screen_h;
 static int use_shm = 0;
 
 /* ================= TIME ================= */
 
 static double now_sec(void) {
     struct timeval tv;
     gettimeofday(&tv, NULL);
     return tv.tv_sec + tv.tv_usec / 1e6;
 }
 
 /* ================= SIGNAL ================= */
 
 static void on_signal(int sig) {
     running = 0;
 }
 
 /* ================= X11 ================= */
 
 static int init_x11(void) {
     display = XOpenDisplay(NULL);
     if (!display) return 0;
 
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
 
         shminfo.shmid = shmget(
             IPC_PRIVATE,
             ximage->bytes_per_line * ximage->height,
             IPC_CREAT | 0777
         );
 
         shminfo.shmaddr = ximage->data = shmat(shminfo.shmid, 0, 0);
         shminfo.readOnly = False;
         XShmAttach(display, &shminfo);
     } else {
         use_shm = 0;
         ximage = NULL;
     }
 
     printf("X11: %dx%d | XShm: %s\n",
            screen_w, screen_h,
            use_shm ? "ON" : "OFF");
     return 1;
 }
 
 static void cleanup_x11(void) {
     if (use_shm) {
         XShmDetach(display, &shminfo);
         shmdt(shminfo.shmaddr);
         shmctl(shminfo.shmid, IPC_RMID, 0);
         XDestroyImage(ximage);
     }
     XCloseDisplay(display);
 }
 
 /* ================= CAPTURE ================= */
 
 static void capture_and_convert(unsigned char *dst) {
     if (use_shm) {
         XShmGetImage(display, root, ximage, 0, 0, AllPlanes);
     } else {
         ximage = XGetImage(display, root, 0, 0,
                            screen_w, screen_h,
                            AllPlanes, ZPixmap);
     }
 
     unsigned char *src = (unsigned char *)ximage->data;
     int src_stride = ximage->bytes_per_line;
 
     double sx = (double)ximage->width / PROJECTOR_WIDTH;
     double sy = (double)ximage->height / PROJECTOR_HEIGHT;
 
     for (int y = 0; y < PROJECTOR_HEIGHT; y++) {
         int syy = (int)(y * sy);
         unsigned char *src_row = src + syy * src_stride;
         unsigned char *dst_row = dst + y * STRIDE_BYTES_PER_LINE;
 
         for (int x = 0; x < PROJECTOR_WIDTH; x++) {
             int sxx = (int)(x * sx);
             unsigned char *p = src_row + sxx * 4;
             dst_row[x*3+0] = p[0]; // B
             dst_row[x*3+1] = p[1]; // G
             dst_row[x*3+2] = p[2]; // R
         }
     }
 
     if (!use_shm) {
         XDestroyImage(ximage);
     }
 }
 
 /* ================= FILE SWAP ================= */
 
 static void write_frame_atomic(
     const char *tmp,
     const char *final,
     unsigned char *buf
 ) {
     int fd = open(tmp, O_WRONLY | O_CREAT | O_TRUNC, 0644);
     write(fd, buf, TOTAL_FILE_SIZE);
     fsync(fd);
     close(fd);
     rename(tmp, final);   // ATOMIC SWAP
 }
 
 /* ================= MAIN ================= */
 
 int main(int argc, char **argv) {
     if (argc != 3 || strcmp(argv[2], "screen") != 0) {
         printf("Usage: %s <fps> screen\n", argv[0]);
         return 1;
     }
 
     double fps = atof(argv[1]);
     double interval = 1.0 / fps;
 
     unsigned char *buffer =
         calloc(TOTAL_FILE_SIZE, 1);
 
     signal(SIGINT, on_signal);
     signal(SIGTERM, on_signal);
 
     if (!init_x11()) return 1;
 
     int flip = 0;
     double start = now_sec();
     int frames = 0;
 
     while (running) {
         double t0 = now_sec();
 
         capture_and_convert(buffer);
 
         if (flip) {
             write_frame_atomic(FILE_A, FILE_ACTIVE, buffer);
         } else {
             write_frame_atomic(FILE_B, FILE_ACTIVE, buffer);
         }
         flip = !flip;
 
         frames++;
         if (frames % 30 == 0) {
             double fps_real = frames / (now_sec() - start);
             printf("FPS: %.1f\n", fps_real);
         }
 
         double dt = now_sec() - t0;
         if (dt < interval)
             usleep((interval - dt) * 1e6);
     }
 
     cleanup_x11();
     free(buffer);
     return 0;
 }