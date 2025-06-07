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
    VERSIÓN SIN REINICIO AUTOMÁTICO: FFmpeg corre hasta que termine naturalmente
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
        self.segment_duration = 15  # Valor por defecto
        self.secwithoutactivity = 120  # 2 minutos sin actividad
        
        # Gestión de archivos
        self.completed_files = set()
        self.detected_files = {}
        
        # Configuración optimizada para segmentos cortos
        self.min_file_age_seconds = 3       # Reducido para segmentos cortos
        self.file_stability_time = 1        # Reducido para mayor agilidad
        self.last_activity_time = time.time()
        
        # Control de reinicio automático
        self.auto_restart_count = 0
        self.max_auto_restarts_per_hour = 10  # Máximo 10 reinicios por hora
        self.last_restart_time = 0
        
        print("🚀 Sistema con FFmpeg ROBUSTO + Relanzamiento automático")
        print("📝 FFmpeg se reconectará automáticamente y se relanzará si termina")
        print("🔄 Máximo 10 reinicios automáticos por hora")
        
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
        Monitor de archivos SIMPLIFICADO - sin reinicio de FFmpeg
        Solo procesa archivos que NO sean el más reciente
        """
        print("📁 Iniciando monitor de archivos (SIN reinicio automático)...")
        
        while self.is_capturing:
            try:
                current_files = list(self.output_dir.glob("*.mp4"))
                
                files_processed_this_iteration = 0
                
                if len(current_files) == 0:
                    time.sleep(5)
                    continue
                
                # Obtener el archivo más reciente por número de segmento
                highest_segment = self._get_highest_segment_number()
                
                # REGLA CLAVE: Solo procesar archivos que NO sean el más reciente
                for file_path in current_files:
                    if file_path in self.completed_files:
                        continue
                    
                    segment_number = self._extract_segment_number(file_path.name)
                    
                    # NO procesar el archivo más reciente EXCEPTO si es muy viejo o único
                    if segment_number == highest_segment:
                        # EXCEPCIÓN 1: Si es el único archivo y es viejo, procesarlo
                        if len(current_files) == 1:
                            file_age = current_time - file_path.stat().st_mtime
                            if file_age > 45:  # Si tiene más de 45 segundos, procesarlo
                                print(f"🔓 Procesando archivo único viejo: {file_path.name} (age:{file_age:.1f}s)")
                            else:
                                continue
                        # EXCEPCIÓN 2: Si han pasado más de 3 minutos sin nuevos archivos
                        elif current_time - self.last_activity_time > 180:
                            print(f"🔓 Procesando por timeout: {file_path.name}")
                        else:
                            continue
                    
                    # Procesar archivos anteriores
                    current_time = time.time()
                    
                    if file_path not in self.detected_files:
                        self.detected_files[file_path] = current_time
                        self.last_activity_time = current_time
                        print(f"🔍 Evaluando archivo: {file_path.name} (seg:{segment_number})")
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
    
    async def _monitor_ffmpeg_logs(self, log_file):
        """Monitorea los logs de FFmpeg para detectar problemas"""
        try:
            await asyncio.sleep(5)  # Esperar que se cree el archivo
            
            if not log_file.exists():
                return
            
            last_size = 0
            no_activity_count = 0
            
            while self.is_capturing:
                try:
                    current_size = log_file.stat().st_size
                    
                    if current_size > last_size:
                        # Hay nueva actividad en logs
                        no_activity_count = 0
                        last_size = current_size
                        
                        # Leer últimas líneas para detectar errores
                        with open(log_file, 'r') as f:
                            f.seek(max(0, current_size - 1000))  # Últimos 1000 chars
                            recent_logs = f.read()
                            
                            # Detectar errores comunes
                            if "Connection refused" in recent_logs:
                                print("🚨 FFmpeg: Conexión rechazada por RTSP")
                            elif "timeout" in recent_logs.lower():
                                print("🚨 FFmpeg: Timeout de conexión")
                            elif "error" in recent_logs.lower():
                                print("🚨 FFmpeg: Error detectado en logs")
                    else:
                        no_activity_count += 1
                        
                        # Si no hay actividad en logs por mucho tiempo
                        if no_activity_count > 20:  # 20 * 5s = 100s sin logs
                            print("⚠️ FFmpeg: Sin actividad en logs por 100+ segundos")
                            no_activity_count = 0  # Reset
                    
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    print(f"⚠️ Error monitoreando logs: {e}")
                    await asyncio.sleep(10)
                    
        except Exception as e:
            print(f"⚠️ Error en monitor de logs: {e}")
    
    def _should_auto_restart(self):
        """Verifica si se puede hacer un reinicio automático"""
        current_time = time.time()
        
        # Reset contador cada hora
        if current_time - self.last_restart_time > 3600:  # 1 hora
            self.auto_restart_count = 0
        
        # Verificar límite
        if self.auto_restart_count >= self.max_auto_restarts_per_hour:
            print(f"⚠️ Límite de reinicios alcanzado ({self.auto_restart_count}/h)")
            print("🛑 Pausando reinicios automáticos por 1 hora")
            return False
        
        return True
    
    async def _auto_restart_ffmpeg(self, reason="terminación"):
        """Realiza reinicio automático con control de límites"""
        if not self._should_auto_restart():
            return False
        
        self.auto_restart_count += 1
        self.last_restart_time = time.time()
        
        print(f"🔄 Auto-reinicio #{self.auto_restart_count} por {reason}")
        
        # Generar nuevo patrón de salida
        output_pattern = self._get_output_pattern()
        
        try:
            await self._start_ffmpeg_process(self.segment_duration, output_pattern)
            self.last_activity_time = time.time()
            print(f"✅ FFmpeg auto-reiniciado exitosamente (#{self.auto_restart_count})")
            return True
        except Exception as e:
            print(f"❌ Error en auto-reinicio: {e}")
            return False

    async def _start_ffmpeg_process(self, duration_seconds, output_pattern):
        """Inicia el proceso FFmpeg - SIN sistema de reinicio"""
        cmd = [
            'ffmpeg',
            # Configuración RTSP básica y compatible
            '-rtsp_transport', 'tcp',
            '-i', self.rtsp_url,
            
            # Configuración de segmentación continua
            '-f', 'segment',
            '-segment_time', str(duration_seconds),
            '-segment_format', 'mp4',
            '-reset_timestamps', '1',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-avoid_negative_ts', 'make_zero',
            '-rtbufsize', '100M',
            '-segment_list_flags', '+live',
            '-segment_wrap', '0',              # Sin límite de segmentos
            '-segment_start_number', '0',
            
            # Output
            output_pattern
        ]
        
        print(f"🎬 Iniciando FFmpeg...")
        
        # Crear archivo de log para FFmpeg
        log_file = self.output_dir / f"ffmpeg_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        self.ffmpeg_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=open(log_file, 'w')  # Guardar errores en archivo
        )
        
        print(f"📝 Log de FFmpeg: {log_file}")
        
        # Crear tarea para monitorear logs en tiempo real
        asyncio.create_task(self._monitor_ffmpeg_logs(log_file))
        
        print(f"✅ FFmpeg iniciado (PID: {self.ffmpeg_process.pid})")
        print("📝 FFmpeg correrá sin interrupciones hasta finalización manual")
        return True
    
    def get_queue_status(self):
        """Estado del sistema simplificado"""
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
            "ffmpeg_running": self.ffmpeg_process is not None and self.ffmpeg_process.returncode is None,
            "queue_lag": len(mp4_files) - self.video_queue.qsize() - len(self.completed_files) - 1
        }
    
    def print_detailed_status(self):
        """Estado detallado del sistema"""
        status = self.get_queue_status()
        
        print(f"\n📊 ESTADO DEL SISTEMA (SIN REINICIO):")
        print(f"   📁 Archivos en directorio: {status['files_in_directory']}")
        print(f"   📋 Archivos en cola: {status['files_in_queue']}")
        print(f"   ✅ Archivos completados: {status['files_completed']}")
        print(f"   🔍 Archivos siendo evaluados: {status['files_being_tracked']}")
        print(f"   📺 Segmento más alto: {status['highest_segment']}")
        print(f"   🕒 Tiempo desde última actividad: {status['time_since_activity']}s")
        print(f"   🎬 FFmpeg corriendo: {'Sí' if status['ffmpeg_running'] else 'No'}")
        print(f"   ⏱️ Retraso de cola: {status['queue_lag']} archivos")
        
        if self.detected_files:
            print(f"   📝 Archivos en evaluación:")
            current_time = time.time()
            for file_path, detection_time in list(self.detected_files.items())[:5]:
                age = current_time - detection_time
                segment_num = self._extract_segment_number(file_path.name)
                print(f"      • {file_path.name} (seg:{segment_num}) - {age:.1f}s")
    
    async def continuous_capture_segmented(self, duration_seconds=15, max_videos=None):
        """
        Captura continua SIN reinicio automático de FFmpeg
        """
        self.is_capturing = True
        self.segment_duration = duration_seconds
        self.last_activity_time = time.time()
        
        print(f"🚀 Iniciando captura continua de videos de {duration_seconds} segundos")
        print("📝 MODO SIN REINICIO - FFmpeg correrá hasta finalización manual")
        print("🔄 NO habrá reinicio automático de FFmpeg")
        
        # Ignorar max_videos para captura continua
        if max_videos:
            print(f"⚠️ max_videos ({max_videos}) IGNORADO en modo continuo")
        
        output_pattern = self._get_output_pattern()
        print(f"📁 Patrón de salida: {output_pattern}")
        
        try:
            # Iniciar FFmpeg UNA SOLA VEZ
            await self._start_ffmpeg_process(self.segment_duration, output_pattern)
            
            # Iniciar monitor de archivos
            self.file_monitor_thread = threading.Thread(
                target=self._monitor_new_files,
                args=(duration_seconds,),
                daemon=True
            )
            self.file_monitor_thread.start()
            print("📁 Monitor de archivos iniciado")
            
            videos_detected = 0
            start_time = time.time()
            last_status_time = start_time
            last_detailed_status_time = start_time
            
            while self.is_capturing:
                current_time = time.time()
                
                # Verificar si FFmpeg terminó (solo para información, NO para reiniciar)
                if self.ffmpeg_process and self.ffmpeg_process.returncode is not None:
                    print(f"ℹ️ FFmpeg terminó (código: {self.ffmpeg_process.returncode})")
                    print("📝 Continuando con archivos existentes hasta Ctrl+C")
                    # NO reiniciamos automáticamente
                
                # NUEVA LÓGICA: Relanzamiento automático inteligente
                if self.ffmpeg_process and self.ffmpeg_process.returncode is not None:
                    print(f"🔄 FFmpeg terminó (código: {self.ffmpeg_process.returncode})")
                    
                    # Esperar un momento
                    await asyncio.sleep(3)
                    
                    # Intentar auto-reinicio
                    restart_success = await self._auto_restart_ffmpeg("terminación")
                    if not restart_success:
                        print("❌ Auto-reinicio falló o límite alcanzado")
                        print("💡 Usa Ctrl+C + 'python main.py' para reinicio manual")
                
                # DETECTAR INACTIVIDAD Y RELANZAR
                time_since_activity = current_time - self.last_activity_time
                if (time_since_activity > self.secwithoutactivity and  # 2 minutos sin actividad
                    self.ffmpeg_process and 
                    self.ffmpeg_process.returncode is None):
                    
                    print(f"🚨 Inactividad: {time_since_activity/60:.1f} min sin archivos")
                    
                    # Terminar proceso actual
                    self.ffmpeg_process.terminate()
                    try:
                        await asyncio.wait_for(self.ffmpeg_process.wait(), timeout=5)
                    except asyncio.TimeoutError:
                        self.ffmpeg_process.kill()
                        await self.ffmpeg_process.wait()
                    
                    # Auto-reinicio por inactividad
                    await asyncio.sleep(3)
                    restart_success = await self._auto_restart_ffmpeg("inactividad")
                    if not restart_success:
                        print("❌ Auto-reinicio por inactividad falló")
                
                # Estado básico cada 30 segundos
                if current_time - last_status_time >= 30:
                    elapsed = current_time - start_time
                    elapsed_hours = elapsed // 3600
                    elapsed_mins = (elapsed % 3600) // 60
                    
                    current_queue_size = self.video_queue.qsize()
                    videos_detected = self.video_counter - 1
                    
                    ffmpeg_status = "Activo" if (self.ffmpeg_process and self.ffmpeg_process.returncode is None) else "Terminado"
                    
                    print(f"🔄 Estado: {elapsed_hours:02.0f}:{elapsed_mins:02.0f} | "
                          f"Videos: {videos_detected} | Cola: {current_queue_size} | "
                          f"FFmpeg: {ffmpeg_status}")
                    
                    last_status_time = current_time
                
                # Estado detallado cada 2 minutos
                if current_time - last_detailed_status_time >= 120:
                    self.print_detailed_status()
                    last_detailed_status_time = current_time
                
                await asyncio.sleep(5)
        
        except KeyboardInterrupt:
            print("\n🛑 Captura detenida por usuario")
        
        except Exception as e:
            print(f"❌ Error en captura: {e}")
        
        finally:
            await self._cleanup_capture()
            videos_detected = self.video_counter - 1
            print(f"📈 Total de videos detectados: {videos_detected}")
            
            final_status = self.get_queue_status()
            print(f"📊 Estado final: {final_status['files_in_directory']} archivos, "
                  f"{final_status['files_in_queue']} en cola")
    
    async def _cleanup_capture(self):
        """Limpieza del sistema"""
        print("🧹 Limpiando sistema...")
        
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
        """Método legacy - redirige a captura continua"""
        print("🔄 Redirigiendo a captura continua SIN reinicio...")
        await self.continuous_capture_segmented(duration_seconds, max_videos)
    
    def get_capture_stats(self):
        """Estadísticas del sistema"""
        base_stats = {
            "is_capturing": self.is_capturing,
            "videos_in_queue": self.video_queue.qsize(),
            "video_counter": self.video_counter,
            "ffmpeg_running": self.ffmpeg_process is not None and self.ffmpeg_process.returncode is None,
            "monitor_active": self.file_monitor_thread is not None and self.file_monitor_thread.is_alive(),
            "mode": "CONTINUOUS_NO_RESTART"
        }
        
        queue_status = self.get_queue_status()
        base_stats.update(queue_status)
        
        return base_stats
    
    def print_status(self):
        """Estado actual del sistema"""
        stats = self.get_capture_stats()
        print(f"\n📊 ESTADO DEL SISTEMA (SIN REINICIO):")
        print(f"   🎥 Capturando: {'Sí' if stats['is_capturing'] else 'No'}")
        print(f"   🎬 FFmpeg activo: {'Sí' if stats['ffmpeg_running'] else 'No'}")
        print(f"   📁 Monitor activo: {'Sí' if stats['monitor_active'] else 'No'}")
        print(f"   📊 Videos en cola: {stats['videos_in_queue']}")
        print(f"   📁 Archivos en directorio: {stats['files_in_directory']}")
        print(f"   ✅ Archivos completados: {stats['files_completed']}")
        print(f"   🕒 Última actividad: {stats['time_since_activity']}s")
        print(f"   📝 Modo: CONTINUO SIN REINICIO")
        print(f"   🔢 Contador: {stats['video_counter']}")