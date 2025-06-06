#!/usr/bin/env python3
"""
Sistema de Captura RTSP y Conteo de Personas con YOLOv11

Este sistema captura videos desde un stream RTSP y cuenta personas
que pasan hacia la derecha o izquierda usando detección por IA.

Autor: Tu Nombre
Fecha: 2024
"""

import asyncio
import subprocess
import sys
from pathlib import Path

# Importar módulos del sistema
from rtsp_system import RTSPSystem
from config import (
    RTSP_URL,
    VIDEO_DURATION_SECONDS,
    MAX_VIDEOS,
    PROCESS_VIDEOS,
    SHOW_PREVIEW
)


def check_dependencies():
    """
    Verifica que todas las dependencias estén instaladas
    """
    print("🔍 Verificando dependencias...")
    
    # Verificar FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, 
                              text=True)
        if result.returncode != 0:
            print("❌ FFmpeg no encontrado. Instala FFmpeg primero.")
            print("   Ubuntu/Debian: sudo apt install ffmpeg")
            print("   macOS: brew install ffmpeg")
            print("   Windows: Descarga desde https://ffmpeg.org/")
            return False
        else:
            print("✅ FFmpeg encontrado")
    except FileNotFoundError:
        print("❌ FFmpeg no encontrado. Instala FFmpeg primero.")
        return False
    
    # Verificar librerías Python
    required_packages = [
        'cv2',
        'numpy',
        'ultralytics',
        'pathlib'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} encontrado")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} no encontrado")
    
    if missing_packages:
        print(f"\n📦 Instala los paquetes faltantes:")
        print(f"   pip install {' '.join(missing_packages)}")
        if 'cv2' in missing_packages:
            print("   Para OpenCV: pip install opencv-python")
        return False
    
    return True


def show_configuration():
    """
    Muestra la configuración actual del sistema
    """
    print("\n⚙️  Configuración actual:")
    print(f"   📡 URL RTSP: {RTSP_URL}")
    print(f"   ⏱️  Duración por video: {VIDEO_DURATION_SECONDS} segundos")
    print(f"   📊 Máximo de videos: {MAX_VIDEOS}")
    print(f"   🤖 Procesamiento automático: {'Sí' if PROCESS_VIDEOS else 'No'}")
    print(f"   👁️  Mostrar preview: {'Sí' if SHOW_PREVIEW else 'No'}")


def create_directories():
    """
    Crea los directorios necesarios si no existen
    """
    directories = [
        "videos",
        "processed_videos"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("📁 Directorios creados/verificados")


async def main():
    """
    Función principal del sistema
    """
    print("🎯 Sistema de Captura RTSP y Conteo de Personas con YOLOv11")
    print("=" * 65)
    
    # Verificar dependencias
    if not check_dependencies():
        print("\n❌ Dependencias faltantes. Instálalas y vuelve a ejecutar.")
        sys.exit(1)
    
    # Mostrar configuración
    show_configuration()
    
    # Crear directorios necesarios
    create_directories()
    
    # Confirmar inicio
    print(f"\n🚀 ¿Iniciar el sistema? (presiona Enter para continuar, Ctrl+C para cancelar)")
    try:
        input()
    except KeyboardInterrupt:
        print("\n👋 Cancelado por usuario")
        sys.exit(0)
    
    # Crear y ejecutar sistema
    try:
        system = RTSPSystem(RTSP_URL)
        
        await system.run_capture_and_process(
            video_duration=VIDEO_DURATION_SECONDS,
            max_videos=MAX_VIDEOS,
            process_videos=PROCESS_VIDEOS,
            show_preview=SHOW_PREVIEW
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido por usuario")
    except Exception as e:
        print(f"\n❌ Error en el sistema: {e}")
        sys.exit(1)
    
    print("\n✅ Sistema finalizado correctamente")


if __name__ == "__main__":
    # Verificar versión de Python
    if sys.version_info < (3, 7):
        print("❌ Se requiere Python 3.7 o superior")
        sys.exit(1)
    
    # Ejecutar sistema
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Hasta luego!")
    except Exception as e:
        print(f"\n💥 Error fatal: {e}")
        sys.exit(1)
