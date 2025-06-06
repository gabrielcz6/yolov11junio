import cv2
from datetime import datetime
from collections import defaultdict, deque
from ultralytics import YOLO


class PersonCounter:
    """
    Clase para contar personas que pasan hacia la derecha o izquierda usando YOLOv11
    """
    
    def __init__(self, model_path="yolo11n.pt", target_width=640, rotation_angle=0):
        print("🤖 Cargando modelo YOLOv11...")
        self.model = YOLO(model_path)
        print("✅ Modelo YOLOv11 cargado exitosamente")
        
        # Configuración de resize
        self.target_width = target_width
        self.target_height = None  # Se calculará automáticamente manteniendo aspecto
        self.scale_factor = 1.0
        
        # Configuración de rotación
        self.rotation_angle = rotation_angle
        self.rotation_code = self._get_rotation_code(rotation_angle)
        if rotation_angle != 0:
            print(f"🔄 Rotación configurada: {rotation_angle}°")
        
        # Configuración del conteo
        self.tracks = defaultdict(lambda: deque(maxlen=30))  # Histórico de posiciones
        self.counted_ids = set()  # IDs ya contados
        self.direction_threshold = 50  # Píxeles mínimos de movimiento para contar
        
        # Contadores
        self.count_right = 0  # Personas que van hacia la derecha
        self.count_left = 0   # Personas que van hacia la izquierda
        
        # Línea de detección (centro de la imagen por defecto)
        self.detection_line = None
        self.line_margin = 30  # Margen de la línea
        
    def _get_rotation_code(self, angle):
        """
        Convierte el ángulo de rotación a código OpenCV
        """
        rotation_codes = {
            0: None,
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE
        }
        
        if angle not in rotation_codes:
            print(f"⚠️ Ángulo de rotación no válido: {angle}°. Usando 0°")
            return None
        
        return rotation_codes[angle]
    
    def rotate_frame(self, frame):
        """
        Rota el frame según el ángulo configurado
        """
        if self.rotation_code is None:
            return frame
        
        return cv2.rotate(frame, self.rotation_code)
        
    def resize_frame(self, frame):
        """
        Redimensiona el frame a 640p manteniendo la relación de aspecto
        """
        h, w = frame.shape[:2]
        
        # Calcular nueva altura manteniendo aspecto
        if self.target_height is None:
            aspect_ratio = h / w
            self.target_height = int(self.target_width * aspect_ratio)
            self.scale_factor = self.target_width / w
            rotation_info = f" (rotado {self.rotation_angle}°)" if self.rotation_angle != 0 else ""
            print(f"📐 Redimensionando de {w}x{h} a {self.target_width}x{self.target_height}{rotation_info}")
        
        # Redimensionar frame
        resized_frame = cv2.resize(frame, (self.target_width, self.target_height))
        return resized_frame
        
    def set_detection_line(self, frame_width, frame_height):
        """
        Establece la línea de detección en el centro vertical de la imagen
        """
        self.detection_line = frame_width // 2
        print(f"📏 Línea de detección establecida en x={self.detection_line} (ancho: {frame_width})")
    
    def get_direction(self, track_id, current_x):
        """
        Determina la dirección del movimiento basado en el histórico de posiciones
        """
        if len(self.tracks[track_id]) < 2:
            return None
        
        # Obtener posiciones anteriores
        positions = list(self.tracks[track_id])
        start_x = positions[0]
        end_x = positions[-1]
        
        movement = end_x - start_x
        
        # Solo contar si el movimiento es significativo
        if abs(movement) < self.direction_threshold:
            return None
        
        return "right" if movement > 0 else "left"
    
    def crossed_line(self, track_id, current_x):
        """
        Verifica si la persona cruzó la línea de detección
        """
        if not self.detection_line or len(self.tracks[track_id]) < 2:
            return False
        
        positions = list(self.tracks[track_id])
        prev_x = positions[-2] if len(positions) >= 2 else positions[-1]
        
        # Verificar si cruzó la línea (con margen)
        line_left = self.detection_line - self.line_margin
        line_right = self.detection_line + self.line_margin
        
        # Cruzó de izquierda a derecha
        if prev_x < line_left and current_x > line_right:
            return True
        
        # Cruzó de derecha a izquierda  
        if prev_x > line_right and current_x < line_left:
            return True
        
        return False
    
    def process_frame(self, frame):
        """
        Procesa un frame para detectar y contar personas
        """
        # Rotar frame si es necesario
        rotated_frame = self.rotate_frame(frame)
        
        # Redimensionar frame a 640p
        resized_frame = self.resize_frame(rotated_frame)
        h, w = resized_frame.shape[:2]
        
        # Establecer línea de detección si no existe
        if self.detection_line is None:
            self.set_detection_line(w, h)
        
        # Detectar y trackear objetos en el frame redimensionado
        results = self.model.track(resized_frame, persist=True, classes=[0])  # Solo personas (clase 0)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            # Obtener detecciones
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()
            
            # Procesar cada detección
            for box, track_id, conf in zip(boxes, track_ids, confidences):
                if conf < 0.5:  # Filtrar detecciones con baja confianza
                    continue
                
                x1, y1, x2, y2 = box
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                
                # Actualizar histórico de posiciones
                self.tracks[track_id].append(center_x)
                
                # Verificar si cruzó la línea y no ha sido contado
                if track_id not in self.counted_ids and self.crossed_line(track_id, center_x):
                    direction = self.get_direction(track_id, center_x)
                    
                    if direction == "right":
                        self.count_right += 1
                        self.counted_ids.add(track_id)
                        print(f"➡️  Persona #{track_id} fue hacia la DERECHA (Total derecha: {self.count_right})")
                    elif direction == "left":
                        self.count_left += 1
                        self.counted_ids.add(track_id)
                        print(f"⬅️  Persona #{track_id} fue hacia la IZQUIERDA (Total izquierda: {self.count_left})")
        
        return results[0], resized_frame
    
    def draw_annotations(self, frame, results):
        """
        Dibuja las anotaciones en el frame redimensionado
        """
        # El frame ya viene redimensionado del process_frame
        annotated_frame = results.plot()
        h, w = annotated_frame.shape[:2]
        
        # Dibujar línea de detección PRINCIPAL (más gruesa y visible)
        if self.detection_line:
            # Línea principal amarilla gruesa
            cv2.line(annotated_frame, 
                    (self.detection_line, 0), 
                    (self.detection_line, h), 
                    (0, 255, 255), 5)  # Línea amarilla MÁS GRUESA
            
            # Líneas de área de detección (más finas)
            cv2.line(annotated_frame, 
                    (self.detection_line - self.line_margin, 0), 
                    (self.detection_line - self.line_margin, h), 
                    (0, 255, 255), 2)
            cv2.line(annotated_frame, 
                    (self.detection_line + self.line_margin, 0), 
                    (self.detection_line + self.line_margin, h), 
                    (0, 255, 255), 2)
            
            # Agregar texto de la línea
            cv2.putText(annotated_frame, "LINEA DETECCION", 
                       (self.detection_line - 80, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Dibujar contadores con fondo para mejor visibilidad
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        
        # Función para dibujar texto con fondo
        def draw_text_with_background(img, text, position, font, scale, color, thickness, bg_color):
            # Obtener tamaño del texto
            (text_width, text_height), baseline = cv2.getTextSize(text, font, scale, thickness)
            
            # Dibujar rectángulo de fondo
            cv2.rectangle(img, 
                         (position[0], position[1] - text_height - 10),
                         (position[0] + text_width + 10, position[1] + baseline),
                         bg_color, -1)
            
            # Dibujar texto
            cv2.putText(img, text, position, font, scale, color, thickness)
        
        # Contador derecha (verde)
        text_right = f"DERECHA: {self.count_right}"
        draw_text_with_background(annotated_frame, text_right, (20, 50), 
                                font, font_scale, (0, 255, 0), thickness, (0, 0, 0))
        
        # Contador izquierda (rojo)
        text_left = f"IZQUIERDA: {self.count_left}"
        draw_text_with_background(annotated_frame, text_left, (20, 90), 
                                font, font_scale, (0, 0, 255), thickness, (0, 0, 0))
        
        # Total (blanco)
        total = self.count_right + self.count_left
        text_total = f"TOTAL: {total}"
        draw_text_with_background(annotated_frame, text_total, (20, 130), 
                                font, font_scale, (255, 255, 255), thickness, (0, 0, 0))
        
        # Información de resolución y rotación
        text_resolution = f"Resolucion: {w}x{h}"
        if self.rotation_angle != 0:
            text_resolution += f" | Rotacion: {self.rotation_angle}°"
        draw_text_with_background(annotated_frame, text_resolution, (20, h - 30), 
                                font, 0.5, (255, 255, 255), 1, (0, 0, 0))
        
        return annotated_frame
    
    def reset_counters(self):
        """
        Reinicia los contadores
        """
        self.count_right = 0
        self.count_left = 0
        self.counted_ids.clear()
        self.tracks.clear()
        print("🔄 Contadores reiniciados")
    
    def get_stats(self):
        """
        Retorna estadísticas del conteo
        """
        return {
            "derecha": self.count_right,
            "izquierda": self.count_left,
            "total": self.count_right + self.count_left,
            "timestamp": datetime.now().isoformat(),
            "resolution": f"{self.target_width}x{self.target_height}" if self.target_height else "original",
            "rotation_angle": self.rotation_angle
        }