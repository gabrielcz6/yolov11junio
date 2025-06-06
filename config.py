# Configuración del sistema

# URL del stream RTSP
RTSP_URL = "rtsp://admin:usuario1234@192.168.18.13:554/Streaming/channels/101?tcp"

# Parámetros de captura
VIDEO_DURATION_SECONDS = 15  # Duración de cada video en segundos
MAX_VIDEOS = 50  # Máximo número de videos a capturar
PROCESS_VIDEOS = True  # Si procesar videos automáticamente
SHOW_PREVIEW = False  # Si mostrar preview durante procesamiento

# Parámetros del modelo YOLO
YOLO_MODEL_PATH = "yolo11n.pt"  # Ruta del modelo YOLO

# Directorios de salida
VIDEOS_OUTPUT_DIR = "videos"  # Directorio para videos capturados
PROCESSED_OUTPUT_DIR = "processed_videos"  # Directorio para videos procesados

# Parámetros de detección
DETECTION_CONFIDENCE_THRESHOLD = 0.5  # Umbral de confianza para detecciones
DIRECTION_THRESHOLD = 50  # Píxeles mínimos de movimiento para contar
LINE_MARGIN = 30  # Margen de la línea de detección

# Configuración de tracking
TRACK_HISTORY_SIZE = 30  # Número de posiciones históricas a mantener
