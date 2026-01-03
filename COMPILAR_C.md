# Compilación de show_image_c

Programa optimizado en C para captura de pantalla en el proyector GM12U320.

## Requisitos

- Compilador GCC
- Librerías de desarrollo X11:
  ```bash
  sudo apt install libx11-dev libxext-dev
  ```

## Compilación

### Opción 1: Usando el Makefile
```bash
make -f Makefile.show_image
```

### Opción 2: Compilación manual
```bash
gcc -O3 -o show_image_c show_image_c.c -lX11 -lXext -lm
```

## Uso

```bash
./show_image_c <fps> screen
```

### Ejemplos

```bash
# Captura a 24 FPS
./show_image_c 24 screen

# Captura a 30 FPS
./show_image_c 30 screen

# Captura a 10 FPS (por defecto)
./show_image_c 10 screen
```

## Ventajas sobre la versión Python

- **Mayor rendimiento**: Compilado nativo, sin interpretación
- **Menor latencia**: Acceso directo a memoria
- **XShm**: Usa Shared Memory de X11 para captura ultra-rápida
- **Menor uso de CPU**: Procesamiento optimizado
- **Mejor para altos FPS**: Ideal para 24+ FPS

## Instalación (opcional)

```bash
make -f Makefile.show_image install
```

Esto instalará el programa en `/usr/local/bin/show_image_c`

## Notas

- El programa requiere acceso al servidor X11
- Funciona mejor sin `sudo` (permisos X11)
- Presiona Ctrl+C para detener
- Muestra estadísticas cada 10 frames

