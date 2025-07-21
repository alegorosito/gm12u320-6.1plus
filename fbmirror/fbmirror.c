#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <linux/fb.h>

#define FB_PRIMARY "/dev/fb0"
#define FB_PROJECTOR "/dev/fb1"

int main() {
    int fb0_fd, fb1_fd;
    struct fb_var_screeninfo vinfo0, vinfo1;
    struct fb_fix_screeninfo finfo0, finfo1;
    long screensize0, screensize1;
    char *fbp0, *fbp1;

    fb0_fd = open(FB_PRIMARY, O_RDONLY);
    if (fb0_fd == -1) {
        perror("Error abriendo framebuffer principal");
        exit(1);
    }

    fb1_fd = open(FB_PROJECTOR, O_RDWR);
    if (fb1_fd == -1) {
        perror("Error abriendo framebuffer proyector");
        close(fb0_fd);
        exit(1);
    }

    ioctl(fb0_fd, FBIOGET_FSCREENINFO, &finfo0);
    ioctl(fb0_fd, FBIOGET_VSCREENINFO, &vinfo0);

    ioctl(fb1_fd, FBIOGET_FSCREENINFO, &finfo1);
    ioctl(fb1_fd, FBIOGET_VSCREENINFO, &vinfo1);

    screensize0 = vinfo0.yres_virtual * finfo0.line_length;
    screensize1 = vinfo1.yres_virtual * finfo1.line_length;

    if (screensize0 > screensize1) {
        fprintf(stderr, "Error: el framebuffer del proyector es más pequeño que el principal\n");
        close(fb0_fd);
        close(fb1_fd);
        exit(1);
    }

    fbp0 = mmap(0, screensize0, PROT_READ, MAP_SHARED, fb0_fd, 0);
    if (fbp0 == MAP_FAILED) {
        perror("Error mapeando fb0");
        exit(1);
    }

    fbp1 = mmap(0, screensize1, PROT_WRITE, MAP_SHARED, fb1_fd, 0);
    if (fbp1 == MAP_FAILED) {
        perror("Error mapeando fb1");
        exit(1);
    }

    printf("Copiando framebuffer de %s a %s… presiona Ctrl+C para salir\n", FB_PRIMARY, FB_PROJECTOR);

    while (1) {
        memcpy(fbp1, fbp0, screensize0);
        usleep(16000); // ~60fps
    }

    munmap(fbp0, screensize0);
    munmap(fbp1, screensize1);
    close(fb0_fd);
    close(fb1_fd);

    return 0;
}
