import asyncio
from rtsp_capture import RTSPVideoCapture
from video_processor import VideoProcessor


class RTSPSystem:
    """
    Sistema principal que coordina captura y procesamiento en vivo
    """
    
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.capture_system = RTSPVideoCapture(rtsp_url)
        self.processor = VideoProcessor()
        self.processing_enabled = True
        self.exit_requested = False
    
    async def run_capture_and_process(self, video_duration=600, max_videos=None, 
                                    process_videos=True, show_live=True):
        """
        Ejecuta captura y procesamiento en paralelo
        """
        print("🚀 Iniciando sistema RTSP con conteo de personas EN VIVO")
        print(f"📡 URL RTSP: {self.rtsp_url}")
        print(f"⏱️  Duración por video: {video_duration} segundos")
        print(f"🤖 Procesamiento: {'Habilitado' if process_videos else 'Deshabilitado'}")
        print(f"👁️ Visualización en vivo: {'Habilitada' if show_live else 'Deshabilitada'}")
        print(f"💾 Videos procesados: NO se guardan (solo estadísticas)")
        
        # Crear tareas asíncronas
        tasks = []
        
        # Tarea de captura
        capture_task = asyncio.create_task(
            self.capture_system.continuous_capture(video_duration, max_videos)
        )
        tasks.append(capture_task)
        
        # Tarea de procesamiento si está habilitada
        if process_videos:
            process_task = asyncio.create_task(
                self._process_videos_live(show_live)
            )
            tasks.append(process_task)
        
        try:
            # Ejecutar todas las tareas
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n🛑 Sistema detenido por usuario")
            self.exit_requested = True
            # Cancelar tareas
            for task in tasks:
                task.cancel()
        
        # Mostrar resumen final
        self.processor.print_summary()
        print("👋 Sistema finalizado")
    
    async def _process_videos_live(self, show_live=True):
        """
        Procesa videos de la cola mostrándolos en vivo
        """
        print("🎬 Iniciando procesador de videos EN VIVO...")
        print("📖 Controles:")
        print("   - 'q': Saltar al siguiente video")
        print("   - 'ESC': Salir del procesamiento")
        print("   - Ctrl+C: Detener todo el sistema")
        
        processed_videos = 0
        
        while self.processing_enabled and not self.exit_requested:
            try:
                # Verificar si hay videos en la cola
                if not self.capture_system.video_queue.empty():
                    video_path = self.capture_system.video_queue.get()
                    processed_videos += 1
                    
                    print(f"\n🎯 Procesando video #{processed_videos}: {video_path}")
                    
                    # Procesar video en thread separado para no bloquear
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, 
                        self.processor.process_video_live, 
                        video_path, 
                        show_live
                    )
                    
                    # Si el usuario presionó ESC, salir
                    if result == "exit":
                        print("🚪 Saliendo del procesamiento por solicitud del usuario")
                        self.exit_requested = True
                        break
                    
                    # Pequeña pausa entre videos
                    if not self.exit_requested:
                        await asyncio.sleep(2)
                        
                else:
                    # Esperar un poco si no hay videos
                    await asyncio.sleep(3)
                    
            except Exception as e:
                print(f"❌ Error procesando video: {e}")
                await asyncio.sleep(5)
        
        print(f"🏁 Procesamiento finalizado. Videos procesados: {processed_videos}")
    
    async def process_existing_videos(self, videos_dir="videos", show_live=True):
        """
        Procesa videos existentes en el directorio
        """
        from pathlib import Path
        
        videos_dir = Path(videos_dir)
        if not videos_dir.exists():
            print(f"❌ Directorio {videos_dir} no existe")
            return
        
        # Buscar videos
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        video_files = []
        for ext in video_extensions:
            video_files.extend(videos_dir.glob(f'*{ext}'))
        
        if not video_files:
            print(f"❌ No se encontraron videos en {videos_dir}")
            return
        
        video_files.sort()  # Ordenar por nombre
        
        print(f"🎬 Encontrados {len(video_files)} videos para procesar")
        print("📖 Controles:")
        print("   - 'q': Saltar al siguiente video")
        print("   - 'ESC': Salir del procesamiento")
        
        processed_count = 0
        
        for video_file in video_files:
            if self.exit_requested:
                break
                
            processed_count += 1
            print(f"\n🎯 Procesando video {processed_count}/{len(video_files)}: {video_file.name}")
            
            # Procesar video
            result = self.processor.process_video_live(video_file, show_live)
            
            # Si el usuario presionó ESC, salir
            if result == "exit":
                print("🚪 Saliendo del procesamiento por solicitud del usuario")
                break
            
            # Pequeña pausa entre videos
            await asyncio.sleep(2)
        
        # Mostrar resumen final
        self.processor.print_summary()
        print(f"🏁 Procesamiento completado. {processed_count} videos procesados de {len(video_files)}")
