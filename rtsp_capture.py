import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from queue import Queue


class RTSPVideoCapture:
    """
    Clase para capturar videos del stream RTSP de manera asíncrona
    """
    
    def __init__(self, rtsp_url, output_dir="videos"):
        self.rtsp_url = rtsp_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.video_queue = Queue()
        self.video_counter = 1
        self.is_capturing = False
        
    async def capture_video(self, duration_seconds=600):  # 10 minutos por defecto
        """
        Captura un solo video del stream RTSP usando ffmpeg
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"video{self.video_counter}_{timestamp}.mp4"
        
        # Comando ffmpeg para capturar
        cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', self.rtsp_url,
            '-t', str(duration_seconds),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-y',  # Sobrescribir archivo si existe
            str(output_file)
        ]
        
        print(f"🎥 Iniciando captura de video {self.video_counter}: {output_file.name}")
        print(f"⏱️  Duración: {duration_seconds} segundos")
        
        try:
            # Ejecutar ffmpeg de manera asíncrona
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print(f"✅ Video {self.video_counter} capturado exitosamente: {output_file.name}")
                # Agregar a la cola para procesamiento
                self.video_queue.put(str(output_file))
                self.video_counter += 1
                return str(output_file)
            else:
                print(f"❌ Error capturando video {self.video_counter}")
                print(f"Error: {stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"❌ Excepción durante captura: {e}")
            return None
    
    async def continuous_capture(self, duration_seconds=600, max_videos=None):
        """
        Captura videos continuamente
        """
        self.is_capturing = True
        videos_captured = 0
        
        print(f"🚀 Iniciando captura continua de videos de {duration_seconds} segundos")
        if max_videos:
            print(f"📊 Máximo de videos: {max_videos}")
        else:
            print("♾️  Captura infinita (Ctrl+C para detener)")
        
        try:
            while self.is_capturing:
                if max_videos and videos_captured >= max_videos:
                    print(f"🏁 Alcanzado límite de {max_videos} videos")
                    break
                
                video_path = await self.capture_video(duration_seconds)
                if video_path:
                    videos_captured += 1
                
                # Pequeña pausa entre capturas
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            print("\n🛑 Captura detenida por usuario")
        finally:
            self.is_capturing = False
            print(f"📈 Total de videos capturados: {videos_captured}")
