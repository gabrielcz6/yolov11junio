#!/usr/bin/env python3
"""
Sistema de Captura RTSP y Conteo de Personas con YOLOv11 - Visualización en Vivo

Este sistema captura videos desde un stream RTSP y cuenta personas
que pasan hacia la derecha o izquierda usando detección por IA.
Los videos se procesan mostrando frames en vivo SIN guardar videos procesados.

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
    SHOW_LIVE,
    VIDEOS_OUTPUT_DIR,
    STATS_OUTPUT_DIR,
    TARGET_WIDTH,
    ROTATION_ANGLE
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
    print(f"   👁️  Visualización en vivo: {'Sí' if SHOW_LIVE else 'No'}")
    print(f"   📐 Resolución objetivo: {TARGET_WIDTH}p")
    print(f"   🔄 Rotación: {ROTATION_ANGLE}°")
    print(f"   💾 Videos procesados guardados: NO (solo estadísticas)")
    print(f"   📁 Videos sin procesar: {VIDEOS_OUTPUT_DIR}/")
    print(f"   📊 Estadísticas: {STATS_OUTPUT_DIR}/")


def create_directories():
    """
    Crea los directorios necesarios si no existen
    """
    directories = [
        VIDEOS_OUTPUT_DIR,
        STATS_OUTPUT_DIR
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("📁 Directorios creados/verificados")


def show_menu():
    """
    Muestra el menú de opciones
    """
    print("\n🎯 ¿Qué deseas hacer?")
    print("1. 🚀 Capturar y procesar videos en vivo desde RTSP")
    print("2. 🎬 Procesar videos existentes (mostrar en vivo)")
    print("3. 📊 Ver estadísticas guardadas")
    print("4. 🚪 Salir")
    return input("\nElige una opción (1-4): ").strip()


async def capture_and_process_live():
    """
    Captura videos desde RTSP y los procesa en vivo
    """
    print("\n🚀 Iniciando captura y procesamiento en vivo...")
    
    try:
        system = RTSPSystem(RTSP_URL)
        
        await system.run_capture_and_process(
            video_duration=VIDEO_DURATION_SECONDS,
            max_videos=MAX_VIDEOS,
            process_videos=PROCESS_VIDEOS,
            show_live=SHOW_LIVE
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido por usuario")
    except Exception as e:
        print(f"\n❌ Error en el sistema: {e}")


async def process_existing_videos():
    """
    Procesa videos existentes mostrándolos en vivo
    """
    print(f"\n🎬 Procesando videos existentes en '{VIDEOS_OUTPUT_DIR}'...")
    
    try:
        system = RTSPSystem(RTSP_URL)  # URL no importa para procesar existentes
        await system.process_existing_videos(VIDEOS_OUTPUT_DIR, SHOW_LIVE)
        
    except KeyboardInterrupt:
        print("\n🛑 Procesamiento detenido por usuario")
    except Exception as e:
        print(f"\n❌ Error procesando videos: {e}")


def show_stats():
    """
    Muestra las estadísticas guardadas
    """
    from video_processor import VideoProcessor
    
    print("\n📊 Cargando estadísticas...")
    processor = VideoProcessor()
    processor.print_summary()
    
    # Mostrar estadísticas detalladas si hay datos
    if processor.all_stats:
        print(f"\n📋 Últimos 5 videos procesados:")
        for i, entry in enumerate(processor.all_stats[-5:], 1):
            stats = entry['stats']
            print(f"   {i}. {entry['video']}")
            print(f"      👥 Total: {stats['total']} | ➡️ {stats['derecha']} | ⬅️ {stats['izquierda']}")
            print(f"      🕒 {entry['processed_at'][:19].replace('T', ' ')}")


async def main():
    """
    Función principal del sistema
    """
    print("🎯 Sistema de Captura RTSP y Conteo de Personas con YOLOv11")
    print("📺 MODO: Procesamiento y Visualización EN VIVO")
    print("=" * 65)
    
    # Verificar dependencias
    if not check_dependencies():
        print("\n❌ Dependencias faltantes. Instálalas y vuelve a ejecutar.")
        sys.exit(1)
    
    # Mostrar configuración
    show_configuration()
    
    # Crear directorios necesarios
    create_directories()
    
    # Menú principal
    while True:
        try:
            choice = show_menu()
            
            if choice == '1':
                await capture_and_process_live()
            elif choice == '2':
                await process_existing_videos()
            elif choice == '3':
                show_stats()
            elif choice == '4':
                print("\n👋 ¡Hasta luego!")
                break
            else:
                print("❌ Opción inválida. Elige 1, 2, 3 o 4.")
            
            if choice in ['1', '2', '3']:
                input("\n⏸️  Presiona Enter para volver al menú...")
        
        except KeyboardInterrupt:
            print("\n👋 Cancelado por usuario")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            input("⏸️  Presiona Enter para continuar...")


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