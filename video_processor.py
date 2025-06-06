import cv2
import time
import json
from datetime import datetime
from pathlib import Path
from person_counter import PersonCounter


class VideoProcessor:
    """
    Clase para procesar videos mostrando frames en vivo sin guardar videos procesados
    """
    
    def __init__(self, stats_dir="stats"):
        from config import TARGET_WIDTH, ROTATION_ANGLE
        self.counter = PersonCounter(target_width=TARGET_WIDTH, rotation_angle=ROTATION_ANGLE)
        self.stats_dir = Path(stats_dir)
        self.stats_dir.mkdir(exist_ok=True)
        self.stats_file = self.stats_dir / "counting_stats.json"
        self.all_stats = []
        
        # Cargar estadísticas existentes si el archivo existe
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    self.all_stats = json.load(f)
                print(f"📊 Cargadas {len(self.all_stats)} estadísticas previas")
            except:
                print("⚠️ No se pudieron cargar estadísticas previas, empezando limpio")
    
    def save_stats(self, video_name, stats):
        """
        Guarda estadísticas en archivo JSON
        """
        stats_entry = {
            "video": video_name,
            "stats": stats,
            "processed_at": datetime.now().isoformat()
        }
        
        self.all_stats.append(stats_entry)
        
        try:
            with open(self.stats_file, 'w') as f:
                json.dump(self.all_stats, f, indent=2)
            print(f"💾 Estadísticas guardadas en {self.stats_file}")
        except Exception as e:
            print(f"❌ Error guardando estadísticas: {e}")
    
    def process_video_live(self, video_path, show_live=True):
        """
        Procesa un video mostrando frames en vivo SIN guardar video procesado
        """
        video_path = Path(video_path)
        print(f"\n🎬 Procesando video EN VIVO: {video_path.name}")
        
        # Reiniciar contadores para nuevo video
        self.counter.reset_counters()
        
        # Abrir video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"❌ Error abriendo video: {video_path}")
            return None
        
        # Propiedades del video
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"📊 Video info: {width}x{height} @ {fps}fps, {total_frames} frames")
        print(f"👁️ Mostrando frames en vivo - Presiona 'q' para saltar al siguiente, 'ESC' para salir")
        
        # Calcular delay para reproducir a velocidad original
        frame_delay = 1.0 / fps if fps > 0 else 0.033  # 30fps por defecto
        
        # Procesar frames
        frame_count = 0
        start_time = time.time()
        last_progress_time = start_time
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Procesar frame (ahora devuelve results y frame redimensionado)
                results, resized_frame = self.counter.process_frame(frame)
                annotated_frame = self.counter.draw_annotations(resized_frame, results)
                
                # Mostrar frame procesado en vivo
                if show_live:
                    cv2.imshow(f'🎯 Person Counter - {video_path.name}', annotated_frame)
                    
                    # Control de teclado
                    key = cv2.waitKey(int(frame_delay * 1000)) & 0xFF
                    if key == ord('q'):  # 'q' para saltar video
                        print(f"⏭️ Saltando video {video_path.name}")
                        break
                    elif key == 27:  # ESC para salir completamente
                        print(f"🚪 Saliendo del procesamiento")
                        cap.release()
                        cv2.destroyAllWindows()
                        return "exit"
                
                frame_count += 1
                
                # Mostrar progreso cada 5 segundos
                current_time = time.time()
                if current_time - last_progress_time >= 5.0:
                    progress = (frame_count / total_frames) * 100
                    elapsed = current_time - start_time
                    fps_processed = frame_count / elapsed if elapsed > 0 else 0
                    
                    print(f"📈 Progreso: {progress:.1f}% | "
                          f"Frame: {frame_count}/{total_frames} | "
                          f"FPS: {fps_processed:.1f} | "
                          f"Derecha: {self.counter.count_right} | "
                          f"Izquierda: {self.counter.count_left}")
                    
                    last_progress_time = current_time
        
        except KeyboardInterrupt:
            print(f"\n🛑 Procesamiento detenido por usuario")
        
        finally:
            # Cleanup
            cap.release()
            if show_live:
                cv2.destroyWindow(f'🎯 Person Counter - {video_path.name}')
        
        # Estadísticas finales
        processing_time = time.time() - start_time
        stats = self.counter.get_stats()
        stats["processing_time_seconds"] = round(processing_time, 2)
        stats["total_frames"] = frame_count
        stats["fps_processed"] = round(frame_count / processing_time, 2) if processing_time > 0 else 0
        stats["video_duration_seconds"] = round(total_frames / fps, 2) if fps > 0 else 0
        
        print(f"\n✅ Procesamiento completado para {video_path.name}:")
        print(f"   🕒 Tiempo de procesamiento: {processing_time:.2f} segundos")
        print(f"   📹 Duración del video: {stats['video_duration_seconds']:.2f} segundos")
        print(f"   🎯 Personas hacia la DERECHA: {stats['derecha']}")
        print(f"   🎯 Personas hacia la IZQUIERDA: {stats['izquierda']}")
        print(f"   📊 TOTAL de personas: {stats['total']}")
        print(f"   ⚡ FPS procesados: {stats['fps_processed']:.2f}")
        
        # Guardar estadísticas
        self.save_stats(video_path.name, stats)
        
        return stats
    
    def get_summary_stats(self):
        """
        Obtiene estadísticas resumidas de todos los videos procesados
        """
        if not self.all_stats:
            return None
        
        total_derecha = sum(entry['stats']['derecha'] for entry in self.all_stats)
        total_izquierda = sum(entry['stats']['izquierda'] for entry in self.all_stats)
        total_personas = total_derecha + total_izquierda
        total_videos = len(self.all_stats)
        
        summary = {
            "total_videos_procesados": total_videos,
            "total_personas_derecha": total_derecha,
            "total_personas_izquierda": total_izquierda,
            "total_personas_general": total_personas,
            "promedio_personas_por_video": round(total_personas / total_videos, 2) if total_videos > 0 else 0,
            "ultima_actualizacion": datetime.now().isoformat()
        }
        
        return summary
    
    def print_summary(self):
        """
        Imprime resumen de estadísticas
        """
        summary = self.get_summary_stats()
        if not summary:
            print("📊 No hay estadísticas disponibles")
            return
        
        print("\n" + "="*60)
        print("📊 RESUMEN GENERAL DE ESTADÍSTICAS")
        print("="*60)
        print(f"📹 Videos procesados: {summary['total_videos_procesados']}")
        print(f"➡️  Total personas hacia DERECHA: {summary['total_personas_derecha']}")
        print(f"⬅️  Total personas hacia IZQUIERDA: {summary['total_personas_izquierda']}")
        print(f"👥 TOTAL GENERAL de personas: {summary['total_personas_general']}")
        print(f"📈 Promedio por video: {summary['promedio_personas_por_video']}")
        print("="*60)