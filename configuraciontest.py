from config import *

def verificar_configuracion():
    
    
    print("🔧 CONFIGURACIÓN ACTUAL:")
    print("=" * 40)
    print(f"📏 LINE_ORIENTATION: {LINE_ORIENTATION}")
    print(f"📍 DETECTION_LINE_Y: {DETECTION_LINE_Y}")
    print(f"📍 DETECTION_LINE_X: {DETECTION_LINE_X}")
    print(f"📊 LINE_MARGIN: {LINE_MARGIN}")
    print(f"🎯 COUNTING_MODE: {COUNTING_MODE}")
    print(f"🚪 ENTRANCE_DIRECTION: {ENTRANCE_DIRECTION}")
    print(f"📏 DIRECTION_THRESHOLD: {DIRECTION_THRESHOLD}")
    print(f"🔄 ROTATION_ANGLE: {ROTATION_ANGLE}")
    print(f"📐 TARGET_WIDTH: {TARGET_WIDTH}")
    
    print("\n🧭 INTERPRETACIÓN:")
    if LINE_ORIENTATION == "horizontal":
        print("📐 Línea HORIZONTAL - detecta movimiento VERTICAL (↑↓)")
        print(f"📍 Línea en Y = {DETECTION_LINE_Y}")
        print(f"📏 Zona de detección: Y = {DETECTION_LINE_Y - LINE_MARGIN} a {DETECTION_LINE_Y + LINE_MARGIN}")
        
        if ENTRANCE_DIRECTION == "positive":
            print("🚪 ENTRADA = Personas que van hacia ABAJO (aumentando Y)")
            print("🚪 SALIDA = Personas que van hacia ARRIBA (disminuyendo Y)")
        else:
            print("🚪 ENTRADA = Personas que van hacia ARRIBA (disminuyendo Y)")
            print("🚪 SALIDA = Personas que van hacia ABAJO (aumentando Y)")
    else:
        print("📐 Línea VERTICAL - detecta movimiento HORIZONTAL (←→)")
        print(f"📍 Línea en X = {DETECTION_LINE_X}")
        print(f"📏 Zona de detección: X = {DETECTION_LINE_X - LINE_MARGIN} a {DETECTION_LINE_X + LINE_MARGIN}")
        
        if ENTRANCE_DIRECTION == "positive":
            print("🚪 ENTRADA = Personas que van hacia DERECHA (aumentando X)")
            print("🚪 SALIDA = Personas que van hacia IZQUIERDA (disminuyendo X)")
        else:
            print("🚪 ENTRADA = Personas que van hacia IZQUIERDA (disminuyendo X)")
            print("🚪 SALIDA = Personas que van hacia DERECHA (aumentando X)")
    
    print(f"\n⚠️ POSIBLES PROBLEMAS:")
    if DIRECTION_THRESHOLD > 40:
        print(f"❌ DIRECTION_THRESHOLD muy alto ({DIRECTION_THRESHOLD}) - personas lentas no se contarán")
    if LINE_MARGIN > 30:
        print(f"❌ LINE_MARGIN muy grande ({LINE_MARGIN}) - puede ser difícil cruzar")
    if ROTATION_ANGLE == 180:
        print(f"🔄 Con rotación 180°, las coordenadas pueden estar invertidas")
    
    print("=" * 40)

# Ejecutar verificación
verificar_configuracion()