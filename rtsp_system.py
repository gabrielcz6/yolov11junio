import asyncio
from rtsp_capture import RTSPVideoCapture
from video_processor import VideoProcessor


class RTSPSystem:
    """
    Sistema principal que coordina captura y procesamiento
    """
    
    def __init__(self, rtsp_url):
        self.rtsp_url = rtsp_url
        self.capture_system = RTSPVideoCapture(rtsp_url)
        self.processor = VideoProcessor()
        self.processing_enabled = True
    
    async def run_capture_and_process(self, video_duration=600, max_videos=None, 
                                    process_videos=True, show_preview=False):
        """
        Ejecuta captura y procesamiento en paralelo
        """
        print("🚀 Iniciando sistema RTSP con conteo de personas")
        print(f"📡 URL RTSP: {self.rtsp_url}")
        print(f"⏱️  Duración por video: {video_duration} segundos")
        print(f"🤖 Procesamiento: {'Habilitado' if process_videos else 'Deshabilitado'}")
        
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
                self._process_videos_continuously(show_preview)
            )
            tasks.append(process_task)
        
        try:
            # Ejecutar todas las tareas
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n🛑 Sistema detenido por usuario")
            # Cancelar tareas
            for task in tasks:
                task.cancel()
        
        print("👋 Sistema finalizado")
    
    async def _process_videos_continuously(self, show_preview=False):
        """
        Procesa videos de la cola continuamente
        """
        print("🎬 Iniciando procesador de videos...")
        
        while self.processing_enabled:
            try:
                # Verificar si hay videos en la cola
                if not self.capture_system.video_queue.empty():
                    video_path = self.capture_system.video_queue.get()
                    
                    # Procesar video en thread separado para no bloquear
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None, 
                        self.processor.process_video, 
                        video_path, 
                        True,  # save_output
                        show_preview
                    )
                else:
                    # Esperar un poco si no hay videos
                    await asyncio.sleep(5)
                    
            except Exception as e:
                print(f"❌ Error procesando video: {e}")
                await asyncio.sleep(5)
