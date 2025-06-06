# Configuración del Sistema de Conteo de Personas - CORREGIDA
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
# CONFIGURACIÓN DE LÍNEA - BASADA EN DATOS REALES
# =====================================================================
# Datos observados: Personas en Y=140-208 (centro ≈ Y=174)
# =====================================================================

LINE_ORIENTATION = "horizontal"
DETECTION_LINE_Y = 174          # CENTRO del rango observado (140+208)/2
DETECTION_LINE_X = None
DETECTION_LINE_RATIO = None
LINE_MARGIN = 10               # Zona: 149-199 (cubre todo el rango)
COUNTING_MODE = "entrance_exit"
ENTRANCE_DIRECTION = "positive" # Las personas van de 140→208 (aumentando Y)

# =====================================================================
# CÁLCULO DE LA LÍNEA:
# =====================================================================
# Rango observado: Y=140 a Y=208
# Centro: (140 + 208) / 2 = 174
# Margen: 25 píxeles
# Zona de detección: 149 ← 174 → 199
# Esto cubre perfectamente el rango 140-208
# =====================================================================

# =====================================================================
# DIRECCIÓN SEMÁNTICA:
# =====================================================================
# ENTRANCE_DIRECTION = "positive" porque:
# - Las personas van de Y=140 → Y=208 (aumentando Y)
# - En línea horizontal, "positive" = hacia ABAJO
# - Por tanto: ir hacia ABAJO = ENTRADA
# =====================================================================