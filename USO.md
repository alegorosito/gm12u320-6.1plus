# Guía de Uso - show_image.py

Script simplificado para mostrar contenido en el proyector GM12U320.

## Opciones Disponibles

### 1. Patrón de Prueba (Por Defecto)
```bash
python3 show_image.py
```
- Muestra un patrón de prueba animado
- FPS por defecto: 10
- **NO MODIFICAR** - Esta es la opción por defecto

### 2. Patrón de Prueba con FPS Personalizado
```bash
python3 show_image.py 24
python3 show_image.py 30
```
- Muestra el patrón de prueba a la velocidad especificada
- Útil para probar diferentes velocidades de actualización

### 3. Mostrar Imagen
```bash
python3 show_image.py imagen.jpg
python3 show_image.py foto.png
```
- Muestra una imagen estática
- Formatos soportados: JPG, PNG, BMP, etc. (cualquier formato que PIL soporte)
- La imagen se redimensiona automáticamente a 800x600

### 4. Reproducir Video
```bash
python3 show_image.py video.mp4
python3 show_image.py pelicula.avi
```
- Reproduce un video frame por frame
- Formatos soportados: MP4, AVI, MOV, MKV, WEBM, etc.
- Usa el FPS original del video
- Se reinicia automáticamente al finalizar
- **Requiere OpenCV**: `pip install opencv-python`

### 5. Capturar Pantalla Principal
```bash
python3 show_image.py screen
```
- Captura la pantalla principal en tiempo real
- Actualiza continuamente a 10 FPS (por defecto)
- Útil para espejar tu escritorio al proyector

## Ejemplos de Uso

```bash
# Prueba básica (patrón de prueba)
python3 show_image.py

# Prueba con diferentes FPS
python3 show_image.py 15
python3 show_image.py 24
python3 show_image.py 30

# Mostrar una imagen
python3 show_image.py mi_foto.jpg

# Reproducir un video
python3 show_image.py mi_video.mp4

# Capturar pantalla principal
python3 show_image.py screen
```

## Notas

- Presiona **Ctrl+C** para detener en cualquier momento
- El script muestra estadísticas cada 10 frames
- La resolución por defecto es 800x600
- Para video, asegúrate de tener OpenCV instalado

