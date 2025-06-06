import cv2
import time
import json
from datetime import datetime
from pathlib import Path
from person_counter import PersonCounter


class VideoProcessor:
    """
    Clase para procesar videos de manera asíncrona
    """
    
    def __init__(self, output_dir="processed_videos"):
        self.counter = PersonCounter()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.stats_file = self.output_dir / "counting_stats.json"
        self.all_stats = []
    
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
        
        with open(self.stats_file, 'w') as f:
            json.dump(self.all_stats, f, indent=2)
    
    def process_video(self, video_path, save_output=True, show_preview=False):
        """
        Procesa un video para contar personas
        """
        video_path = Path(video_path)
        print(f"\n🎬 Procesando video: {video_path.name}")
        
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
        
        # Configurar salida si se requiere
        output_video = None
        if save_output:
            output_path = self.output_dir / f"processed_{video_path.name}"
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            output_video = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
            print(f"💾 Guardando video procesado en: {output_path.name}")
        
        # Procesar frames
        frame_count = 0
        start_time = time.time()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Procesar frame
                results = self.counter.process_frame(frame)
                annotated_frame = self.counter.draw_annotations(frame, results)
                
                # Guardar frame procesado
                if output_video:
                    output_video.write(annotated_frame)
                
                # Mostrar preview si se requiere
                if show_preview:
                    cv2.imshow('Person Counter', annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                frame_count += 1
                
                # Progress cada 100 frames
                if frame_count % 100 == 0:
                    progress = (frame_count / total_frames) * 100
                    print(f"📈 Progreso: {progress:.1f}% ({frame_count}/{total_frames})")
        
        except KeyboardInterrupt:
            print("\n🛑 Procesamiento detenido por usuario")
        
        finally:
            # Cleanup
            cap.release()
            if output_video:
                output_video.release()
            if show_preview:
                cv2.destroyAllWindows()
        
        # Estadísticas finales
        processing_time = time.time() - start_time
        stats = self.counter.get_stats()
        stats["processing_time_seconds"] = round(processing_time, 2)
        stats["total_frames"] = frame_count
        stats["fps_processed"] = round(frame_count / processing_time, 2)
        
        print(f"\n✅ Procesamiento completado:")
        print(f"   🕒 Tiempo: {processing_time:.2f} segundos")
        print(f"   🎯 Personas hacia la derecha: {stats['derecha']}")
        print(f"   🎯 Personas hacia la izquierda: {stats['izquierda']}")
        print(f"   📊 Total de personas: {stats['total']}")
        print(f"   ⚡ FPS procesados: {stats['fps_processed']:.2f}")
        
        # Guardar estadísticas
        self.save_stats(video_path.name, stats)
        
        return stats
