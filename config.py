# Configuración del Sistema de Conteo de Personas - CON FRAME SKIPPING DINÁMICO
# ================================================================

# URL del stream RTSP
RTSP_URL = "rtsp://admin:usuario1234@192.168.18.13:554/Streaming/channels/101?tcp"

# Parámetros de captura
VIDEO_DURATION_SECONDS = 15
MAX_VIDEOS = 5000000
PROCESS_VIDEOS = True
SHOW_LIVE = True

# Parámetros del modelo YOLO
YOLO_MODEL_PATH = "yolo11n.pt"
TARGET_WIDTH = 640
ROTATION_ANGLE = 180

# Directorios
VIDEOS_OUTPUT_DIR = "videos"
STATS_OUTPUT_DIR = "stats"

# Parámetros de detección
DETECTION_CONFIDENCE_THRESHOLD = 0.3
DIRECTION_THRESHOLD = 10        # MUY REDUCIDO - solo 10 píxeles
TRACK_HISTORY_SIZE = 30

# =====================================================================
# CONFIGURACIÓN DE FRAME SKIPPING DINÁMICO
# =====================================================================
# Optimización de rendimiento: saltar frames cuando no hay actividad
# =====================================================================

# Frame skipping por defecto (siempre activo)
DEFAULT_FRAME_SKIP = 1          # Saltar 1 frame por defecto (procesar 1 de cada 2)
# Frame skipping cuando no hay personas detectadas
NO_DETECTION_FRAME_SKIP = 1     # Saltar 5 frames cuando no hay detecciones (procesar 1 de cada 6)
# Número de frames consecutivos sin detección para activar modo "sin personas"
NO_DETECTION_THRESHOLD = 10     # Después de 10 frames sin detecciones, usar skip de 5
# Número de frames con detecciones para volver al modo normal
DETECTION_RECOVERY_THRESHOLD = 3  # Después de 3 frames con detecciones, volver a skip de 1
# Habilitar/deshabilitar frame skipping
ENABLE_FRAME_SKIPPING = True    # True para activar, False para procesar todos los frames
# Mostrar información de frame skipping en consola
SHOW_FRAME_SKIP_INFO = True     # True para ver logs del frame skipping




LINE_ORIENTATION = "horizontal"
DETECTION_LINE_Y = 174          # CENTRO del rango observado (140+208)/2
DETECTION_LINE_X = None
DETECTION_LINE_RATIO = None
LINE_MARGIN = 10               # Zona: 149-199 (cubre todo el rango)
COUNTING_MODE = "entrance_exit"
ENTRANCE_DIRECTION = "positive" # Las personas van de 140→208 (aumentando Y)
