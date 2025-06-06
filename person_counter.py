import cv2
from datetime import datetime
from collections import defaultdict, deque
from ultralytics import YOLO


class PersonCounter:
    """
    Clase para contar personas que pasan hacia la derecha o izquierda usando YOLOv11
    """
    
    def __init__(self, model_path="yolo11n.pt"):
        print("🤖 Cargando modelo YOLOv11...")
        self.model = YOLO(model_path)
        print("✅ Modelo YOLOv11 cargado exitosamente")
        
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
        
    def set_detection_line(self, frame_width, frame_height):
        """
        Establece la línea de detección en el centro vertical de la imagen
        """
        self.detection_line = frame_width // 2
        print(f"📏 Línea de detección establecida en x={self.detection_line}")
    
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
        # Detectar y trackear objetos
        results = self.model.track(frame, persist=True, classes=[0])  # Solo personas (clase 0)
        
        if results[0].boxes is not None and results[0].boxes.id is not None:
            # Obtener detecciones
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()
            
            # Establecer línea de detección si no existe
            if self.detection_line is None:
                h, w = frame.shape[:2]
                self.set_detection_line(w, h)
            
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
        
        return results[0]
    
    def draw_annotations(self, frame, results):
        """
        Dibuja las anotaciones en el frame
        """
        annotated_frame = results.plot()
        
        # Dibujar línea de detección
        if self.detection_line:
            h, w = frame.shape[:2]
            cv2.line(annotated_frame, 
                    (self.detection_line, 0), 
                    (self.detection_line, h), 
                    (0, 255, 255), 3)  # Línea amarilla
            
            # Dibujar área de detección
            cv2.line(annotated_frame, 
                    (self.detection_line - self.line_margin, 0), 
                    (self.detection_line - self.line_margin, h), 
                    (0, 255, 255), 1)
            cv2.line(annotated_frame, 
                    (self.detection_line + self.line_margin, 0), 
                    (self.detection_line + self.line_margin, h), 
                    (0, 255, 255), 1)
        
        # Dibujar contadores
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        thickness = 2
        
        # Contador derecha
        text_right = f"DERECHA: {self.count_right}"
        cv2.putText(annotated_frame, text_right, (50, 50), 
                   font, font_scale, (0, 255, 0), thickness)
        
        # Contador izquierda
        text_left = f"IZQUIERDA: {self.count_left}"
        cv2.putText(annotated_frame, text_left, (50, 100), 
                   font, font_scale, (255, 0, 0), thickness)
        
        # Total
        total = self.count_right + self.count_left
        text_total = f"TOTAL: {total}"
        cv2.putText(annotated_frame, text_total, (50, 150), 
                   font, font_scale, (255, 255, 255), thickness)
        
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
            "timestamp": datetime.now().isoformat()
        }
