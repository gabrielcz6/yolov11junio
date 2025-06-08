#!/usr/bin/env python3
"""
Generador de reporte PDF para análisis de videos
Crea un reporte profesional con gráficos y estadísticas
"""

import json
from datetime import datetime
from collections import defaultdict
import statistics
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

def install_requirements():
    """Instala las dependencias necesarias"""
    import subprocess
    import sys
    
    packages = ['reportlab', 'matplotlib', 'seaborn']
    
    for package in packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Instalando {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ {package} instalado correctamente")

def load_data(filename):
    """Carga los datos desde el archivo JSON"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {filename}")
        return None
    except json.JSONDecodeError:
        print(f"❌ Error: El archivo {filename} no es un JSON válido")
        return None

def analyze_data(data):
    """Analiza los datos y genera estadísticas"""
    if not data:
        return None
    
    total_videos = len(data)
    
    # Métricas principales
    entradas_total = sum(item['stats']['entradas'] for item in data)
    salidas_total = sum(item['stats']['salidas'] for item in data)
    movimientos_total = sum(item['stats']['total_movimientos'] for item in data)
    
    # Eficiencia y rendimiento
    skip_efficiencies = [item['stats']['skip_efficiency_percent'] for item in data]
    processing_times = [item['stats']['processing_time_seconds'] for item in data]
    fps_processed = [item['stats']['fps_processed'] for item in data]
    
    # Análisis por modo
    frame_skip_modes = defaultdict(int)
    for item in data:
        mode = item['stats']['frame_skip_mode']
        frame_skip_modes[mode] += 1
    
    # Videos con actividad
    videos_con_movimiento = [item for item in data if item['stats']['total_movimientos'] > 0]
    
    # Análisis temporal
    timestamps = [datetime.fromisoformat(item['stats']['timestamp'].replace('Z', '+00:00')) 
                 for item in data]
    duracion_sesion = (max(timestamps) - min(timestamps)).total_seconds() / 60
    
    # Datos para gráficos
    timeline_data = []
    for item in data:
        time = datetime.fromisoformat(item['stats']['timestamp'].replace('Z', '+00:00'))
        timeline_data.append({
            'tiempo': time.strftime('%H:%M'),
            'entradas': item['stats']['entradas'],
            'salidas': item['stats']['salidas'],
            'eficiencia': item['stats']['skip_efficiency_percent']
        })
    
    return {
        'general': {
            'total_videos': total_videos,
            'duracion_sesion_minutos': round(duracion_sesion, 2),
            'periodo': f"{min(timestamps).strftime('%H:%M:%S')} - {max(timestamps).strftime('%H:%M:%S')}",
            'fecha': min(timestamps).strftime('%d/%m/%Y')
        },
        'conteo_personas': {
            'total_entradas': entradas_total,
            'total_salidas': salidas_total,
            'total_movimientos': movimientos_total,
            'balance_personas': entradas_total - salidas_total
        },
        'rendimiento': {
            'eficiencia_promedio': round(statistics.mean(skip_efficiencies), 2),
            'eficiencia_min': round(min(skip_efficiencies), 2),
            'eficiencia_max': round(max(skip_efficiencies), 2),
            'tiempo_procesamiento_promedio': round(statistics.mean(processing_times), 2),
            'fps_promedio': round(statistics.mean(fps_processed), 2),
            'skip_efficiencies': skip_efficiencies,
            'processing_times': processing_times
        },
        'configuracion': {
            'resolucion': data[0]['stats']['resolution'],
            'angulo_rotacion': data[0]['stats']['rotation_angle'],
            'posicion_linea_deteccion': data[0]['stats']['detection_line_position'],
            'margen_linea': data[0]['stats']['line_margin']
        },
        'modos_salto_frames': dict(frame_skip_modes),
        'actividad': {
            'videos_con_movimiento': len(videos_con_movimiento),
            'videos_sin_movimiento': total_videos - len(videos_con_movimiento),
            'porcentaje_actividad': round((len(videos_con_movimiento) / total_videos) * 100, 2)
        },
        'timeline_data': timeline_data,
        'raw_data': data
    }

def create_charts(analysis):
    """Crea gráficos usando matplotlib"""
    charts = {}
    
    # Configurar estilo
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
    # 1. Gráfico de barras - Entradas vs Salidas
    fig, ax = plt.subplots(figsize=(8, 6))
    categories = ['Entradas', 'Salidas', 'Balance']
    values = [
        analysis['conteo_personas']['total_entradas'],
        analysis['conteo_personas']['total_salidas'],
        analysis['conteo_personas']['balance_personas']
    ]
    colors_bar = ['#2E8B57', '#DC143C', '#4169E1']
    
    bars = ax.bar(categories, values, color=colors_bar, alpha=0.8, edgecolor='black', linewidth=1)
    ax.set_title('Conteo de Personas - Resumen General', fontsize=16, fontweight='bold', pad=20)
    ax.set_ylabel('Número de Personas', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    # Añadir valores encima de las barras
    for bar, value in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{value}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    charts['conteo_barras'] = fig
    plt.close()
    
    # 2. Gráfico circular - Modos de salto de frames
    fig, ax = plt.subplots(figsize=(8, 8))
    modes = list(analysis['modos_salto_frames'].keys())
    counts = list(analysis['modos_salto_frames'].values())
    colors_pie = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    wedges, texts, autotexts = ax.pie(counts, labels=modes, autopct='%1.1f%%', 
                                     colors=colors_pie, startangle=90,
                                     explode=[0.05] * len(modes))
    
    ax.set_title('Distribución de Modos de Salto de Frames', fontsize=16, fontweight='bold', pad=20)
    
    # Mejorar la legibilidad
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    plt.tight_layout()
    charts['modos_pie'] = fig
    plt.close()
    
    # 3. Histograma - Eficiencia de procesamiento
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.hist(analysis['rendimiento']['skip_efficiencies'], bins=10, 
            color='#4CAF50', alpha=0.7, edgecolor='black', linewidth=1)
    ax.set_title('Distribución de Eficiencia de Procesamiento', fontsize=16, fontweight='bold', pad=20)
    ax.set_xlabel('Eficiencia (%)', fontsize=12)
    ax.set_ylabel('Frecuencia', fontsize=12)
    ax.grid(True, alpha=0.3)
    
    # Línea vertical para el promedio
    avg_eff = analysis['rendimiento']['eficiencia_promedio']
    ax.axvline(avg_eff, color='red', linestyle='--', linewidth=2, 
               label=f'Promedio: {avg_eff}%')
    ax.legend()
    
    plt.tight_layout()
    charts['eficiencia_hist'] = fig
    plt.close()
    
    return charts

def save_chart_to_bytes(fig):
    """Convierte un gráfico matplotlib a bytes para ReportLab"""
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=300, bbox_inches='tight')
    img_buffer.seek(0)
    return img_buffer

def create_pdf_report(analysis, output_filename):
    """Crea el reporte PDF profesional"""
    
    # Crear documento
    doc = SimpleDocTemplate(output_filename, pagesize=A4,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        textColor=colors.darkgreen,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=12,
        fontName='Helvetica'
    )
    
    # Contenido del documento
    story = []
    
    # Título principal
    story.append(Paragraph("📊 REPORTE DE ANÁLISIS DE VIDEOS", title_style))
    story.append(Paragraph("Sistema de Conteo de Personas", styles['Heading3']))
    story.append(Spacer(1, 20))
    
    # Información de la sesión
    info_data = [
        ['📅 Fecha:', analysis['general']['fecha']],
        ['⏰ Período:', analysis['general']['periodo']],
        ['📹 Videos procesados:', str(analysis['general']['total_videos'])],
        ['⏱️ Duración sesión:', f"{analysis['general']['duracion_sesion_minutos']} minutos"]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 3*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 30))
    
    # Resumen ejecutivo
    story.append(Paragraph("🎯 RESUMEN EJECUTIVO", subtitle_style))
    
    executive_summary = f"""
    Durante esta sesión de monitoreo se procesaron <b>{analysis['general']['total_videos']} videos</b> 
    con una duración total de <b>{analysis['general']['duracion_sesion_minutos']} minutos</b>. 
    El sistema registró <b>{analysis['conteo_personas']['total_entradas']} entradas</b> y 
    <b>{analysis['conteo_personas']['total_salidas']} salidas</b>, resultando en un balance neto de 
    <b>{analysis['conteo_personas']['balance_personas']} personas</b>. 
    
    La eficiencia promedio de procesamiento fue del <b>{analysis['rendimiento']['eficiencia_promedio']}%</b>, 
    con un <b>{analysis['actividad']['porcentaje_actividad']}%</b> de los videos mostrando actividad detectada.
    """
    
    story.append(Paragraph(executive_summary, normal_style))
    story.append(Spacer(1, 20))
    
    # Métricas principales
    story.append(Paragraph("📈 MÉTRICAS PRINCIPALES", subtitle_style))
    
    metrics_data = [
        ['Métrica', 'Valor', 'Descripción'],
        ['👥 Total Entradas', str(analysis['conteo_personas']['total_entradas']), 'Personas que ingresaron'],
        ['🚪 Total Salidas', str(analysis['conteo_personas']['total_salidas']), 'Personas que salieron'],
        ['⚖️ Balance Neto', str(analysis['conteo_personas']['balance_personas']), 'Diferencia entre entradas y salidas'],
        ['🎯 Movimientos Totales', str(analysis['conteo_personas']['total_movimientos']), 'Total de detecciones'],
        ['⚡ Eficiencia Promedio', f"{analysis['rendimiento']['eficiencia_promedio']}%", 'Optimización de procesamiento'],
        ['🎬 FPS Procesados', f"{analysis['rendimiento']['fps_promedio']}", 'Frames por segundo promedio']
    ]
    
    metrics_table = Table(metrics_data, colWidths=[2*inch, 1.5*inch, 2.5*inch])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(metrics_table)
    story.append(Spacer(1, 30))
    
    # Configuración del sistema
    story.append(Paragraph("⚙️ CONFIGURACIÓN DEL SISTEMA", subtitle_style))
    
    config_data = [
        ['Parámetro', 'Valor'],
        ['📺 Resolución', analysis['configuracion']['resolucion']],
        ['🔄 Ángulo de rotación', f"{analysis['configuracion']['angulo_rotacion']}°"],
        ['📏 Posición línea detección', str(analysis['configuracion']['posicion_linea_deteccion'])],
        ['📐 Margen de línea', str(analysis['configuracion']['margen_linea'])]
    ]
    
    config_table = Table(config_data, colWidths=[3*inch, 2*inch])
    config_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    
    story.append(config_table)
    story.append(Spacer(1, 20))
    
    # Generar gráficos
    print("📊 Generando gráficos...")
    charts = create_charts(analysis)
    
    # Añadir gráficos al PDF
    if charts:
        story.append(Paragraph("📊 ANÁLISIS GRÁFICO", subtitle_style))
        
        for chart_name, fig in charts.items():
            chart_buffer = save_chart_to_bytes(fig)
            
            # Crear imagen para ReportLab
            from reportlab.platypus import Image as RLImage
            chart_img = RLImage(chart_buffer, width=6*inch, height=4*inch)
            story.append(chart_img)
            story.append(Spacer(1, 20))
    
    # Pie de página con timestamp
    story.append(Spacer(1, 30))
    footer_text = f"Reporte generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.grey
    )
    story.append(Paragraph(footer_text, footer_style))
    
    # Construir PDF
    print("📝 Generando PDF...")
    doc.build(story)
    print(f"✅ Reporte PDF generado: {output_filename}")

def main():
    """Función principal"""
    print("🎬 Generador de Reporte PDF - Análisis de Videos")
    print("=" * 50)
    
    # Verificar e instalar dependencias
    try:
        install_requirements()
    except Exception as e:
        print(f"⚠️ Error instalando dependencias: {e}")
        print("Por favor, instala manualmente: pip install reportlab matplotlib seaborn")
        return
    
    # Configuración
    input_file = './stats/counting_stats.json'
    output_file = f'reporte_videos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    
    # Cargar y analizar datos
    print("📂 Cargando datos...")
    data = load_data(input_file)
    if not data:
        return
    
    print("🔍 Analizando estadísticas...")
    analysis = analyze_data(data)
    if not analysis:
        print("❌ Error en el análisis de datos")
        return
    
    # Generar reporte PDF
    try:
        create_pdf_report(analysis, output_file)
        print(f"\n🎉 ¡Reporte completado exitosamente!")
        print(f"📄 Archivo generado: {output_file}")
        print(f"📊 Videos analizados: {analysis['general']['total_videos']}")
        print(f"👥 Total movimientos: {analysis['conteo_personas']['total_movimientos']}")
        
    except Exception as e:
        print(f"❌ Error generando el reporte: {e}")
        print("Verifica que tengas permisos de escritura en el directorio")

if __name__ == "__main__":
    main()