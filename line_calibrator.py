def draw_interface(self):
        """
        Dibuja la interfaz de calibración
        """
        if self.frame is None:
            return None
        
        # Crear copia del frame para dibujar
        display_frame = self.frame.copy()
        h, w = display_frame.shape[:2]
        
        # Dibujar línea actual si existe
        if self.line_start and self.line_end:
            # Línea principal
            cv2.line(display_frame, self.line_start, self.line_end, (0, 255, 255), 3)
            
            # Puntos de inicio y fin
            cv2.circle(display_frame, self.line_start, 5, (0, 255, 0), -1)
            cv2.circle(display_frame, self.line_end, 5, (0, 0, 255), -1)
            
            # Calcular línea de detección según orientación
            if self.line_orientation == "vertical":
                # Línea vertical de detección
                center_x = int((self.line_start[0] + self.line_end[0]) / 2)
                cv2.line(display_frame, (center_x, 0), (center_x, h), (255, 0, 255), 2)
                
                # Área de detección (margen)
                cv2.line(display_frame, (center_x - self.line_margin, 0), 
                        (center_x - self.line_margin, h), (255, 0, 255), 1)
                cv2.line(display_frame, (center_x + self.line_margin, 0), 
                        (center_x + self.line_margin, h), (255, 0, 255), 1)
                
                # Texto de información
                cv2.putText(display_frame, f"Linea X: {center_x}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Flechas indicando direcciones de movimiento
                cv2.arrowedLine(display_frame, (50, h//2), (100, h//2), (0, 255, 0), 3, tipLength=0.3)
                cv2.putText(display_frame, "ENTRADA", (50, h//2 - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                cv2.arrowedLine(display_frame, (w - 50, h//2), (w - 100, h//2), (0, 0, 255), 3, tipLength=0.3)
                cv2.putText(display_frame, "SALIDA", (w - 100, h//2 - 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            else:
                # Línea horizontal de detección
                center_y = int((self.line_start[1] + self.line_end[1]) / 2)
                cv2.line(display_frame, (0, center_y), (w, center_y), (255, 0, 255), 2)
                
                # Área de detección (margen)
                cv2.line(display_frame, (0, center_y - self.line_margin), 
                        (w, center_y - self.line_margin), (255, 0, 255), 1)
                cv2.line(display_frame, (0, center_y + self.line_margin), 
                        (w, center_y + self.line_margin), (255, 0, 255), 1)
                
                # Texto de información
                cv2.putText(display_frame, f"Linea Y: {center_y}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Flechas indicando direcciones de movimiento
                cv2.arrowedLine(display_frame, (w//2, 50), (w//2, 100), (0, 255, 0), 3, tipLength=0.3)
                cv2.putText(display_frame, "ENTRADA", (w//2 - 40, 40), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                cv2.arrowedLine(display_frame, (w//2, h - 50), (w//2, h - 100), (0, 0, 255), 3, tipLength=0.3)
                cv2.putText(display_frame, "SALIDA", (w//2 - 30, h - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            cv2.putText(display_frame, f"Margen: {self.line_margin}px", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Línea temporal mientras se dibuja
        elif self.drawing and self.line_start and self.current_mouse_pos:
            cv2.line(display_frame, self.line_start, self.current_mouse_pos, (0, 255, 255), 2)
            cv2.circle(display_frame, self.line_start, 5, (0, 255, 0), -1)
        
        # Instrucciones
        instructions = [
            f"CALIBRADOR DE LINEA {self.line_orientation.upper()}",
            "Click y arrastra para dibujar la linea",
            "TAB: Cambiar orientacion | ESC: Salir | R: Reset | S: Guardar | +/-: Margen"
        ]
        
        for i, text in enumerate(instructions):
            y_pos = h - 80 + (i * 25)
            cv2.putText(display_frame, text, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Información de resolución y orientación
        info_text = f"Resolucion: {w}x{h} | Orientacion: {self.line_orientation}"
        if self.rotation_angle != 0:
            info_text += f" | Rotacion: {self.rotation_angle}°"
        cv2.putText(display_frame, info_text, (10, h - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return display_frame#!/usr/bin/env python3
"""
Calibrador de Línea de Detección para Sistema RTSP
Este módulo permite capturar un frame del stream RTSP y dibujar interactivamente
la línea de detección para generar los parámetros de configuración.

Autor: Tu Nombre
Fecha: 2024
"""

import cv2
import subprocess
import numpy as np
from datetime import datetime
from pathlib import Path
import json


class LineCalibrator:
    """
    Calibrador interactivo para establecer la línea de detección
    """
    
    def __init__(self, rtsp_url, target_width=640, rotation_angle=0, line_orientation="vertical"):
        self.rtsp_url = rtsp_url
        self.target_width = target_width
        self.rotation_angle = rotation_angle
        self.rotation_code = self._get_rotation_code(rotation_angle)
        self.line_orientation = line_orientation.lower()  # "vertical" o "horizontal"
        
        # Variables para el dibujo de línea
        self.drawing = False
        self.line_start = None
        self.line_end = None
        self.current_mouse_pos = None
        self.line_margin = 30
        
        # Frame capturado
        self.frame = None
        self.original_frame = None
        self.scale_factor = 1.0
        
        # Configuración de salida
        self.output_dir = Path("calibration")
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"📏 Orientación de línea: {self.line_orientation.upper()}")
        if self.line_orientation == "vertical":
            print("   📐 Para detectar movimiento HORIZONTAL (←→)")
        else:
            print("   📐 Para detectar movimiento VERTICAL (↑↓)")
    
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
        aspect_ratio = h / w
        target_height = int(self.target_width * aspect_ratio)
        self.scale_factor = self.target_width / w
        
        resized_frame = cv2.resize(frame, (self.target_width, target_height))
        return resized_frame
    
    def capture_frame_from_rtsp(self, timeout_seconds=30):
        """
        Captura un frame del stream RTSP usando ffmpeg
        """
        print(f"📡 Conectando al stream RTSP: {self.rtsp_url}")
        print(f"⏳ Timeout: {timeout_seconds} segundos")
        
        # Comando ffmpeg para capturar un solo frame
        output_file = self.output_dir / f"calibration_frame_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', self.rtsp_url,
            '-vframes', '1',  # Solo capturar 1 frame
            '-y',  # Sobrescribir si existe
            str(output_file)
        ]
        
        try:
            print("🎬 Capturando frame...")
            
            # Ejecutar ffmpeg con timeout
            process = subprocess.run(
                cmd,
                timeout=timeout_seconds,
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0 and output_file.exists():
                print(f"✅ Frame capturado: {output_file.name}")
                
                # Cargar el frame
                frame = cv2.imread(str(output_file))
                if frame is not None:
                    self.original_frame = frame.copy()
                    
                    # Rotar si es necesario
                    rotated_frame = self.rotate_frame(frame)
                    
                    # Redimensionar
                    self.frame = self.resize_frame(rotated_frame)
                    
                    h, w = self.frame.shape[:2]
                    rotation_info = f" (rotado {self.rotation_angle}°)" if self.rotation_angle != 0 else ""
                    print(f"📐 Frame procesado: {w}x{h}{rotation_info}")
                    
                    return True
                else:
                    print("❌ Error cargando el frame capturado")
                    return False
            else:
                print(f"❌ Error capturando frame")
                print(f"Código de salida: {process.returncode}")
                if process.stderr:
                    print(f"Error: {process.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Timeout después de {timeout_seconds} segundos")
            return False
        except Exception as e:
            print(f"❌ Excepción capturando frame: {e}")
            return False
    
    def mouse_callback(self, event, x, y, flags, param):
        """
        Callback para manejar eventos del mouse
        """
        if event == cv2.EVENT_LBUTTONDOWN:
            # Iniciar dibujo de línea
            self.drawing = True
            self.line_start = (x, y)
            self.line_end = (x, y)
            print(f"🖱️ Iniciando línea en: ({x}, {y})")
        
        elif event == cv2.EVENT_MOUSEMOVE:
            self.current_mouse_pos = (x, y)
            if self.drawing:
                self.line_end = (x, y)
        
        elif event == cv2.EVENT_LBUTTONUP:
            # Finalizar dibujo de línea
            if self.drawing:
                self.drawing = False
                self.line_end = (x, y)
                print(f"🖱️ Línea finalizada en: ({x}, {y})")
                self.calculate_line_parameters()
    
    def calculate_line_parameters(self):
        """
        Calcula los parámetros de la línea de detección
        """
        if self.line_start and self.line_end:
            x1, y1 = self.line_start
            x2, y2 = self.line_end
            
            if self.line_orientation == "vertical":
                # Línea vertical - calcular centro X
                center_pos = int((x1 + x2) / 2)
                dimension = "X"
                frame_dimension = self.frame.shape[1]  # ancho
            else:
                # Línea horizontal - calcular centro Y
                center_pos = int((y1 + y2) / 2)
                dimension = "Y"
                frame_dimension = self.frame.shape[0]  # alto
            
            # Calcular ángulo de la línea
            if x2 != x1:
                angle_rad = np.arctan2(y2 - y1, x2 - x1)
                angle_deg = np.degrees(angle_rad)
            else:
                angle_deg = 90  # Línea vertical
            
            print(f"\n📏 Parámetros de línea {self.line_orientation} calculados:")
            print(f"   📍 Punto inicio: ({x1}, {y1})")
            print(f"   📍 Punto final: ({x2}, {y2})")
            print(f"   📐 Centro {dimension}: {center_pos}")
            print(f"   📐 Ángulo: {angle_deg:.1f}°")
            print(f"   📏 Longitud: {np.sqrt((x2-x1)**2 + (y2-y1)**2):.1f} píxeles")
    
    def draw_interface(self):
        """
        Dibuja la interfaz de calibración
        """
        if self.frame is None:
            return None
        
        # Crear copia del frame para dibujar
        display_frame = self.frame.copy()
        h, w = display_frame.shape[:2]
        
        # Dibujar línea actual si existe
        if self.line_start and self.line_end:
            # Línea principal
            cv2.line(display_frame, self.line_start, self.line_end, (0, 255, 255), 3)
            
            # Puntos de inicio y fin
            cv2.circle(display_frame, self.line_start, 5, (0, 255, 0), -1)
            cv2.circle(display_frame, self.line_end, 5, (0, 0, 255), -1)
            
            # Calcular línea vertical de detección
            center_x = int((self.line_start[0] + self.line_end[0]) / 2)
            
            # Línea de detección vertical
            cv2.line(display_frame, (center_x, 0), (center_x, h), (255, 0, 255), 2)
            
            # Área de detección (margen)
            cv2.line(display_frame, (center_x - self.line_margin, 0), 
                    (center_x - self.line_margin, h), (255, 0, 255), 1)
            cv2.line(display_frame, (center_x + self.line_margin, 0), 
                    (center_x + self.line_margin, h), (255, 0, 255), 1)
            
            # Texto de información
            cv2.putText(display_frame, f"Linea X: {center_x}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(display_frame, f"Margen: {self.line_margin}px", 
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Línea temporal mientras se dibuja
        elif self.drawing and self.line_start and self.current_mouse_pos:
            cv2.line(display_frame, self.line_start, self.current_mouse_pos, (0, 255, 255), 2)
            cv2.circle(display_frame, self.line_start, 5, (0, 255, 0), -1)
        
        # Instrucciones
        instructions = [
            "CALIBRADOR DE LINEA DE DETECCION",
            "Click y arrastra para dibujar la linea",
            "ESC: Salir | R: Reset | S: Guardar | +/-: Ajustar margen"
        ]
        
        for i, text in enumerate(instructions):
            y_pos = h - 80 + (i * 25)
            cv2.putText(display_frame, text, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Información de resolución
        info_text = f"Resolucion: {w}x{h}"
        if self.rotation_angle != 0:
            info_text += f" | Rotacion: {self.rotation_angle}°"
        cv2.putText(display_frame, info_text, (10, h - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        return display_frame
    
    def generate_config_parameters(self):
        """
        Genera los parámetros para config.py
        """
        if not (self.line_start and self.line_end):
            print("❌ No hay línea dibujada")
            return None
        
        x1, y1 = self.line_start
        x2, y2 = self.line_end
        h, w = self.frame.shape[:2]
        
        if self.line_orientation == "vertical":
            center_pos = int((x1 + x2) / 2)
            dimension = w  # ancho del frame
            pos_name = "X"
        else:
            center_pos = int((y1 + y2) / 2)
            dimension = h  # alto del frame
            pos_name = "Y"
        
        # Calcular parámetros
        detection_line_position = center_pos
        detection_line_ratio = center_pos / dimension
        
        config_params = {
            "# Parámetros de línea de detección": "# Generados por LineCalibrator",
            "LINE_ORIENTATION": self.line_orientation.upper(),
            f"DETECTION_LINE_{pos_name}": detection_line_position,
            "DETECTION_LINE_RATIO": round(detection_line_ratio, 3),
            "LINE_MARGIN": self.line_margin,
            "TARGET_WIDTH": self.target_width,
            "ROTATION_ANGLE": self.rotation_angle,
            "# Coordenadas de calibración": f"# Resolución: {w}x{h}",
            "CALIBRATION_LINE_START": list(self.line_start),
            "CALIBRATION_LINE_END": list(self.line_end),
            "CALIBRATION_TIMESTAMP": datetime.now().isoformat()
        }
        
        return config_params
    
    def save_calibration(self):
        """
        Guarda la calibración en archivos
        """
        if not (self.line_start and self.line_end):
            print("❌ No hay línea para guardar")
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Guardar imagen con línea dibujada
        display_frame = self.draw_interface()
        if display_frame is not None:
            image_file = self.output_dir / f"calibration_result_{timestamp}.jpg"
            cv2.imwrite(str(image_file), display_frame)
            print(f"💾 Imagen guardada: {image_file.name}")
        
        # Guardar parámetros
        config_params = self.generate_config_parameters()
        if config_params:
            config_file = self.output_dir / f"line_config_{timestamp}.json"
            with open(config_file, 'w') as f:
                json.dump(config_params, f, indent=2)
            print(f"💾 Configuración guardada: {config_file.name}")
            
            # Mostrar parámetros para config.py
            print(f"\n📋 PARÁMETROS PARA config.py:")
            print(f"# Agregar estas líneas a config.py:")
            print(f"LINE_ORIENTATION = \"{config_params['LINE_ORIENTATION'].lower()}\"")
            if self.line_orientation == "vertical":
                print(f"DETECTION_LINE_X = {config_params['DETECTION_LINE_X']}")
            else:
                print(f"DETECTION_LINE_Y = {config_params['DETECTION_LINE_Y']}")
            print(f"DETECTION_LINE_RATIO = {config_params['DETECTION_LINE_RATIO']}")
            print(f"LINE_MARGIN = {config_params['LINE_MARGIN']}")
            print(f"# Línea {self.line_orientation} dibujada de ({config_params['CALIBRATION_LINE_START']}) a ({config_params['CALIBRATION_LINE_END']})")
            
            return True
        
        return False
    
    def run_calibration(self):
        """
        Ejecuta el proceso de calibración interactivo
        """
        print("🎯 Iniciando Calibrador de Línea de Detección")
        print("=" * 50)
        
        # Capturar frame del RTSP
        if not self.capture_frame_from_rtsp():
            print("❌ No se pudo capturar frame del RTSP")
            return False
        
        print("\n🖱️ Controles del calibrador:")
        print("   • Click y arrastra para dibujar la línea de detección")
        print("   • TAB: Cambiar orientación (vertical ↔ horizontal)")
        print("   • R: Reset (borrar línea)")
        print("   • S: Guardar calibración")
        print("   • +/-: Aumentar/Disminuir margen de línea")
        print("   • ESC: Salir")
        print(f"\n📍 Modo actual: Línea {self.line_orientation.upper()}")
        if self.line_orientation == "vertical":
            print("   📐 Para detectar movimiento HORIZONTAL (personas que cruzan ←→)")
        else:
            print("   📐 Para detectar movimiento VERTICAL (personas que cruzan ↑↓)")
        print("   💡 Usa TAB para cambiar entre vertical y horizontal")
        
        # Configurar ventana
        window_name = "🎯 Calibrador de Línea de Detección"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window_name, self.mouse_callback)
        
        try:
            while True:
                # Dibujar interfaz
                display_frame = self.draw_interface()
                if display_frame is not None:
                    cv2.imshow(window_name, display_frame)
                
                # Manejar teclas
                key = cv2.waitKey(30) & 0xFF
                
                if key == 27:  # ESC
                    print("🚪 Saliendo del calibrador")
                    break
                elif key == ord('r') or key == ord('R'):
                    # Reset
                    self.line_start = None
                    self.line_end = None
                    self.drawing = False
                    print("🔄 Línea borrada")
                elif key == ord('s') or key == ord('S'):
                    # Guardar
                    if self.save_calibration():
                        print("✅ Calibración guardada exitosamente")
                    else:
                        print("❌ Error guardando calibración")
                elif key == ord('+') or key == ord('='):
                    # Aumentar margen
                    self.line_margin = min(100, self.line_margin + 5)
                    print(f"📏 Margen aumentado a: {self.line_margin}px")
                elif key == ord('-'):
                    # Disminuir margen
                    self.line_margin = max(5, self.line_margin - 5)
                    print(f"📏 Margen reducido a: {self.line_margin}px")
                elif key == 9:  # TAB
                    # Cambiar orientación
                    self.line_orientation = "horizontal" if self.line_orientation == "vertical" else "vertical"
                    # Resetear línea al cambiar orientación
                    self.line_start = None
                    self.line_end = None
                    self.drawing = False
                    print(f"🔄 Orientación cambiada a: {self.line_orientation.upper()}")
                    if self.line_orientation == "vertical":
                        print("   📐 Detectará movimiento HORIZONTAL (←→)")
                    else:
                        print("   📐 Detectará movimiento VERTICAL (↑↓)")
        
        except KeyboardInterrupt:
            print("\n🛑 Calibración interrumpida")
        
        finally:
            cv2.destroyAllWindows()
        
        return True


def main():
    """
    Función principal del calibrador
    """
    # Importar configuración si existe
    try:
        from config import RTSP_URL, TARGET_WIDTH, ROTATION_ANGLE
        try:
            from config import LINE_ORIENTATION
        except ImportError:
            LINE_ORIENTATION = "vertical"  # Por defecto
    except ImportError:
        print("⚠️ No se pudo importar config.py, usando valores por defecto")
        RTSP_URL = "rtsp://admin:usuario1234@192.168.18.13:554/Streaming/channels/101?tcp"
        TARGET_WIDTH = 640
        ROTATION_ANGLE = 180
        LINE_ORIENTATION = "vertical"
    
    print("🎯 Calibrador de Línea de Detección para Sistema RTSP")
    print("=" * 55)
    print(f"📡 URL RTSP: {RTSP_URL}")
    print(f"📐 Resolución objetivo: {TARGET_WIDTH}p")
    print(f"🔄 Rotación: {ROTATION_ANGLE}°")
    print(f"📏 Orientación inicial: {LINE_ORIENTATION.upper()}")
    
    # Crear y ejecutar calibrador
    calibrator = LineCalibrator(
        rtsp_url=RTSP_URL,
        target_width=TARGET_WIDTH,
        rotation_angle=ROTATION_ANGLE,
        line_orientation=LINE_ORIENTATION
    )
    
    success = calibrator.run_calibration()
    
    if success:
        print("\n✅ Calibración completada")
        print("📁 Archivos guardados en: calibration/")
    else:
        print("\n❌ Error en la calibración")
    
    return success


if __name__ == "__main__":
    import sys
    
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Hasta luego!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Error fatal: {e}")
        sys.exit(1)