import cv2
import time
import json
from datetime import datetime
from pathlib import Path
from flexible_person_counter import FlexiblePersonCounter


class VideoProcessor:
    """
    Clase para procesar videos con el nuevo FlexiblePersonCounter
    Soporta líneas horizontales y verticales con configuración semántica
    INCLUYE FRAME SKIPPING DINÁMICO para optimización de rendimiento
    """
    
    def __init__(self, stats_dir="stats"):
        import config
        from config import (TARGET_WIDTH, ROTATION_ANGLE, LINE_ORIENTATION,
                           LINE_MARGIN, COUNTING_MODE, ENTRANCE_DIRECTION)
        
        # Obtener parámetros de línea según orientación
        try:
            DETECTION_LINE_X = getattr(config, 'DETECTION_LINE_X', None)
        except AttributeError:
            DETECTION_LINE_X = None
            
        try:
            DETECTION_LINE_Y = getattr(config, 'DETECTION_LINE_Y', None)
        except AttributeError:
            DETECTION_LINE_Y = None
            
        try:
            DETECTION_LINE_RATIO = getattr(config, 'DETECTION_LINE_RATIO', None)
        except AttributeError:
            DETECTION_LINE_RATIO = None
        
        # Determinar parámetros según orientación de línea
        if LINE_ORIENTATION.lower() == "vertical":
            detection_line_position = DETECTION_LINE_X
        else:
            detection_line_position = DETECTION_LINE_Y
        
        # Crear contador flexible con parámetros completos
        self.counter = FlexiblePersonCounter(
            target_width=TARGET_WIDTH,
            rotation_angle=ROTATION_ANGLE,
            line_orientation=LINE_ORIENTATION,
            detection_line_position=detection_line_position,
            detection_line_ratio=DETECTION_LINE_RATIO,
            line_margin=LINE_MARGIN,
            entrance_direction=ENTRANCE_DIRECTION,
            counting_mode=COUNTING_MODE
        )
        
        self.stats_dir = Path(stats_dir)
        self.stats_dir.mkdir(exist_ok=True)
        self.stats_file = self.stats_dir / "counting_stats.json"
        self.all_stats = []
        
        # Cargar estadísticas existentes
        if self.stats_file.exists():
            try:
                with open(self.stats_file, 'r') as f:
                    self.all_stats = json.load(f)
                print(f"📊 Cargadas {len(self.all_stats)} estadísticas previas")
            except:
                print("⚠️ No se pudieron cargar estadísticas previas, empezando limpio")
        
        # Mostrar información de configuración
        self._show_configuration_info()
    
    def _show_configuration_info(self):
        """Muestra información detallada de la configuración"""
        print("\n" + "="*60)
        print("🎯 CONFIGURACIÓN DEL SISTEMA DE CONTEO")
        print("="*60)
        
        # Información de línea
        if self.counter.line_calibrated:
            print("✅ Sistema configurado con línea de detección CALIBRADA")
        else:
            print("⚠️ Sistema usando línea de detección por DEFECTO")
            print("💡 Sugerencia: Ejecuta 'python line_calibrator.py' para calibrar")
        
        # Orientación y detección
        print(f"📏 Orientación de línea: {self.counter.line_orientation.upper()}")
        if self.counter.line_orientation == "vertical":
            print("   📐 Detecta movimiento HORIZONTAL (←→)")
        else:
            print("   📐 Detecta movimiento VERTICAL (↑↓)")
        
        # Modo de conteo
        print(f"📊 Modo de conteo: {self.counter.counting_mode.upper()}")
        if self.counter.counting_mode == "entrance_exit":
            print(f"🚪 Dirección de ENTRADA: {self.counter.entrance_direction.upper()}")
            if self.counter.line_orientation == "vertical":
                directions = "DERECHA" if self.counter.entrance_direction == "positive" else "IZQUIERDA"
            else:
                directions = "ABAJO" if self.counter.entrance_direction == "positive" else "ARRIBA"
            print(f"🚪 Personas que van hacia {directions} = ENTRAN")
        
        # Información de frame skipping
        if self.counter.enable_frame_skipping:
            print(f"⚡ Frame skipping: HABILITADO")
            print(f"   📊 Skip normal: {self.counter.default_frame_skip} (1 de cada {self.counter.default_frame_skip + 1})")
            print(f"   📊 Skip sin detecciones: {self.counter.no_detection_frame_skip} (1 de cada {self.counter.no_detection_frame_skip + 1})")
        else:
            print(f"⚡ Frame skipping: DESHABILITADO")
        
        print("="*60)
    
    def save_stats(self, video_name, stats):
        """Guarda estadísticas en archivo JSON"""
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
        """Procesa un video mostrando frames en vivo CON FRAME SKIPPING DINÁMICO"""
        video_path = Path(video_path)
        print(f"\n🎬 Procesando video EN VIVO: {video_path.name}")
        
        # Mostrar información de configuración
        config_info = []
        config_info.append(f"Línea: {self.counter.line_orientation}")
        config_info.append(f"Modo: {self.counter.counting_mode}")
        if self.counter.line_calibrated:
            config_info.append("CALIBRADA")
        else:
            config_info.append("DEFECTO")
        
        if self.counter.enable_frame_skipping:
            config_info.append(f"Skip: {self.counter.default_frame_skip}/{self.counter.no_detection_frame_skip}")
        else:
            config_info.append("Sin Skip")
        
        print(f"📏 Configuración: {' | '.join(config_info)}")
        
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
        print(f"👁️ Mostrando frames en vivo - Presiona 'q' para saltar, 'ESC' para salir")
        
        # Calcular delay para reproducir a velocidad original
        base_frame_delay = 1.0 / fps if fps > 0 else 0.033
        
        # Procesar frames
        frame_count = 0
        start_time = time.time()
        last_progress_time = start_time
        last_skip_info_time = start_time
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                
                # Procesar frame (con frame skipping interno)
                results, resized_frame = self.counter.process_frame(frame)
                annotated_frame = self.counter.draw_annotations(resized_frame, results)
                
                # Mostrar frame procesado en vivo
                if show_live:
                    window_title = f'🎯 Person Counter - {video_path.name}'
                    if self.counter.line_calibrated:
                        window_title += ' (CALIBRADA)'
                    if self.counter.line_orientation == "horizontal":
                        window_title += ' [HORIZONTAL]'
                    if self.counter.enable_frame_skipping:
                        window_title += f' [SKIP: {self.counter.skip_mode.upper()}]'
                    
                    cv2.imshow(window_title, annotated_frame)
                    
                    # Ajustar delay según frame skipping
                    # Si se saltaron frames, mostrar más rápido para compensar
                    current_delay = base_frame_delay
                    if self.counter.enable_frame_skipping and self.counter.current_frame_skip > 0:
                        # Reducir delay proporcionalmente al skip
                        current_delay = base_frame_delay / (self.counter.current_frame_skip + 1)
                    
                    # Control de teclado
                    key = cv2.waitKey(int(current_delay * 1000)) & 0xFF
                    if key == ord('q'):
                        print(f"⏭️ Saltando video {video_path.name}")
                        break
                    elif key == 27:  # ESC
                        print(f"🚪 Saliendo del procesamiento")
                        cap.release()
                        cv2.destroyAllWindows()
                        return "exit"
                
                # Mostrar progreso cada 5 segundos
                current_time = time.time()
                if current_time - last_progress_time >= 5.0:
                    progress = (frame_count / total_frames) * 100
                    elapsed = current_time - start_time
                    fps_processed = frame_count / elapsed if elapsed > 0 else 0
                    
                    # Estadísticas según modo de conteo
                    if self.counter.counting_mode == "entrance_exit":
                        stats_text = f"Entradas: {self.counter.count_entrance} | Salidas: {self.counter.count_exit}"
                    else:
                        if self.counter.line_orientation == "vertical":
                            stats_text = f"Derecha: {self.counter.count_positive} | Izquierda: {self.counter.count_negative}"
                        else:
                            stats_text = f"Abajo: {self.counter.count_positive} | Arriba: {self.counter.count_negative}"
                    
                    print(f"📈 {progress:.1f}% | Frame: {frame_count}/{total_frames} | "
                          f"FPS: {fps_processed:.1f} | {stats_text}")
                    
                    last_progress_time = current_time
                
                # Mostrar info de frame skipping cada 10 segundos
                if self.counter.enable_frame_skipping and current_time - last_skip_info_time >= 10.0:
                    skip_stats = self.counter.get_frame_skip_stats()
                    if skip_stats:
                        print(f"⚡ Skip: {skip_stats['current_mode']} | "
                              f"Eficiencia: {skip_stats['skip_percentage']:.1f}% | "
                              f"Cambios: {skip_stats['mode_changes']}")
                    last_skip_info_time = current_time
        
        except KeyboardInterrupt:
            print(f"\n🛑 Procesamiento detenido por usuario")
        
        finally:
            # Cleanup
            cap.release()
            if show_live:
                cv2.destroyAllWindows()
        
        # Estadísticas finales
        processing_time = time.time() - start_time
        stats = self.counter.get_stats()
        stats["processing_time_seconds"] = round(processing_time, 2)
        stats["total_frames"] = frame_count
        stats["fps_processed"] = round(frame_count / processing_time, 2) if processing_time > 0 else 0
        stats["video_duration_seconds"] = round(total_frames / fps, 2) if fps > 0 else 0
        
        # Mostrar resumen final
        print(f"\n✅ Procesamiento completado para {video_path.name}:")
        print(f"   🕒 Tiempo: {processing_time:.2f}s | Duración video: {stats['video_duration_seconds']:.2f}s")
        print(f"   ⚡ FPS procesados: {stats['fps_processed']:.2f}")
        print(f"   📏 Línea: {self.counter.line_orientation.upper()} {'(CALIBRADA)' if self.counter.line_calibrated else '(DEFECTO)'}")
        
        if self.counter.counting_mode == "entrance_exit":
            print(f"   🚪 ENTRADAS: {stats['entradas']} | SALIDAS: {stats['salidas']}")
            print(f"   👥 PERSONAS DENTRO: {stats['personas_dentro']}")
            print(f"   📊 TOTAL MOVIMIENTOS: {stats['total_movimientos']}")
        else:
            if self.counter.line_orientation == "vertical":
                print(f"   ➡️ DERECHA: {stats['derecha']} | ⬅️ IZQUIERDA: {stats['izquierda']}")
            else:
                print(f"   ⬇️ ABAJO: {stats['abajo']} | ⬆️ ARRIBA: {stats['arriba']}")
            print(f"   📊 TOTAL: {stats['total']}")
        
        if self.counter.detection_line:
            if self.counter.line_orientation == "vertical":
                print(f"   📍 Línea X: {self.counter.detection_line} (±{self.counter.line_margin}px)")
            else:
                print(f"   📍 Línea Y: {self.counter.detection_line} (±{self.counter.line_margin}px)")
        
        # Mostrar resumen de frame skipping
        if self.counter.enable_frame_skipping:
            self.counter.print_frame_skip_summary()
        
        # Guardar estadísticas
        self.save_stats(video_path.name, stats)
        
        # Borrar video procesado
        try:
            video_path.unlink()  # Elimina el archivo
            print(f"🗑️ Video eliminado: {video_path.name}")
        except Exception as e:
            print(f"⚠️ Error eliminando video {video_path.name}: {e}")
        
        return stats
    
    def get_summary_stats(self):
        """Obtiene estadísticas resumidas de todos los videos procesados"""
        if not self.all_stats:
            return None
        
        total_videos = len(self.all_stats)
        
        # Separar por modo de conteo
        entrance_exit_videos = [e for e in self.all_stats if e['stats'].get('counting_mode') == 'entrance_exit']
        directional_videos = [e for e in self.all_stats if e['stats'].get('counting_mode') == 'directional']
        
        # Contar líneas calibradas
        calibrated_videos = sum(1 for e in self.all_stats if e['stats'].get('line_calibrated', False))
        
        # Orientaciones
        vertical_videos = sum(1 for e in self.all_stats if e['stats'].get('line_orientation') == 'vertical')
        horizontal_videos = sum(1 for e in self.all_stats if e['stats'].get('line_orientation') == 'horizontal')
        
        # Estadísticas de frame skipping
        if summary['videos_con_frame_skipping'] > 0:
            print(f"\n⚡ ESTADÍSTICAS DE FRAME SKIPPING:")
            print(f"   📊 Videos con frame skipping: {summary['videos_con_frame_skipping']}")
            if 'promedio_eficiencia_skip' in summary:
                print(f"   📈 Eficiencia promedio: {summary['promedio_eficiencia_skip']:.2f}% frames saltados")
                print(f"   🚀 Mejora de rendimiento: {summary['mejora_rendimiento_promedio']}x más rápido")
                print(f"   ⚡ Total frames saltados: {summary.get('total_frames_saltados', 0):,}")
                print(f"   ✅ Total frames procesados: {summary.get('total_frames_procesados', 0):,}")
        
        # Estadísticas de entrada/salida
        if summary.get('total_entradas') is not None:
            print(f"\n🚪 ESTADÍSTICAS ENTRADA/SALIDA:")
            print(f"   ➡️ Total ENTRADAS: {summary['total_entradas']}")
            print(f"   ⬅️ Total SALIDAS: {summary['total_salidas']}")
            print(f"   👥 PERSONAS DENTRO: {summary['personas_dentro_actual']}")
            print(f"   📈 Total movimientos: {summary['total_movimientos']}")
        
        # Estadísticas direccionales
        if summary.get('total_direccion_positiva') is not None:
            print(f"\n📐 ESTADÍSTICAS DIRECCIONALES:")
            print(f"   ➡️⬇️ Dirección positiva: {summary['total_direccion_positiva']}")
            print(f"   ⬅️⬆️ Dirección negativa: {summary['total_direccion_negativa']}")
            print(f"   📊 Total direccional: {summary['total_direccional']}")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        if summary['videos_con_linea_defecto'] > 0:
            print(f"   • {summary['videos_con_linea_defecto']} videos usaron línea por defecto")
            print(f"   • Ejecuta 'python line_calibrator.py' para calibrar línea")
            print(f"   • Esto mejorará la precisión del conteo")
        
        if summary['videos_con_frame_skipping'] == 0:
            print(f"   • Frame skipping deshabilitado en todos los videos")
            print(f"   • Habilita ENABLE_FRAME_SKIPPING = True en config.py para mejor rendimiento")
        elif summary.get('promedio_eficiencia_skip', 0) < 20:
            print(f"   • Eficiencia de frame skipping baja ({summary.get('promedio_eficiencia_skip', 0):.1f}%)")
            print(f"   • Considera ajustar NO_DETECTION_FRAME_SKIP en config.py")
        
        if summary['videos_modo_direccional'] > 0 and summary['videos_modo_entrada_salida'] == 0:
            print(f"   • Considera usar COUNTING_MODE = 'entrance_exit' para mejor semántica")
        
        print("="*70) 
        skip_enabled_videos = sum(1 for e in self.all_stats if e['stats'].get('frame_skipping_enabled', False))
        
        summary = {
            "total_videos_procesados": total_videos,
            "videos_con_linea_calibrada": calibrated_videos,
            "videos_con_linea_defecto": total_videos - calibrated_videos,
            "videos_linea_vertical": vertical_videos,
            "videos_linea_horizontal": horizontal_videos,
            "videos_modo_entrada_salida": len(entrance_exit_videos),
            "videos_modo_direccional": len(directional_videos),
            "videos_con_frame_skipping": skip_enabled_videos,
            "ultima_actualizacion": datetime.now().isoformat()
        }
        
        # Estadísticas de frame skipping
        if skip_enabled_videos > 0:
            skip_videos = [e for e in self.all_stats if e['stats'].get('frame_skipping_enabled', False)]
            avg_skip_efficiency = sum(e['stats'].get('skip_efficiency_percent', 0) for e in skip_videos) / len(skip_videos)
            total_frames_skipped = sum(e['stats'].get('frames_skipped', 0) for e in skip_videos)
            total_frames_processed = sum(e['stats'].get('frames_processed', 0) for e in skip_videos)
            
            summary.update({
                "promedio_eficiencia_skip": round(avg_skip_efficiency, 2),
                "total_frames_saltados": total_frames_skipped,
                "total_frames_procesados": total_frames_processed,
                "mejora_rendimiento_promedio": round(100 / (100 - avg_skip_efficiency), 2) if avg_skip_efficiency < 100 else "∞"
            })
        
        # Estadísticas para modo entrada/salida
        if entrance_exit_videos:
            total_entradas = sum(e['stats'].get('entradas', 0) for e in entrance_exit_videos)
            total_salidas = sum(e['stats'].get('salidas', 0) for e in entrance_exit_videos)
            
            summary.update({
                "total_entradas": total_entradas,
                "total_salidas": total_salidas,
                "personas_dentro_actual": total_entradas - total_salidas,
                "total_movimientos": total_entradas + total_salidas
            })
        
        # Estadísticas para modo direccional
        if directional_videos:
            # Sumar según orientación
            total_positive = sum(e['stats'].get('derecha', 0) + e['stats'].get('abajo', 0) for e in directional_videos)
            total_negative = sum(e['stats'].get('izquierda', 0) + e['stats'].get('arriba', 0) for e in directional_videos)
            
            summary.update({
                "total_direccion_positiva": total_positive,  # derecha/abajo
                "total_direccion_negativa": total_negative,  # izquierda/arriba
                "total_direccional": total_positive + total_negative
            })
        
        return summary
    
    def print_summary(self):
        """Imprime resumen de estadísticas"""
        summary = self.get_summary_stats()
        if not summary:
            print("📊 No hay estadísticas disponibles")
            return
        
        print("\n" + "="*70)
        print("📊 RESUMEN GENERAL DE ESTADÍSTICAS")
        print("="*70)
        
        # Información general
        print(f"📹 Videos procesados: {summary['total_videos_procesados']}")
        print(f"📏 Con línea calibrada: {summary['videos_con_linea_calibrada']}")
        print(f"📏 Con línea por defecto: {summary['videos_con_linea_defecto']}")
        print(f"📐 Línea vertical: {summary['videos_linea_vertical']} | Horizontal: {summary['videos_linea_horizontal']}")
        print(f"📊 Modo entrada/salida: {summary['videos_modo_entrada_salida']} | Direccional: {summary['videos_modo_direccional']}")
        
        # Estadísticas de