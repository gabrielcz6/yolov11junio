import asyncio
import subprocess
import time
from pathlib import Path

async def diagnose_ffmpeg_issue(rtsp_url, output_dir="videos"):
    """
    Función de diagnóstico para identificar por qué FFmpeg dejó de grabar
    """
    print("🔍 DIAGNÓSTICO DE FFMPEG")
    print("=" * 50)
    
    # 1. Verificar espacio en disco
    print("1. 💾 Verificando espacio en disco...")
    try:
        import shutil
        total, used, free = shutil.disk_usage(output_dir)
        free_gb = free // (1024**3)
        print(f"   ✅ Espacio libre: {free_gb} GB")
        if free_gb < 1:
            print("   ❌ PROBLEMA: Poco espacio en disco!")
    except Exception as e:
        print(f"   ⚠️ Error verificando disco: {e}")
    
    # 2. Verificar directorio de salida
    print("2. 📁 Verificando directorio...")
    output_path = Path(output_dir)
    try:
        # Intentar crear archivo de prueba
        test_file = output_path / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
        print("   ✅ Directorio escribible")
    except Exception as e:
        print(f"   ❌ PROBLEMA: No se puede escribir en directorio: {e}")
    
    # 3. Verificar conectividad RTSP
    print("3. 📡 Verificando conexión RTSP...")
    try:
        # Comando simple para probar conectividad
        cmd = [
            'ffprobe',
            '-rtsp_transport', 'tcp',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            rtsp_url
        ]
        
        print("   🔄 Probando conexión RTSP...")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
        
        if process.returncode == 0:
            print("   ✅ Conexión RTSP funcional")
            # Mostrar info del stream
            try:
                import json
                stream_info = json.loads(stdout.decode())
                streams = stream_info.get('streams', [])
                print(f"   📊 Streams detectados: {len(streams)}")
                for i, stream in enumerate(streams):
                    codec = stream.get('codec_name', 'unknown')
                    print(f"      Stream {i}: {codec}")
            except:
                print("   📊 Stream info no disponible")
        else:
            print("   ❌ PROBLEMA: No se puede conectar al RTSP")
            print(f"   Error: {stderr.decode()}")
            
    except asyncio.TimeoutError:
        print("   ❌ PROBLEMA: Timeout conectando al RTSP")
    except Exception as e:
        print(f"   ❌ PROBLEMA: Error verificando RTSP: {e}")
    
    # 4. Test de grabación corta
    print("4. 🎬 Probando grabación de 10 segundos...")
    try:
        test_output = output_path / f"test_recording_{int(time.time())}.mp4"
        
        cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', rtsp_url,
            '-t', '10',  # Solo 10 segundos
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-y',  # Sobrescribir
            str(test_output)
        ]
        
        print("   🔄 Iniciando grabación de prueba...")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=20)
        
        if process.returncode == 0 and test_output.exists():
            size_mb = test_output.stat().st_size / (1024*1024)
            print(f"   ✅ Grabación exitosa: {size_mb:.2f} MB")
            test_output.unlink()  # Limpiar
        else:
            print("   ❌ PROBLEMA: Grabación falló")
            print(f"   Error: {stderr.decode()}")
            
    except asyncio.TimeoutError:
        print("   ❌ PROBLEMA: Timeout en grabación de prueba")
    except Exception as e:
        print(f"   ❌ PROBLEMA: Error en grabación: {e}")
    
    # 5. Verificar procesos FFmpeg activos
    print("5. 🔍 Verificando procesos FFmpeg...")
    try:
        result = subprocess.run(['pgrep', '-f', 'ffmpeg'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"   📊 Procesos FFmpeg activos: {len(pids)}")
            for pid in pids:
                if pid:
                    print(f"      PID: {pid}")
        else:
            print("   ⚠️ No se encontraron procesos FFmpeg activos")
    except Exception as e:
        print(f"   ⚠️ Error verificando procesos: {e}")
    
    print("\n🎯 RECOMENDACIONES:")
    print("   1. Si hay problemas de RTSP: Verificar cámara/red")
    print("   2. Si hay problemas de disco: Liberar espacio")
    print("   3. Si FFmpeg está colgado: Reiniciar el proceso")
    print("   4. Si todo está OK: Puede ser timeout normal de stream")

# Ejecutar diagnóstico
if __name__ == "__main__":
    # Usar tu URL RTSP actual
    rtsp_url = "rtsp://admin:usuario1234@192.168.18.13:554/Streaming/channels/101?tcp"
    asyncio.run(diagnose_ffmpeg_issue(rtsp_url))