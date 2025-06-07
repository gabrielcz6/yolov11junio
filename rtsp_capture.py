import asyncio
import subprocess
import os
import time
from datetime import datetime
from pathlib import Path
from queue import Queue
import threading
import re


class RTSPVideoCapture:
    """
    Clase para capturar videos del stream RTSP de manera continua sin gaps
    VERSIÓN ETERNA: Captura infinita con reinicio automático de FFmpeg
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
        
        # Gestión de archivos
        self.completed_files = set()
        self.detected_files = {}
        
        # Configuración para captura eterna
        self.min_file_age_seconds = 6
        self.file_stability_time = 3
        self.ffmpeg_restart_threshold = 30    # Segundos sin actividad antes de reiniciar FFmpeg
        self.last_activity_time = time.time()
        
        # Control de reinicio automático
        self.ffmpeg_restart_count = 0
        self.max_restart_attempts = 5
        self.restart_delay = 10  # Segundos entre reinicios
        
    def _get_output_pattern(self):
        """Genera el patrón de salida para segmentación"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return str(self.output_dir / f"video_{timestamp}_%03d.mp4")
    
    def _extract_segment_number(self, filename):
        """Extrae el número de segmento del nombre del archivo"""
        match = re.search(r'_(\d{3})\.mp4$', str(filename))
        return int(match.group(1)) if match else None
    
    def _get_highest_segment_number(self):
        """Obtiene el número de segmento más alto en el directorio"""
        try:
            mp4_files = list(self.output_dir.glob("*.mp4"))
            if not mp4_files:
                return -1
            
            max_segment = -1
            for file_path in mp4_files:
                segment_num = self._extract_segment_number(file_path.name)
                if segment_num is not None:
                    max_segment = max(max_segment, segment_num)
            
            return max_segment
        except Exception:
            return -1
    
    def _is_file_stable_without_opening(self, file_path):
        """Verifica si un archivo está estable SIN abrirlo"""
        try:
            if not file_path.exists():
                return False
            
            # Verificar antigüedad mínima
            file_age = time.time() - file_path.stat().st_mtime
            if file_age < self.min_file_age_seconds:
                return False
            
            # Verificar estabilidad de tamaño
            size1 = file_path.stat().st_size
            time.sleep(self.file_stability_time)
            
            if not file_path.exists():
                return False
                
            size2 = file_path.stat().st_size
            
            # El archivo está estable si no cambió de tamaño
            size_stable = size1 == size2
            
            # Verificar tamaño mínimo
            min_size = 50 * 1024  # 50KB mínimo
            size_adequate = size2 >= min_size
            
            return size_stable and size_adequate
            
        except Exception as e:
            print(f"⚠️ Error verificando estabilidad de {file_path.name}: {e}")
            return False
    
    def _monitor_new_files(self, duration_seconds):
        """
        Monitor de archivos para captura ETERNA
        Solo procesa archivos que NO sean el más reciente
        """
        print("📁 Iniciando monitor ETERNO (solo procesa archivos anteriores al último)...")
        
        while self.is_capturing:
            try:
                current_files = list(self.output_dir.glob("*.mp4"))
                files_processed_this_iteration = 0
                
                if len(current_files) == 0:
                    print("📁 No hay archivos en directorio, esperando...")
                    time.sleep(5)
                    continue
                
                # Obtener el archivo más reciente por número de segmento
                highest_segment = self._get_highest_segment_number()
                
                # REGLA CLAVE: Solo procesar archivos que NO sean el más reciente
                for file_path in current_files:
                    if file_path in self.completed_files:
                        continue
                    
                    segment_number = self._extract_segment_number(file_path.name)
                    
                    # NO procesar el archivo con el número más alto (más reciente)
                    if segment_number == highest_segment:
                        # Solo mostrar mensaje ocasionalmente para el último archivo
                        if self.video_counter % 20 == 0:  # Cada 20 iteraciones
                            print(f"⏸️ Archivo más reciente {file_path.name} (seg:{segment_number}) - manteniendo sin procesar")
                        continue
                    
                    # Procesar archivos anteriores
                    current_time = time.time()
                    
                    if file_path not in self.detected_files:
                        self.detected_files[file_path] = current_time
                        self.last_activity_time = current_time
                        print(f"🔍 Evaluando archivo anterior: {file_path.name} (seg:{segment_number})")
                        continue
                    
                    # Verificar tiempo desde detección
                    time_since_detection = current_time - self.detected_files[file_path]
                    if time_since_detection < self.min_file_age_seconds:
                        continue
                    
                    # Verificar estabilidad
                    if self._is_file_stable_without_opening(file_path):
                        print(f"✅ Procesando archivo: {file_path.name} (seg:{segment_number})")
                        self.video_queue.put(str(file_path))
                        self.completed_files.add(file_path)
                        self.video_counter += 1
                        files_processed_this_iteration += 1
                        self.last_activity_time = current_time
                        
                        if file_path in self.detected_files:
                            del self.detected_files[file_path]
                
                # Limpieza de archivos inexistentes
                existing_files = set(current_files)
                files_to_remove = [f for f in self.detected_files if f not in existing_files]
                for file_to_remove in files_to_remove:
                    del self.detected_files[file_to_remove]
                
                # Tiempo de espera dinámico
                if files_processed_this_iteration > 0:
                    sleep_time = 2  # Menos tiempo si hay actividad
                else:
                    sleep_time = 5  # Más tiempo si no hay actividad
                
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"⚠️ Error en monitor de archivos: {e}")
                time.sleep(5)
        
        print("📁 Monitor de archivos finalizado")
    
    async def _start_ffmpeg_process(self, duration_seconds, output_pattern):
        """Inicia el proceso FFmpeg"""
        cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', self.rtsp_url,
            '-f', 'segment',
            '-segment_time', str(duration_seconds),
            '-segment_format', 'mp4',
            '-reset_timestamps', '1',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-avoid_negative_ts', 'make_zero',
            '-rtbufsize', '100M',
            '-segment_list_flags', '+live',
            '-segment_wrap', '1000',          # NUEVO: Envolver después de 1000 segmentos
            '-segment_start_number', '0',     # NUEVO: Empezar desde 0
            output_pattern
        ]
        
        print(f"🎬 Iniciando FFmpeg proceso #{self.ffmpeg_restart_count + 1}...")
        
        self.ffmpeg_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        print(f"✅ FFmpeg iniciado (PID: {self.ffmpeg_process.pid})")
        return True
    
    async def _monitor_ffmpeg_health(self):
        """Monitorea la salud de FFmpeg y lo reinicia si es necesario"""
        print("🔍 Iniciando monitor de salud de FFmpeg...")
        
        while self.is_capturing:
            try:
                # Verificar si FFmpeg sigue corriendo
                if self.ffmpeg_process and self.ffmpeg_process.returncode is not None:
                    print(f"⚠️ FFmpeg terminó inesperadamente (código: {self.ffmpeg_process.returncode})")
                    
                    if self.ffmpeg_restart_count < self.max_restart_attempts:
                        print(f"🔄 Reiniciando FFmpeg ({self.ffmpeg_restart_count + 1}/{self.max_restart_attempts})...")
                        await self._restart_ffmpeg()
                    else:
                        print(f"❌ Máximo de reintentos alcanzado ({self.max_restart_attempts})")
                        self.is_capturing = False
                        break
                
                # Verificar actividad reciente
                time_since_activity = time.time() - self.last_activity_time
                if time_since_activity > self.ffmpeg_restart_threshold:
                    print(f"⏰ Sin actividad por {time_since_activity:.1f}s - FFmpeg puede estar colgado")
                    
                    # Solo reiniciar si FFmpeg sigue "corriendo" pero sin generar archivos
                    if (self.ffmpeg_process and 
                        self.ffmpeg_process.returncode is None and 
                        self.ffmpeg_restart_count < self.max_restart_attempts):
                        
                        print("🔄 Reiniciando FFmpeg por inactividad...")
                        await self._restart_ffmpeg()
                
                await asyncio.sleep(10)  # Verificar cada 10 segundos
                
            except Exception as e:
                print(f"⚠️ Error en monitor de salud: {e}")
                await asyncio.sleep(5)
        
        print("🔍 Monitor de salud finalizado")
    
    async def _restart_ffmpeg(self):
        """Reinicia el proceso FFmpeg"""
        try:
            # Terminar proceso actual
            if self.ffmpeg_process and self.ffmpeg_process.returncode is None:
                self.ffmpeg_process.terminate()
                try:
                    await asyncio.wait_for(self.ffmpeg_process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self.ffmpeg_process.kill()
                    await self.ffmpeg_process.wait()
            
            # Esperar antes de reiniciar
            await asyncio.sleep(self.restart_delay)
            
            # Generar nuevo patrón de salida
            output_pattern = self._get_output_pattern()
            
            # Incrementar contador de reinicio
            self.ffmpeg_restart_count += 1
            
            # Reiniciar
            await self._start_ffmpeg_process(15, output_pattern)  # Usar duración fija de 15s
            
            # Reset timer de actividad
            self.last_activity_time = time.time()
            
            print(f"✅ FFmpeg reiniciado exitosamente")
            
        except Exception as e:
            print(f"❌ Error reiniciando FFmpeg: {e}")
            self.ffmpeg_restart_count += 1
    
    def get_queue_status(self):
        """Estado del sistema eterno"""
        mp4_files = list(self.output_dir.glob("*.mp4"))
        highest_segment = self._get_highest_segment_number()
        time_since_activity = time.time() - self.last_activity_time
        
        return {
            "files_in_directory": len(mp4_files),
            "files_in_queue": self.video_queue.qsize(),
            "files_completed": len(self.completed_files),
            "files_being_tracked": len(self.detected_files),
            "highest_segment": highest_segment,
            "time_since_activity": round(time_since_activity, 1),
            "ffmpeg_restart_count": self.ffmpeg_restart_count,
            "ffmpeg_running": self.ffmpeg_process is not None and self.ffmpeg_process.returncode is None,
            "queue_lag": len(mp4_files) - self.video_queue.qsize() - len(self.completed_files) - 1  # -1 por el archivo actual
        }
    
    def print_detailed_status(self):
        """Estado detallado del sistema eterno"""
        status = self.get_queue_status()
        
        print(f"\n📊 ESTADO DEL SISTEMA ETERNO:")
        print(f"   📁 Archivos en directorio: {status['files_in_directory']}")
        print(f"   📋 Archivos en cola: {status['files_in_queue']}")
        print(f"   ✅ Archivos completados: {status['files_completed']}")
        print(f"   🔍 Archivos siendo evaluados: {status['files_being_tracked']}")
        print(f"   📺 Segmento más alto: {status['highest_segment']}")
        print(f"   🕒 Tiempo desde última actividad: {status['time_since_activity']}s")
        print(f"   🔄 Reinicios de FFmpeg: {status['ffmpeg_restart_count']}")
        print(f"   🎬 FFmpeg corriendo: {'Sí' if status['ffmpeg_running'] else 'No'}")
        print(f"   ⏱️ Retraso de cola: {status['queue_lag']} archivos")
        
        if self.detected_files:
            print(f"   📝 Archivos en evaluación:")
            current_time = time.time()
            for file_path, detection_time in list(self.detected_files.items())[:5]:  # Solo mostrar primeros 5
                age = current_time - detection_time
                segment_num = self._extract_segment_number(file_path.name)
                print(f"      • {file_path.name} (seg:{segment_num}) - {age:.1f}s")
    
    async def continuous_capture_segmented(self, duration_seconds=15, max_videos=None):
        """
        Captura ETERNA - ignora max_videos para ser verdaderamente infinita
        """
        self.is_capturing = True
        self.last_activity_time = time.time()
        self.ffmpeg_restart_count = 0
        
        print(f"🚀 Iniciando captura ETERNA de videos de {duration_seconds} segundos")
        print("♾️ MODO ETERNO - Captura infinita con reinicio automático")
        print("🔄 FFmpeg se reiniciará automáticamente si se detiene")
        
        # Ignorar max_videos para captura eterna
        if max_videos:
            print(f"⚠️ max_videos ({max_videos}) IGNORADO en modo eterno")
        
        output_pattern = self._get_output_pattern()
        print(f"📁 Patrón inicial: {output_pattern}")
        
        try:
            # Iniciar FFmpeg
            await self._start_ffmpeg_process(duration_seconds, output_pattern)
            
            # Iniciar monitor de archivos
            self.file_monitor_thread = threading.Thread(
                target=self._monitor_new_files,
                args=(duration_seconds,),
                daemon=True
            )
            self.file_monitor_thread.start()
            print("📁 Monitor de archivos ETERNO iniciado")
            
            # Iniciar monitor de salud de FFmpeg
            health_task = asyncio.create_task(self._monitor_ffmpeg_health())
            
            videos_detected = 0
            start_time = time.time()
            last_status_time = start_time
            last_detailed_status_time = start_time
            
            while self.is_capturing:
                current_time = time.time()
                
                # Estado básico cada 30 segundos
                if current_time - last_status_time >= 30:
                    elapsed = current_time - start_time
                    elapsed_hours = elapsed // 3600
                    elapsed_mins = (elapsed % 3600) // 60
                    
                    current_queue_size = self.video_queue.qsize()
                    videos_detected = self.video_counter - 1
                    
                    print(f"🔄 Estado ETERNO: {elapsed_hours:02.0f}:{elapsed_mins:02.0f} | "
                          f"Videos: {videos_detected} | Cola: {current_queue_size} | "
                          f"Reinicios: {self.ffmpeg_restart_count}")
                    
                    last_status_time = current_time
                
                # Estado detallado cada 2 minutos
                if current_time - last_detailed_status_time >= 120:
                    self.print_detailed_status()
                    last_detailed_status_time = current_time
                
                # En modo eterno, NUNCA parar por límite de videos
                # Solo parar por Ctrl+C o error fatal
                
                await asyncio.sleep(5)
            
            # Cancelar monitor de salud
            health_task.cancel()
        
        except KeyboardInterrupt:
            print("\n🛑 Captura ETERNA detenida por usuario")
        
        except Exception as e:
            print(f"❌ Error en captura eterna: {e}")
        
        finally:
            await self._cleanup_capture()
            videos_detected = self.video_counter - 1
            print(f"📈 Total de videos detectados en sesión eterna: {videos_detected}")
            
            final_status = self.get_queue_status()
            print(f"📊 Estado final: {final_status['files_in_directory']} archivos, "
                  f"{final_status['files_in_queue']} en cola, "
                  f"{final_status['ffmpeg_restart_count']} reinicios")
    
    async def _cleanup_capture(self):
        """Limpieza del sistema eterno"""
        print("🧹 Limpiando sistema eterno...")
        
        self.is_capturing = False
        
        if self.ffmpeg_process and self.ffmpeg_process.returncode is None:
            print("🛑 Terminando proceso FFmpeg...")
            self.ffmpeg_process.terminate()
            
            try:
                await asyncio.wait_for(self.ffmpeg_process.wait(), timeout=10)
                print("✅ FFmpeg terminado correctamente")
            except asyncio.TimeoutError:
                print("⚠️ Forzando terminación de FFmpeg...")
                self.ffmpeg_process.kill()
                await self.ffmpeg_process.wait()
        
        if self.file_monitor_thread and self.file_monitor_thread.is_alive():
            print("📁 Esperando finalización del monitor...")
            self.file_monitor_thread.join(timeout=8)
        
        print("✅ Limpieza completada")
    
    # Métodos legacy para compatibilidad
    async def capture_video(self, duration_seconds=600):
        """Método legacy - para una sola captura"""
        await self.continuous_capture_segmented(duration_seconds, max_videos=1)
        
        timeout = duration_seconds + 30
        start_wait = time.time()
        
        while time.time() - start_wait < timeout:
            if not self.video_queue.empty():
                return self.video_queue.get()
            await asyncio.sleep(2)
        
        return None
    
    async def continuous_capture(self, duration_seconds=600, max_videos=None):
        """Método legacy - redirige a captura eterna"""
        print("🔄 Redirigiendo a captura ETERNA...")
        await self.continuous_capture_segmented(duration_seconds, max_videos)
    
    def get_capture_stats(self):
        """Estadísticas del sistema eterno"""
        base_stats = {
            "is_capturing": self.is_capturing,
            "videos_in_queue": self.video_queue.qsize(),
            "video_counter": self.video_counter,
            "ffmpeg_running": self.ffmpeg_process is not None and self.ffmpeg_process.returncode is None,
            "monitor_active": self.file_monitor_thread is not None and self.file_monitor_thread.is_alive(),
            "mode": "ETERNAL"
        }
        
        queue_status = self.get_queue_status()
        base_stats.update(queue_status)
        
        return base_stats
    
    def print_status(self):
        """Estado actual del sistema eterno"""
        stats = self.get_capture_stats()
        print(f"\n📊 ESTADO DEL SISTEMA ETERNO:")
        print(f"   🎥 Capturando: {'Sí' if stats['is_capturing'] else 'No'}")
        print(f"   🎬 FFmpeg activo: {'Sí' if stats['ffmpeg_running'] else 'No'}")
        print(f"   📁 Monitor activo: {'Sí' if stats['monitor_active'] else 'No'}")
        print(f"   📊 Videos en cola: {stats['videos_in_queue']}")
        print(f"   📁 Archivos en directorio: {stats['files_in_directory']}")
        print(f"   ✅ Archivos completados: {stats['files_completed']}")
        print(f"   🔄 Reinicios FFmpeg: {stats['ffmpeg_restart_count']}")
        print(f"   🕒 Última actividad: {stats['time_since_activity']}s")
        print(f"   ♾️ Modo: ETERNO")
        print(f"   🔢 Contador: {stats['video_counter']}")