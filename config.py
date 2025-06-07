# Configuración del Sistema de Conteo de Personas - CON FRAME SKIPPING CORREGIDO
# ================================================================

# URL del stream RTSP
RTSP_URL = "rtsp://admin:usuario1234@192.168.18.13:554/Streaming/channels/101?tcp"

# Parámetros de captura
VIDEO_DURATION_SECONDS = 300# Duración del video a capturar
MAX_VIDEOS = 9999999
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
DETECTION_CONFIDENCE_THRESHOLD = 0.25
DIRECTION_THRESHOLD = 10        # MUY REDUCIDO - solo 10 píxeles
TRACK_HISTORY_SIZE = 30

# =====================================================================
# CONFIGURACIÓN DE FRAME SKIPPING DINÁMICO - VERSIÓN CORREGIDA
# =====================================================================
# Optimización de rendimiento: saltar frames cuando no hay actividad
# VALORES CORREGIDOS para evitar frames varados
# =====================================================================

# HABILITAR/DESHABILITAR FRAME SKIPPING
ENABLE_FRAME_SKIPPING = True    # True para activar, False para procesar todos los frames

# CONFIGURACIÓN CONSERVADORA para evitar problemas:
DEFAULT_FRAME_SKIP = 0          # CORREGIDO: 0 = procesar todos los frames en modo normal
NO_DETECTION_FRAME_SKIP = 3     # CORREGIDO: Skip moderado cuando no hay personas (procesar 1 de cada 3)

# THRESHOLDS más conservadores:
NO_DETECTION_THRESHOLD = 45     # CORREGIDO: Esperar más frames antes de cambiar modo
DETECTION_RECOVERY_THRESHOLD = 1  # CORREGIDO: Más frames para confirmar detecciones

# DEBUG Y LOGS
SHOW_FRAME_SKIP_INFO = True     # True para ver logs del frame skipping

# =====================================================================
# CONFIGURACIÓN ALTERNATIVA PARA MÁXIMO RENDIMIENTO (comentada)
# =====================================================================
# Si necesitas máximo rendimiento, descomenta estas líneas:
# DEFAULT_FRAME_SKIP = 1          # Skip normal más agresivo
# NO_DETECTION_FRAME_SKIP = 4     # Skip alto sin detecciones
# NO_DETECTION_THRESHOLD = 8      # Cambio más rápido
# DETECTION_RECOVERY_THRESHOLD = 2  # Recuperación más rápida

# =====================================================================
# CONFIGURACIÓN SIN FRAME SKIPPING (para debugging)
# =====================================================================
# Si tienes problemas, descomenta esta línea para deshabilitar completamente:
# ENABLE_FRAME_SKIPPING = False

# =====================================================================
# CONFIGURACIÓN DE LÍNEA DE DETECCIÓN
# =====================================================================
LINE_ORIENTATION = "horizontal"
DETECTION_LINE_Y = 174          # CENTRO del rango observado (140+208)/2
DETECTION_LINE_X = None
DETECTION_LINE_RATIO = None
LINE_MARGIN = 10               # Zona: 149-199 (cubre todo el rango)
COUNTING_MODE = "entrance_exit"
ENTRANCE_DIRECTION = "positive" # Las personas van de 140→208 (aumentando Y)