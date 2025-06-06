import cv2
import numpy as np
from datetime import datetime
from collections import defaultdict, deque
from ultralytics import YOLO
# Suprimir COMPLETAMENTE el output de YOLO
import io
import sys
from contextlib import redirect_stdout, redirect_stderr

class FlexiblePersonCounter:
    """
    Contador de personas que soporta líneas horizontales y verticales
    Para detectar movimiento en cualquier dirección
    """
    
    def __init__(self, model_path="yolo11n.pt", target_width=640, rotation_angle=0,
                 line_orientation="vertical", detection_line_position=None, 
                 detection_line_ratio=None, line_margin=30,
                 entrance_direction="positive", counting_mode="entrance_exit"):
        
        print("🤖 Cargando modelo YOLOv11...")
        self.model = YOLO(model_path)
        print("✅ Modelo YOLOv11 cargado exitosamente")
        
        # Configuración de resize y rotación
        self.target_width = target_width
        self.target_height = None
        self.scale_factor = 1.0
        self.rotation_angle = rotation_angle
        self.rotation_code = self._get_rotation_code(rotation_angle)
        
        # NUEVA CONFIGURACIÓN: Orientación de línea
        self.line_orientation = line_orientation.lower()  # "vertical" o "horizontal"
        self.detection_line_position = detection_line_position  # Posición fija
        self.detection_line_ratio = detection_line_ratio  # Ratio de posición
        self.line_margin = line_margin
        self.detection_line = None
        
        # Configuración del conteo
        self.tracks = defaultdict(lambda: deque(maxlen=30))
        self.counted_ids = set()
        self.direction_threshold = 50
        
        # Configuración semántica
        self.entrance_direction = entrance_direction.lower()  # "positive" o "negative"
        self.counting_mode = counting_mode.lower()  # "entrance_exit" o "directional"
        
        # Contadores
        if self.counting_mode == "entrance_exit":
            self.count_entrance = 0
            self.count_exit = 0
        else:
            self.count_positive = 0  # Derecha/Abajo
            self.count_negative = 0  # Izquierda/Arriba
        
        # Información de configuración
        self.line_calibrated = detection_line_position is not None or detection_line_ratio is not None
        
        # Mostrar configuración
        print(f"📏 Orientación de línea: {self.line_orientation.upper()}")
        if self.line_orientation == "vertical":
            print("   📐 Detecta movimiento HORIZONTAL (←→)")
            directions = "DERECHA/IZQUIERDA"
        else:
            print("   📐 Detecta movimiento VERTICAL (↑↓)")
            directions = "ABAJO/ARRIBA"
        
        print(f"📊 Modo de conteo: {self.counting_mode.upper()}")
        if self.counting_mode == "entrance_exit":
            print(f"🚪 Dirección de ENTRADA: {self.entrance_direction.upper()}")
            print(f"🚪 Direcciones detectadas: {directions}")
        
        if rotation_angle != 0:
            print(f"🔄 Rotación configurada: {rotation_angle}°")
    
    def _get_rotation_code(self, angle):
        """Convierte el ángulo de rotación a código OpenCV"""
        rotation_codes = {
            0: None,
            90: cv2.ROTATE_90_CLOCKWISE,
            180: cv2.ROTATE_180,
            270: cv2.ROTATE_90_COUNTERCLOCKWISE
        }
        return rotation_codes.get(angle, None)
    
    def rotate_frame(self, frame):
        """Rota el frame según el ángulo configurado"""
        if self.rotation_code is None:
            return frame
        return cv2.rotate(frame, self.rotation_code)
    
    def resize_frame(self, frame):
        """Redimensiona el frame manteniendo la relación de aspecto"""
        h, w = frame.shape[:2]
        
        if self.target_height is None:
            aspect_ratio = h / w
            self.target_height = int(self.target_width * aspect_ratio)
            self.scale_factor = self.target_width / w
            rotation_info = f" (rotado {self.rotation_angle}°)" if self.rotation_angle != 0 else ""
            print(f"📐 Redimensionando de {w}x{h} a {self.target_width}x{self.target_height}{rotation_info}")
        
        return cv2.resize(frame, (self.target_width, self.target_height))
    
    def set_detection_line(self, frame_width, frame_height):
        """Establece la línea de detección según orientación"""
        if self.line_orientation == "vertical":
            # Línea vertical - usa ancho del frame
            reference_dimension = frame_width
            default_position = frame_width // 2
            line_type = "vertical (X)"
        else:
            # Línea horizontal - usa altura del frame
            reference_dimension = frame_height
            default_position = frame_height // 2
            line_type = "horizontal (Y)"
        
        if self.detection_line_position is not None:
            self.detection_line = self.detection_line_position
            print(f"📏 Línea {line_type} fija en {self.detection_line}")
        elif self.detection_line_ratio is not None:
            self.detection_line = int(reference_dimension * self.detection_line_ratio)
            print(f"📏 Línea {line_type} calculada por ratio ({self.detection_line_ratio}) en {self.detection_line}")
        else:
            self.detection_line = default_position
            print(f"📏 Línea {line_type} por defecto (centro) en {self.detection_line}")
        
        # Validar límites
        if self.detection_line < 0:
            self.detection_line = 0
        elif self.detection_line >= reference_dimension:
            self.detection_line = reference_dimension - 1
        
        print(f"📏 Línea de detección establecida: {line_type} = {self.detection_line}")
    
    # DIAGNÓSTICO ESPECÍFICO PARA CONTEO
# Reemplaza los métodos crossed_line y get_direction en flexible_person_counter.py

    def crossed_line(self, track_id, current_pos):
      """Verifica si la persona cruzó la línea - CON DEBUG DETALLADO"""
      if not self.detection_line or len(self.tracks[track_id]) < 2:
          print(f"🔍 ID {track_id}: Sin línea o historial insuficiente")
          return False
      
      positions = list(self.tracks[track_id])
      prev_pos = positions[-2] if len(positions) >= 2 else positions[-1]
      
      line_before = self.detection_line - self.line_margin
      line_after = self.detection_line + self.line_margin
      
      print(f"🎯 ID {track_id} - ANÁLISIS DE CRUCE:")
      print(f"   📍 Posición anterior: {prev_pos}")
      print(f"   📍 Posición actual: {current_pos}")
      print(f"   📏 Zona de detección: {line_before} ← {self.detection_line} → {line_after}")
      print(f"   📐 Orientación: {self.line_orientation}")
      
      # Cruzó en dirección positiva (derecha/abajo)
      crossed_positive = prev_pos < line_before and current_pos > line_after
      # Cruzó en dirección negativa (izquierda/arriba)  
      crossed_negative = prev_pos > line_after and current_pos < line_before
      
      print(f"   🚪 Cruzó hacia POSITIVO ({self.line_orientation}): {crossed_positive}")
      print(f"   🚪 Cruzó hacia NEGATIVO ({self.line_orientation}): {crossed_negative}")
      
      if crossed_positive:
          direction_name = "ABAJO" if self.line_orientation == "horizontal" else "DERECHA"
          print(f"   ✅ ¡CRUCE DETECTADO! Dirección: {direction_name}")
          return True
      elif crossed_negative:
          direction_name = "ARRIBA" if self.line_orientation == "horizontal" else "IZQUIERDA"
          print(f"   ✅ ¡CRUCE DETECTADO! Dirección: {direction_name}")
          return True
      else:
          print(f"   ❌ No hay cruce - persona aún no atravesó completamente")
          # Mostrar análisis detallado
          if prev_pos >= line_before and prev_pos <= line_after:
              print(f"      📍 Anterior DENTRO de zona: {prev_pos}")
          if current_pos >= line_before and current_pos <= line_after:
              print(f"      📍 Actual DENTRO de zona: {current_pos}")
          return False

    def crossed_line(self, track_id, current_pos):
       """Verifica si la persona cruzó la línea - LÓGICA SIMPLIFICADA"""
       if not self.detection_line or len(self.tracks[track_id]) < 5:  # Mínimo 5 puntos
           return False
       
       positions = list(self.tracks[track_id])
       
       # Obtener posiciones de inicio y final del trayecto
       start_pos = positions[0]
       end_pos = positions[-1]
       
       line_before = self.detection_line - self.line_margin
       line_after = self.detection_line + self.line_margin
       
       print(f"🎯 ID {track_id} - NUEVO ANÁLISIS DE CRUCE:")
       print(f"   📍 Posición inicial: {start_pos}")
       print(f"   📍 Posición actual: {end_pos}")
       print(f"   📏 Zona de detección: {line_before} ← {self.detection_line} → {line_after}")
       
       # NUEVA LÓGICA: ¿Cruzó completamente la zona?
       crossed_positive = start_pos < line_before and end_pos > line_after
       crossed_negative = start_pos > line_after and end_pos < line_before
       
       print(f"   🚪 Cruzó COMPLETAMENTE hacia POSITIVO: {crossed_positive}")
       print(f"   🚪 Cruzó COMPLETAMENTE hacia NEGATIVO: {crossed_negative}")
       
       if crossed_positive:
           direction_name = "ABAJO" if self.line_orientation == "horizontal" else "DERECHA"
           print(f"   ✅ ¡CRUCE COMPLETO! Dirección: {direction_name}")
           return True
       elif crossed_negative:
           direction_name = "ARRIBA" if self.line_orientation == "horizontal" else "IZQUIERDA"
           print(f"   ✅ ¡CRUCE COMPLETO! Dirección: {direction_name}")
           return True
       else:
           print(f"   ❌ No hay cruce completo")
           print(f"      📊 Para cruce positivo necesita: start < {line_before} AND end > {line_after}")
           print(f"      📊 Para cruce negativo necesita: start > {line_after} AND end < {line_before}")
           print(f"      📊 Actual: start={start_pos}, end={end_pos}")
           return False
   
# T   AMBIÉN MEJORAR get_direction para que use TODO el trayecto:

    def get_direction(self, track_id, current_pos):
         """Determina la dirección usando TODO el trayecto"""
         if len(self.tracks[track_id]) < 5:
             print(f"🧭 ID {track_id}: Trayecto muy corto para determinar dirección")
             return None
         
         positions = list(self.tracks[track_id])
         start_pos = positions[0]
         end_pos = positions[-1]
         
         # Calcular movimiento total
         total_movement = end_pos - start_pos
         
         print(f"🧭 ID {track_id} - ANÁLISIS DE DIRECCIÓN TOTAL:")
         print(f"   📍 Posición inicial: {start_pos}")
         print(f"   📍 Posición final: {end_pos}")
         print(f"   📏 Movimiento TOTAL: {total_movement} píxeles")
         print(f"   📊 Threshold requerido: {self.direction_threshold} píxeles")
         
         if abs(total_movement) < self.direction_threshold:
             print(f"   ❌ Movimiento total insuficiente: {abs(total_movement)} < {self.direction_threshold}")
             return None
         
         direction = "positive" if total_movement > 0 else "negative"
         
         if self.line_orientation == "horizontal":
             direction_name = "ABAJO" if direction == "positive" else "ARRIBA"
         else:
             direction_name = "DERECHA" if direction == "positive" else "IZQUIERDA"
         
         print(f"   ✅ Dirección: {direction} = {direction_name}")
         print(f"   📊 Movimiento total: {abs(total_movement)} píxeles")
         
         return direction
       
    def process_frame(self, frame):
       """Procesa un frame para detectar y contar personas - SIN SPAM"""
       rotated_frame = self.rotate_frame(frame)
       resized_frame = self.resize_frame(rotated_frame)
       h, w = resized_frame.shape[:2]
       
       if self.detection_line is None:
           self.set_detection_line(w, h)
       
       
       
       f = io.StringIO()
       with redirect_stdout(f), redirect_stderr(f):
           results = self.model.track(resized_frame, persist=True, classes=[0], conf=0.5, verbose=False)
       
       # SOLO mostrar info si hay detecciones válidas
       if results[0].boxes is not None and results[0].boxes.id is not None:
           boxes = results[0].boxes.xyxy.cpu().numpy()
           track_ids = results[0].boxes.id.cpu().numpy().astype(int)
           confidences = results[0].boxes.conf.cpu().numpy()
           
           valid_detections = sum(1 for conf in confidences if conf >= 0.5)
           if valid_detections > 0:
               print(f"👥 {valid_detections} personas detectadas")
           
           for box, track_id, conf in zip(boxes, track_ids, confidences):
               if conf < 0.5:
                   continue
               
               x1, y1, x2, y2 = box
               center_x = int((x1 + x2) / 2)
               center_y = int((y1 + y2) / 2)
               
               if self.line_orientation == "vertical":
                   tracking_coord = center_x
                   coord_name = "X"
                   movement_axis = "horizontal"
               else:
                   tracking_coord = center_y
                   coord_name = "Y"
                   movement_axis = "vertical"
               
               print(f"👤 ID {track_id}: {coord_name}={tracking_coord}, conf={conf:.2f}")
               
               self.tracks[track_id].append(tracking_coord)
               
               if track_id not in self.counted_ids and self.crossed_line(track_id, tracking_coord):
                   direction = self.get_direction(track_id, tracking_coord)
                   
                   if direction:
                       self.counted_ids.add(track_id)
                       
                       if self.counting_mode == "entrance_exit":
                           if direction == self.entrance_direction:
                               self.count_entrance += 1
                               arrow = "⬇️" if movement_axis == "vertical" else "➡️"
                               print(f"🚪{arrow} Persona #{track_id} ENTRÓ (Total entradas: {self.count_entrance})")
                           else:
                               self.count_exit += 1
                               arrow = "⬆️" if movement_axis == "vertical" else "⬅️"
                               print(f"🚪{arrow} Persona #{track_id} SALIÓ (Total salidas: {self.count_exit})")
                       else:
                           if direction == "positive":
                               self.count_positive += 1
                               arrow = "⬇️" if movement_axis == "vertical" else "➡️"
                               direction_name = "ABAJO" if movement_axis == "vertical" else "DERECHA"
                               print(f"{arrow} Persona #{track_id} fue hacia {direction_name} (Total: {self.count_positive})")
                           else:
                               self.count_negative += 1
                               arrow = "⬆️" if movement_axis == "vertical" else "⬅️"
                               direction_name = "ARRIBA" if movement_axis == "vertical" else "IZQUIERDA"
                               print(f"{arrow} Persona #{track_id} fue hacia {direction_name} (Total: {self.count_negative})")
       
       # NO mostrar nada si no hay detecciones - elimina el spam
       
       return results[0], resized_frame
    
    def draw_annotations(self, frame, results):
        """Dibuja las anotaciones en el frame"""
        annotated_frame = results.plot()
        h, w = annotated_frame.shape[:2]
        
        if self.detection_line:
            # Dibujar línea según orientación
            if self.line_orientation == "vertical":
                # Línea vertical
                cv2.line(annotated_frame, 
                        (self.detection_line, 0), 
                        (self.detection_line, h), 
                        (0, 255, 255), 5)
                
                # Líneas de margen
                cv2.line(annotated_frame, 
                        (self.detection_line - self.line_margin, 0), 
                        (self.detection_line - self.line_margin, h), 
                        (0, 255, 255), 2)
                cv2.line(annotated_frame, 
                        (self.detection_line + self.line_margin, 0), 
                        (self.detection_line + self.line_margin, h), 
                        (0, 255, 255), 2)
                
                # Indicadores de dirección
                if self.counting_mode == "entrance_exit":
                    if self.entrance_direction == "positive":
                        entrance_x, exit_x = w - 100, 50
                        entrance_arrow = (entrance_x - 20, h//2), (entrance_x + 20, h//2)
                        exit_arrow = (exit_x + 20, h//2), (exit_x - 20, h//2)
                    else:
                        entrance_x, exit_x = 50, w - 100
                        entrance_arrow = (entrance_x + 20, h//2), (entrance_x - 20, h//2)
                        exit_arrow = (exit_x - 20, h//2), (exit_x + 20, h//2)
                    
                    cv2.putText(annotated_frame, "ENTRADA", (entrance_x - 30, h//2 - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.arrowedLine(annotated_frame, entrance_arrow[0], entrance_arrow[1], 
                                   (0, 255, 0), 3, tipLength=0.3)
                    
                    cv2.putText(annotated_frame, "SALIDA", (exit_x - 25, h//2 - 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.arrowedLine(annotated_frame, exit_arrow[0], exit_arrow[1], 
                                   (0, 0, 255), 3, tipLength=0.3)
            
            else:
                # Línea horizontal
                cv2.line(annotated_frame, 
                        (0, self.detection_line), 
                        (w, self.detection_line), 
                        (0, 255, 255), 5)
                
                # Líneas de margen
                cv2.line(annotated_frame, 
                        (0, self.detection_line - self.line_margin), 
                        (w, self.detection_line - self.line_margin), 
                        (0, 255, 255), 2)
                cv2.line(annotated_frame, 
                        (0, self.detection_line + self.line_margin), 
                        (w, self.detection_line + self.line_margin), 
                        (0, 255, 255), 2)
                
                # Indicadores de dirección
                if self.counting_mode == "entrance_exit":
                    if self.entrance_direction == "positive":
                        entrance_y, exit_y = h - 100, 50
                        entrance_arrow = (w//2, entrance_y - 20), (w//2, entrance_y + 20)
                        exit_arrow = (w//2, exit_y + 20), (w//2, exit_y - 20)
                    else:
                        entrance_y, exit_y = 50, h - 100
                        entrance_arrow = (w//2, entrance_y + 20), (w//2, entrance_y - 20)
                        exit_arrow = (w//2, exit_y - 20), (w//2, exit_y + 20)
                    
                    cv2.putText(annotated_frame, "ENTRADA", (w//2 - 40, entrance_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.arrowedLine(annotated_frame, entrance_arrow[0], entrance_arrow[1], 
                                   (0, 255, 0), 3, tipLength=0.3)
                    
                    cv2.putText(annotated_frame, "SALIDA", (w//2 - 35, exit_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                    cv2.arrowedLine(annotated_frame, exit_arrow[0], exit_arrow[1], 
                                   (0, 0, 255), 3, tipLength=0.3)
            
            # Texto de la línea
            line_text = f"LINEA {self.line_orientation.upper()}"
            if self.line_calibrated:
                line_text += " (CALIBRADA)"
            cv2.putText(annotated_frame, line_text, 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Función para texto con fondo
        def draw_text_with_background(img, text, position, font, scale, color, thickness, bg_color):
            (text_width, text_height), baseline = cv2.getTextSize(text, font, scale, thickness)
            cv2.rectangle(img, 
                         (position[0], position[1] - text_height - 10),
                         (position[0] + text_width + 10, position[1] + baseline),
                         bg_color, -1)
            cv2.putText(img, text, position, font, scale, color, thickness)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        
        # Contadores
        if self.counting_mode == "entrance_exit":
            draw_text_with_background(annotated_frame, f"ENTRADAS: {self.count_entrance}", 
                                    (20, 70), font, font_scale, (0, 255, 0), thickness, (0, 0, 0))
            draw_text_with_background(annotated_frame, f"SALIDAS: {self.count_exit}", 
                                    (20, 110), font, font_scale, (0, 0, 255), thickness, (0, 0, 0))
            
            current_inside = self.count_entrance - self.count_exit
            color_current = (255, 255, 0) if current_inside >= 0 else (0, 0, 255)
            draw_text_with_background(annotated_frame, f"DENTRO: {current_inside}", 
                                    (20, 150), font, font_scale, color_current, thickness, (0, 0, 0))
        else:
            if self.line_orientation == "vertical":
                draw_text_with_background(annotated_frame, f"DERECHA: {self.count_positive}", 
                                        (20, 70), font, font_scale, (0, 255, 0), thickness, (0, 0, 0))
                draw_text_with_background(annotated_frame, f"IZQUIERDA: {self.count_negative}", 
                                        (20, 110), font, font_scale, (0, 0, 255), thickness, (0, 0, 0))
            else:
                draw_text_with_background(annotated_frame, f"ABAJO: {self.count_positive}", 
                                        (20, 70), font, font_scale, (0, 255, 0), thickness, (0, 0, 0))
                draw_text_with_background(annotated_frame, f"ARRIBA: {self.count_negative}", 
                                        (20, 110), font, font_scale, (0, 0, 255), thickness, (0, 0, 0))
            
            total = self.count_positive + self.count_negative
            draw_text_with_background(annotated_frame, f"TOTAL: {total}", 
                                    (20, 150), font, font_scale, (255, 255, 255), thickness, (0, 0, 0))
        
        # Info de configuración
        info_parts = [
            f"{w}x{h}",
            f"Linea: {self.line_orientation}",
            f"Modo: {self.counting_mode}"
        ]
        if self.rotation_angle != 0:
            info_parts.append(f"Rot: {self.rotation_angle}°")
        if self.line_calibrated:
            info_parts.append("CALIBRADA")
        
        info_text = " | ".join(info_parts)
        draw_text_with_background(annotated_frame, info_text, (20, h - 30), 
                                font, 0.5, (255, 255, 255), 1, (0, 0, 0))
        
        return annotated_frame
    
    def reset_counters(self):
        """Reinicia los contadores"""
        if self.counting_mode == "entrance_exit":
            self.count_entrance = 0
            self.count_exit = 0
        else:
            self.count_positive = 0
            self.count_negative = 0
        
        self.counted_ids.clear()
        self.tracks.clear()
        print("🔄 Contadores reiniciados")
    
    def get_stats(self):
        """Retorna estadísticas del conteo"""
        base_stats = {
            "timestamp": datetime.now().isoformat(),
            "resolution": f"{self.target_width}x{self.target_height}" if self.target_height else "original",
            "rotation_angle": self.rotation_angle,
            "line_orientation": self.line_orientation,
            "detection_line_position": self.detection_line,
            "line_calibrated": self.line_calibrated,
            "line_margin": self.line_margin,
            "counting_mode": self.counting_mode,
        }
        
        if self.counting_mode == "entrance_exit":
            base_stats.update({
                "entradas": self.count_entrance,
                "salidas": self.count_exit,
                "personas_dentro": self.count_entrance - self.count_exit,
                "total_movimientos": self.count_entrance + self.count_exit,
                "entrance_direction": self.entrance_direction
            })
        else:
            if self.line_orientation == "vertical":
                base_stats.update({
                    "derecha": self.count_positive,
                    "izquierda": self.count_negative,
                    "total": self.count_positive + self.count_negative
                })
            else:
                base_stats.update({
                    "abajo": self.count_positive,
                    "arriba": self.count_negative,
                    "total": self.count_positive + self.count_negative
                })
        
        return base_stats