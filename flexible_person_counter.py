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
    CON FRAME SKIPPING DINÁMICO para optimización de rendimiento
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
        
        # =====================================================================
        # NUEVA FUNCIONALIDAD: FRAME SKIPPING DINÁMICO
        # =====================================================================
        self._init_frame_skipping()
        
        # Mostrar configuración
        self._show_initial_config()
    
    def _init_frame_skipping(self):
        """Inicializa el sistema de frame skipping dinámico - VERSIÓN CORREGIDA"""
        # Importar configuración
        try:
            import config
            self.enable_frame_skipping = getattr(config, 'ENABLE_FRAME_SKIPPING', True)
            self.default_frame_skip = getattr(config, 'DEFAULT_FRAME_SKIP', 1)
            self.no_detection_frame_skip = getattr(config, 'NO_DETECTION_FRAME_SKIP', 5)
            self.no_detection_threshold = getattr(config, 'NO_DETECTION_THRESHOLD', 10)
            self.detection_recovery_threshold = getattr(config, 'DETECTION_RECOVERY_THRESHOLD', 3)
            self.show_frame_skip_info = getattr(config, 'SHOW_FRAME_SKIP_INFO', True)
        except:
            # Valores por defecto si no se puede importar config
            self.enable_frame_skipping = True
            self.default_frame_skip = 1
            self.no_detection_frame_skip = 5
            self.no_detection_threshold = 10
            self.detection_recovery_threshold = 3
            self.show_frame_skip_info = True
        
        # Estado del frame skipping
        self.frame_counter = 0
        self.frames_without_detection = 0
        self.frames_with_detection = 0
        self.current_frame_skip = self.default_frame_skip
        self.skip_mode = "normal"
        
        # Estadísticas de frame skipping
        self.total_frames_processed = 0
        self.total_frames_skipped = 0
        self.mode_changes = 0
        
        # NUEVO: Validar configuración
        if self.enable_frame_skipping:
            self.validate_frame_skip_config()
            
            print(f"⚡ Frame skipping HABILITADO:")
            print(f"   📊 Skip por defecto: {self.default_frame_skip} (procesar 1 de cada {self.default_frame_skip + 1})")
            print(f"   📊 Skip sin detecciones: {self.no_detection_frame_skip} (procesar 1 de cada {self.no_detection_frame_skip + 1})")
            print(f"   🎯 Threshold sin detecciones: {self.no_detection_threshold} frames")
            print(f"   🎯 Threshold recuperación: {self.detection_recovery_threshold} frames")
        else:
            print("⚡ Frame skipping DESHABILITADO - procesando todos los frames")
    
    def _show_initial_config(self):
        """Muestra la configuración inicial"""
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
        
        if self.rotation_angle != 0:
            print(f"🔄 Rotación configurada: {self.rotation_angle}°")
    
    def should_process_frame(self):
       """
       Determina si se debe procesar el frame actual basado en el frame skipping dinámico
       Returns: True si se debe procesar, False si se debe saltar
       VERSIÓN CORREGIDA - sin frames varados
       """
       if not self.enable_frame_skipping:
           return True
       
       # Incrementar contador de frames
       self.frame_counter += 1
       
       # CORRECCIÓN: Determinar si procesar según el skip actual
       # El problema estaba en que skip=0 causaba división por cero o comportamiento extraño
       skip_interval = max(1, self.current_frame_skip + 1)  # Mínimo 1 para evitar problemas
       should_process = (self.frame_counter % skip_interval) == 0
       
       if should_process:
           self.total_frames_processed += 1
       else:
           self.total_frames_skipped += 1
       
       return should_process
    
    def update_frame_skip_mode(self, has_detections):
       """
       Actualiza el modo de frame skipping basado en las detecciones
       VERSIÓN CORREGIDA - transiciones más suaves
       """
       if not self.enable_frame_skipping:
           return
       
       previous_mode = self.skip_mode
       previous_skip = self.current_frame_skip
       
       if has_detections:
           self.frames_with_detection += 1
           self.frames_without_detection = 0
           
           # Volver a modo normal si hay detecciones
           if self.skip_mode == "no_detection" and self.frames_with_detection >= self.detection_recovery_threshold:
               self.current_frame_skip = self.default_frame_skip
               self.skip_mode = "normal"
               if self.show_frame_skip_info:
                   print(f"⚡ Modo NORMAL activado (skip={self.current_frame_skip}) - {self.frames_with_detection} frames con detecciones")
       else:
           self.frames_without_detection += 1
           self.frames_with_detection = 0
           
           # Cambiar a modo sin detecciones
           if self.skip_mode == "normal" and self.frames_without_detection >= self.no_detection_threshold:
               self.current_frame_skip = self.no_detection_frame_skip
               self.skip_mode = "no_detection"
               if self.show_frame_skip_info:
                   print(f"⚡ Modo SIN DETECCIONES activado (skip={self.current_frame_skip}) - {self.frames_without_detection} frames sin detecciones")
       
       # Contar cambios de modo
       if previous_mode != self.skip_mode:
           self.mode_changes += 1
           # NUEVO: Reset parcial del contador para evitar desincronización
           if self.show_frame_skip_info:
               print(f"🔄 Cambio de modo: {previous_mode} → {self.skip_mode} (skip: {previous_skip} → {self.current_frame_skip})")
    
    def get_frame_skip_stats(self):
        """Obtiene estadísticas del frame skipping"""
        total_frames = self.total_frames_processed + self.total_frames_skipped
        if total_frames == 0:
            return None
        
        skip_percentage = (self.total_frames_skipped / total_frames) * 100
        
        return {
            "enabled": self.enable_frame_skipping,
            "current_mode": self.skip_mode,
            "current_skip": self.current_frame_skip,
            "total_frames": total_frames,
            "frames_processed": self.total_frames_processed,
            "frames_skipped": self.total_frames_skipped,
            "skip_percentage": round(skip_percentage, 2),
            "mode_changes": self.mode_changes,
            "frames_without_detection": self.frames_without_detection,
            "frames_with_detection": self.frames_with_detection
        }
    
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
        
        # NUEVA LÓGICA: ¿Cruzó completamente la zona?
        crossed_positive = start_pos < line_before and end_pos > line_after
        crossed_negative = start_pos > line_after and end_pos < line_before
        
        if crossed_positive or crossed_negative:
            direction_name = ""
            if crossed_positive:
                direction_name = "ABAJO" if self.line_orientation == "horizontal" else "DERECHA"
            else:
                direction_name = "ARRIBA" if self.line_orientation == "horizontal" else "IZQUIERDA"
            
            if self.show_frame_skip_info:
                print(f"   ✅ ¡CRUCE COMPLETO! ID {track_id} hacia {direction_name}")
            return True
        
        return False
    
    def get_direction(self, track_id, current_pos):
        """Determina la dirección usando TODO el trayecto"""
        if len(self.tracks[track_id]) < 5:
            return None
        
        positions = list(self.tracks[track_id])
        start_pos = positions[0]
        end_pos = positions[-1]
        
        # Calcular movimiento total
        total_movement = end_pos - start_pos
        
        if abs(total_movement) < self.direction_threshold:
            return None
        
        direction = "positive" if total_movement > 0 else "negative"
        return direction
    # NUEVA FUNCIÓN: Validar configuración de frame skipping
    def validate_frame_skip_config(self):
        """
        Valida y corrige la configuración de frame skipping para evitar problemas
        """
        # Asegurar valores mínimos válidos
        self.default_frame_skip = max(0, self.default_frame_skip)
        self.no_detection_frame_skip = max(0, self.no_detection_frame_skip)
        self.no_detection_threshold = max(1, self.no_detection_threshold)
        self.detection_recovery_threshold = max(1, self.detection_recovery_threshold)
        
        # Advertencias de configuración
        if self.default_frame_skip > 10:
            print(f"⚠️ ADVERTENCIA: DEFAULT_FRAME_SKIP muy alto ({self.default_frame_skip}) - puede perderse actividad")
        
        if self.no_detection_frame_skip > 20:
            print(f"⚠️ ADVERTENCIA: NO_DETECTION_FRAME_SKIP muy alto ({self.no_detection_frame_skip}) - puede perderse cuando aparezcan personas")
        
        if self.no_detection_threshold < 5:
            print(f"⚠️ ADVERTENCIA: NO_DETECTION_THRESHOLD muy bajo ({self.no_detection_threshold}) - cambios de modo muy frecuentes")
        
        print(f"✅ Configuración de frame skipping validada")
    def process_frame(self, frame):
        """
        Procesa un frame para detectar y contar personas - CON FRAME SKIPPING CORREGIDO
        """
        # NUEVA LÓGICA: Siempre rotar y redimensionar para mantener consistencia visual
        rotated_frame = self.rotate_frame(frame)
        resized_frame = self.resize_frame(rotated_frame)
        h, w = resized_frame.shape[:2]
        
        if self.detection_line is None:
            self.set_detection_line(w, h)
        
        # AHORA verificar si se debe procesar este frame para detección
        if not self.should_process_frame():
            # Frame saltado - actualizar modo sin detecciones y devolver frame básico
            self.update_frame_skip_mode(has_detections=False)
            
            # Crear resultado vacío pero mantener frame visual
            class SkippedResult:
                def plot(self):
                    return resized_frame
            
            return SkippedResult(), resized_frame
        
        # FRAME A PROCESAR - hacer detección completa
        # Suprimir output de YOLO
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr
        
        f = io.StringIO()
        with redirect_stdout(f), redirect_stderr(f):
            results = self.model.track(resized_frame, persist=True, classes=[0], conf=0.5, verbose=False)
        
        has_detections = False
        
        # Procesar detecciones si existen
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()
            
            valid_detections = sum(1 for conf in confidences if conf >= 0.5)
            has_detections = valid_detections > 0
            
            if has_detections and self.show_frame_skip_info:
                print(f"👥 {valid_detections} personas detectadas (Frame #{self.frame_counter})")
            
            for box, track_id, conf in zip(boxes, track_ids, confidences):
                if conf < 0.5:
                    continue
                
                x1, y1, x2, y2 = box
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                
                if self.line_orientation == "vertical":
                    tracking_coord = center_x
                    movement_axis = "horizontal"
                else:
                    tracking_coord = center_y
                    movement_axis = "vertical"
                
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
        
        # Actualizar modo de frame skipping
        self.update_frame_skip_mode(has_detections=has_detections)
        
        return results[0], resized_frame
    
    def draw_annotations(self, frame, results):
        """Dibuja las anotaciones en el frame - INCLUYENDO INFO DE FRAME SKIPPING"""
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
                
                # Indicadores de dirección para entrada/salida
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
                
                # Indicadores de dirección para entrada/salida
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
        
        # NUEVA SECCIÓN: Info de Frame Skipping
        if self.enable_frame_skipping:
            skip_stats = self.get_frame_skip_stats()
            if skip_stats:
                # Color según el modo
                skip_color = (0, 255, 255) if skip_stats['current_mode'] == "normal" else (255, 0, 255)
                
                # Texto del modo actual
                mode_text = f"SKIP: {skip_stats['current_mode'].upper()}"
                draw_text_with_background(annotated_frame, mode_text, 
                                        (20, 190), font, 0.6, skip_color, 2, (0, 0, 0))
                
                # Estadísticas de eficiencia
                efficiency_text = f"Eficiencia: {skip_stats['skip_percentage']:.1f}% saltados"
                draw_text_with_background(annotated_frame, efficiency_text, 
                                        (20, 220), font, 0.5, (255, 255, 255), 1, (0, 0, 0))
                
                # Frame actual
                frame_text = f"Frame: {self.frame_counter} (Skip: {skip_stats['current_skip']})"
                draw_text_with_background(annotated_frame, frame_text, 
                                        (20, 245), font, 0.5, (200, 200, 200), 1, (0, 0, 0))
        
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
        if self.enable_frame_skipping:
            info_parts.append(f"Skip: {self.skip_mode}")
        
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
        
        # Reset frame skipping stats
        self.frame_counter = 0
        self.frames_without_detection = 0
        self.frames_with_detection = 0
        self.current_frame_skip = self.default_frame_skip
        self.skip_mode = "normal"
        self.total_frames_processed = 0
        self.total_frames_skipped = 0
        self.mode_changes = 0
        
        print("🔄 Contadores y estadísticas de frame skipping reiniciados")
    
    def get_stats(self):
        """Retorna estadísticas del conteo incluyendo frame skipping"""
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
        
        # Agregar estadísticas de frame skipping
        if self.enable_frame_skipping:
            skip_stats = self.get_frame_skip_stats()
            if skip_stats:
                base_stats.update({
                    "frame_skipping_enabled": True,
                    "frame_skip_mode": skip_stats['current_mode'],
                    "total_frames": skip_stats['total_frames'],
                    "frames_processed": skip_stats['frames_processed'],
                    "frames_skipped": skip_stats['frames_skipped'],
                    "skip_efficiency_percent": skip_stats['skip_percentage'],
                    "mode_changes": skip_stats['mode_changes']
                })
        else:
            base_stats["frame_skipping_enabled"] = False
        
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
    
    def print_frame_skip_summary(self):
        """Imprime un resumen de las estadísticas de frame skipping"""
        if not self.enable_frame_skipping:
            print("⚡ Frame skipping DESHABILITADO")
            return
        
        skip_stats = self.get_frame_skip_stats()
        if not skip_stats:
            return
        
        print("\n" + "="*50)
        print("⚡ RESUMEN DE FRAME SKIPPING")
        print("="*50)
        print(f"📊 Total frames: {skip_stats['total_frames']}")
        print(f"✅ Frames procesados: {skip_stats['frames_processed']}")
        print(f"⏭️  Frames saltados: {skip_stats['frames_skipped']}")
        print(f"📈 Eficiencia: {skip_stats['skip_percentage']:.2f}% saltados")
        print(f"🔄 Cambios de modo: {skip_stats['mode_changes']}")
        print(f"📍 Modo actual: {skip_stats['current_mode'].upper()}")
        
        # Calcular rendimiento mejorado
        if skip_stats['total_frames'] > 0:
            fps_improvement = 100 / (100 - skip_stats['skip_percentage'])
            print(f"🚀 Mejora de rendimiento: {fps_improvement:.1f}x más rápido")
        
        print("="*50)