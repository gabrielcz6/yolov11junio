# Configuración del Sistema de Conteo de Personas con YOLOv11
# ================================================================

# URL del stream RTSP
RTSP_URL = "rtsp://admin:usuario1234@192.168.18.13:554/Streaming/channels/101?tcp"

# Parámetros de captura
VIDEO_DURATION_SECONDS = 15  # Duración de cada video en segundos
MAX_VIDEOS = 50  # Máximo número de videos a capturar
PROCESS_VIDEOS = True  # Si procesar videos automáticamente
SHOW_LIVE = True  # Si mostrar frames procesados en vivo

# Parámetros del modelo YOLO
YOLO_MODEL_PATH = "yolo11n.pt"  # Ruta del modelo YOLO
TARGET_WIDTH = 640  # Ancho objetivo para redimensionar (640p)
ROTATION_ANGLE = 180  # Ángulo de rotación: 0, 90, 180, 270 grados

# Directorios
VIDEOS_OUTPUT_DIR = "videos"  # Directorio para videos capturados (sin procesar)
STATS_OUTPUT_DIR = "stats"  # Directorio para estadísticas JSON

# Parámetros de detección
DETECTION_CONFIDENCE_THRESHOLD = 0.25  # Umbral de confianza para detecciones
DIRECTION_THRESHOLD = 50  # Píxeles mínimos de movimiento para contar
TRACK_HISTORY_SIZE = 30  # Número de posiciones históricas a mantener

# =====================================================================
# CONFIGURACIÓN DE LÍNEA DE DETECCIÓN
# =====================================================================
# 🎯 EJECUTA: python line_calibrator.py para calibrar interactivamente
# =====================================================================

# Orientación de la línea de detección:
# "vertical"   = Línea vertical, detecta movimiento HORIZONTAL (←→)
# "horizontal" = Línea horizontal, detecta movimiento VERTICAL (↑↓)
# Cambiar estas líneas:


LINE_ORIENTATION = "horizontal"     # Era "vertical" 
DETECTION_LINE_Y = 238              # Nueva línea
DETECTION_LINE_X = None             # No se usa para horizontal
DETECTION_LINE_RATIO = None         # Opcional
LINE_MARGIN = 30                    # Mantener o ajustar
COUNTING_MODE = "entrance_exit"     # Tu elección
ENTRANCE_DIRECTION = "positive"     # Ajustar según tu escenario



# =====================================================================
# EJEMPLOS DE CONFIGURACIÓN SEGÚN TU ESCENARIO
# =====================================================================

# 📋 ESCENARIO 1: Puerta horizontal (tradicional)
# ┌─────────────────────────────────────┐
# │ 🏢 INTERIOR                         │
# ├═════════════════════════════════════┤ ← Línea VERTICAL
# │ 🛣️ EXTERIOR                         │
# └─────────────────────────────────────┘
# Configuración:
# LINE_ORIENTATION = "vertical"
# ENTRANCE_DIRECTION = "positive" (si derecha = entrada)

# 📋 ESCENARIO 2: Puerta vertical
# ┌─────┬─────┐
# │ 🏢  │ 🛣️  │
# │     ║     │ ← Línea HORIZONTAL
# │     ║     │
# │     ║     │
# └─────┴─────┘
# Configuración:
# LINE_ORIENTATION = "horizontal"
# ENTRANCE_DIRECTION = "positive" (si abajo = entrada)

# 📋 ESCENARIO 3: Pasillo con movimiento bidireccional
# LINE_ORIENTATION = "vertical" o "horizontal" según orientación
# COUNTING_MODE = "directional" para ver ambas direcciones

# =====================================================================
# INSTRUCCIONES DE CALIBRACIÓN
# =====================================================================
# 1. Ejecuta: python line_calibrator.py
# 2. Usa TAB para alternar entre línea vertical/horizontal
# 3. Dibuja la línea donde quieres detectar el paso
# 4. Ajusta el margen con +/-
# 5. Presiona S para guardar
# 6. Copia los parámetros generados aquí
# 7. Configura ENTRANCE_DIRECTION según tu caso
# =====================================================================

# MAPEO DE DIRECCIONES SEGÚN ORIENTACIÓN:
# ═══════════════════════════════════════
# LÍNEA VERTICAL (detecta movimiento ←→):
#   "positive" = DERECHA
#   "negative" = IZQUIERDA
#
# LÍNEA HORIZONTAL (detecta movimiento ↑↓):
#   "positive" = ABAJO  
#   "negative" = ARRIBA
# ═══════════════════════════════════════

# =====================================================================
# CONFIGURACIÓN AVANZADA
# =====================================================================

# Si ambos DETECTION_LINE_X/Y y DETECTION_LINE_RATIO son None,
# el sistema usará el centro automáticamente

# Para máxima precisión, usa línea calibrada + modo entrance_exit
# Para análisis de flujo, usa modo directional

# El sistema mostrará en pantalla:
# - Línea de detección con área de margen
# - Flechas indicando entrada/salida
# - Contadores según el modo configurado
# - Indicador si la línea está calibrada