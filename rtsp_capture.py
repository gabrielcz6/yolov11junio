import asyncio
import subprocess
import os
import time
from datetime import datetime
from pathlib import Path
from queue import Queue
import threading


class RTSPVideoCapture:
    """
    Clase para capturar videos del stream RTSP de manera continua sin gaps
    usando segmentación automática de FFmpeg
    """
    
    def __init__(self, rtsp_url, output_dir="videos"):
        self.rtsp_url = rtsp_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.video_queue = Queue()
        self.video_counter = 1
        self.is_capturing = False
        self.ffmpeg_process = None
        self.file_monitor_thread = None
        self.known_files = set()
        
    def _get_output_pattern(self):
        """Genera el patrón de salida para segmentación"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(self.output_dir / f"video_{timestamp}_%03d.mp4")
    
    def _monitor_new_files(self, duration_seconds):
        """
        Monitorea el directorio para detectar nuevos archivos completados
        y los agrega a la cola de procesamiento
        """
        print("📁 Iniciando monitor de archivos...")
        
        while self.is_capturing:
            try:
                # Buscar archivos .mp4 en el directorio
                current_files = set()
                for file_path in self.output_dir.glob("*.mp4"):
                    if file_path.is_file():
                        current_files.add(file_path)
                
                # Detectar archivos nuevos
                new_files = current_files - self.known_files
                
                for new_file in new_files:
                    # Verificar que el archivo esté completo
                    # (no está siendo escrito por FFmpeg)
                    if self._is_file_complete(new_file, duration_seconds):
                        print(f"✅ Nuevo video detectado: {new_file.name}")
                        self.video_queue.put(str(new_file))
                        self.video_counter += 1
                        self.known_files.add(new_file)
                    else:
                        # Archivo aún no está completo, no agregarlo a known_files todavía
                        print(f"⏳ Archivo {new_file.name} aún no está completo, esperando...")
                
                # Solo actualizar known_files con archivos que ya procesamos
                # Los archivos incompletos se volverán a detectar en la siguiente iteración
                
                # Esperar antes de la siguiente verificación (más tiempo para archivos grandes)
                time.sleep(5)
                
            except Exception as e:
                print(f"⚠️ Error en monitor de archivos: {e}")
                time.sleep(5)
        
        print("📁 Monitor de archivos finalizado")
    
    def _is_file_complete(self, file_path, expected_duration):
        """
        Verifica si un archivo está completamente escrito
        """
        try:
            # Verificar que el archivo no esté siendo modificado
            stat1 = file_path.stat()
            time.sleep(2)  # Aumentar tiempo de espera
            stat2 = file_path.stat()
            
            # Si el tamaño cambió, aún se está escribiendo
            if stat1.st_size != stat2.st_size:
                return False
            
            # Verificar que tenga un tamaño mínimo razonable
            # (aproximadamente 500KB por minuto de video como mínimo)
            min_size = expected_duration * 500 * 1024 // 60  # Más conservador
            if stat1.st_size < min_size:
                return False
            
            # NUEVA VERIFICACIÓN: Intentar abrir el archivo con OpenCV
            import cv2
            cap = cv2.VideoCapture(str(file_path))
            if not cap.isOpened():
                cap.release()
                return False
            
            # Verificar que tenga al menos algunos frames
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            
            # Debe tener al menos 10 frames para considerarse válido
            if frame_count < 10:
                return False
            
            return True
            
        except Exception as e:
            # Si hay cualquier error, asumir que no está completo
            return False
    
    async def continuous_capture_segmented(self, duration_seconds=600, max_videos=None):
        """
        Captura videos continuamente usando segmentación de FFmpeg
        SIN gaps entre videos
        """
        self.is_capturing = True
        
        print(f"🚀 Iniciando captura continua SEGMENTADA de videos de {duration_seconds} segundos")
        if max_videos:
            print(f"📊 Máximo de videos: {max_videos}")
        else:
            print("♾️  Captura infinita (Ctrl+C para detener)")
        print("🔥 MODO SIN GAPS - Segmentación automática")
        
        # Generar patrón de salida
        output_pattern = self._get_output_pattern()
        print(f"📁 Patrón de archivos: {output_pattern}")
        
        # Comando FFmpeg para segmentación continua
        cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', self.rtsp_url,
            '-f', 'segment',                          # Modo segmentación
            '-segment_time', str(duration_seconds),   # Duración por segmento
            '-segment_format', 'mp4',                 # Formato de segmentos
            '-reset_timestamps', '1',                 # Reset timestamps en cada segmento
            '-c:v', 'libx264',                       # Codec video
            '-c:a', 'aac',                           # Codec audio
            '-avoid_negative_ts', 'make_zero',       # Evitar timestamps negativos
            '-rtbufsize', '100M',                    # Buffer RTSP más grande
            output_pattern
        ]
        
        print(f"🎬 Iniciando FFmpeg con segmentación automática...")
        print(f"⚡ Comando: {' '.join(cmd[:8])}... (simplificado)")
        
        try:
            # Iniciar proceso FFmpeg de manera asíncrona
            self.ffmpeg_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            print(f"✅ Proceso FFmpeg iniciado (PID: {self.ffmpeg_process.pid})")
            
            # Iniciar monitor de archivos en thread separado
            self.file_monitor_thread = threading.Thread(
                target=self._monitor_new_files,
                args=(duration_seconds,),
                daemon=True
            )
            self.file_monitor_thread.start()
            print("📁 Monitor de archivos iniciado")
            
            # Monitorear proceso FFmpeg y mostrar progreso
            videos_detected = 0
            start_time = time.time()
            last_status_time = start_time
            
            while self.is_capturing:
                # Verificar si el proceso sigue corriendo
                if self.ffmpeg_process.returncode is not None:
                    print("⚠️ Proceso FFmpeg terminó inesperadamente")
                    break
                
                # Mostrar estado cada 30 segundos
                current_time = time.time()
                if current_time - last_status_time >= 30:
                    elapsed = current_time - start_time
                    elapsed_hours = elapsed // 3600
                    elapsed_mins = (elapsed % 3600) // 60
                    
                    current_queue_size = self.video_queue.qsize()
                    videos_detected = self.video_counter - 1
                    
                    print(f"🔄 Estado: {elapsed_hours:02.0f}:{elapsed_mins:02.0f} | "
                          f"Videos: {videos_detected} | Cola: {current_queue_size}")
                    
                    last_status_time = current_time
                
                # Verificar límite de videos si está establecido
                if max_videos and videos_detected >= max_videos:
                    print(f"🏁 Alcanzado límite de {max_videos} videos")
                    break
                
                # Pequeña pausa para no saturar CPU
                await asyncio.sleep(5)
        
        except KeyboardInterrupt:
            print("\n🛑 Captura detenida por usuario")
        
        except Exception as e:
            print(f"❌ Error en captura segmentada: {e}")
        
        finally:
            await self._cleanup_capture()
            videos_detected = self.video_counter - 1
            print(f"📈 Total de videos detectados: {videos_detected}")
    
    async def _cleanup_capture(self):
        """
        Limpia recursos al finalizar la captura
        """
        print("🧹 Limpiando recursos...")
        
        self.is_capturing = False
        
        # Terminar proceso FFmpeg si está corriendo
        if self.ffmpeg_process and self.ffmpeg_process.returncode is None:
            print("🛑 Terminando proceso FFmpeg...")
            self.ffmpeg_process.terminate()
            
            try:
                # Esperar terminación graceful
                await asyncio.wait_for(self.ffmpeg_process.wait(), timeout=10)
                print("✅ FFmpeg terminado correctamente")
            except asyncio.TimeoutError:
                print("⚠️ Forzando terminación de FFmpeg...")
                self.ffmpeg_process.kill()
                await self.ffmpeg_process.wait()
        
        # Esperar a que termine el monitor de archivos
        if self.file_monitor_thread and self.file_monitor_thread.is_alive():
            print("📁 Esperando finalización del monitor...")
            self.file_monitor_thread.join(timeout=5)
        
        print("✅ Limpieza completada")
    
    # Métodos legacy para compatibilidad con código existente
    async def capture_video(self, duration_seconds=600):
        """
        Método legacy - ahora redirige a captura segmentada
        """
        print("⚠️ Usando captura segmentada en lugar de captura individual")
        await self.continuous_capture_segmented(duration_seconds, max_videos=1)
        
        # Esperar a que se genere al menos un archivo
        timeout = duration_seconds + 30  # Timeout con margen
        start_wait = time.time()
        
        while time.time() - start_wait < timeout:
            if not self.video_queue.empty():
                return self.video_queue.get()
            await asyncio.sleep(2)
        
        print("⚠️ Timeout esperando video")
        return None
    
    async def continuous_capture(self, duration_seconds=600, max_videos=None):
        """
        Método legacy - redirige a captura segmentada mejorada
        """
        print("🔄 Redirigiendo a captura segmentada sin gaps...")
        await self.continuous_capture_segmented(duration_seconds, max_videos)
    
    def get_capture_stats(self):
        """
        Obtiene estadísticas de la captura actual
        """
        return {
            "is_capturing": self.is_capturing,
            "videos_in_queue": self.video_queue.qsize(),
            "video_counter": self.video_counter,
            "ffmpeg_running": self.ffmpeg_process is not None and self.ffmpeg_process.returncode is None,
            "monitor_active": self.file_monitor_thread is not None and self.file_monitor_thread.is_alive()
        }
    
    def print_status(self):
        """
        Imprime el estado actual del sistema de captura
        """
        stats = self.get_capture_stats()
        print("\n📊 ESTADO DEL SISTEMA DE CAPTURA:")
        print(f"   🎥 Capturando: {'Sí' if stats['is_capturing'] else 'No'}")
        print(f"   🎬 FFmpeg activo: {'Sí' if stats['ffmpeg_running'] else 'No'}")
        print(f"   📁 Monitor activo: {'Sí' if stats['monitor_active'] else 'No'}")
        print(f"   📊 Videos en cola: {stats['videos_in_queue']}")
        print(f"   🔢 Contador: {stats['video_counter']}")