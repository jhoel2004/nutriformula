# app/exporter.py
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import openpyxl
import datetime
import matplotlib.pyplot as plt
import os
import tempfile
from app.calculator import calcular_ratio_ca_p, verificar_limites_inclusion

class Exporter:
    @staticmethod
    def _evaluar_semaforo(valor, minimo, maximo):
        if valor < minimo:
            return "✗ Deficiente", colors.red
        elif maximo and valor > maximo:
            return "⚠ Exceso", colors.orange
        else:
            return "✓ Cumple", colors.green

    @staticmethod
    def exportar_pdf_completo(filepath, datos):
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        elements.append(Paragraph(f"FORMULACIÓN DE RACIÓN - {os.path.basename(filepath)}", styles['Heading1']))
        elements.append(Paragraph(f"Fecha: {datetime.date.today().strftime('%Y-%m-%d')}", styles['Normal']))
        elements.append(Paragraph(f"Especie: {datos.get('especie', '')}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # Composición Detallada
        elements.append(Paragraph("Composición Detallada", styles['Heading2']))
        headers = ["Insumo", "% Ración", "Tanteo"]
        data_table = [headers]
        
        for item in datos.get('ingredientes', []):
            data_table.append([
                item.get('nombre', ''),
                f"{item.get('tanteo', 0)}%",
                str(item.get('tanteo', 0))
            ])
            
        t = Table(data_table)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))
        
        # Análisis Comparativo (Semáforo)
        elements.append(Paragraph("Análisis Nutricional Comparativo", styles['Heading2']))
        req_headers = ["Nutriente", "Aportado", "Mínimo", "Máximo", "Estado"]
        req_data = [req_headers]
        
        # Dummy evaluation para evitar que crashee si los metadatos completos no están presentes
        # En una versión real, los totales y requerimientos se calcularían o se pasarían en `datos`
        # Asumiendo que `datos` tenga un sub-diccionario `analisis` con los totales y metas.
        analisis = datos.get('analisis', {})
        if analisis:
            for nut_name, (aportado, minimo, maximo) in analisis.items():
                estado_str, color = Exporter._evaluar_semaforo(aportado, minimo, maximo)
                row = [nut_name, f"{aportado:.2f}", f"{minimo:.2f}", f"{maximo:.2f}" if maximo else "N/A", estado_str]
                req_data.append(row)
                
            t_req = Table(req_data)
            t_req.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            # Aplicar colores al estado
            for idx, row in enumerate(req_data[1:], start=1):
                estado_str, color = Exporter._evaluar_semaforo(float(row[1]), float(row[2]), float(row[3]) if row[3] != "N/A" else None)
                t_req.setStyle(TableStyle([('TEXTCOLOR', (4, idx), (4, idx), color)]))
                
            elements.append(t_req)
            elements.append(Spacer(1, 20))
        else:
            elements.append(Paragraph("No hay datos de análisis nutricional disponibles.", styles['Normal']))
            elements.append(Spacer(1, 20))
            
        # Alertas Preventivas de Salud
        if 'totales' in datos and 'insumos_sel' in datos:
            elements.append(Paragraph("Validación de Salud Preventiva", styles['Heading2']))
            
            # Ratio Ca:P
            ratio, estado, msg_cap = calcular_ratio_ca_p(datos['totales'])
            color_cap = colors.green if estado == 'verde' else (colors.orange if estado == 'amarillo' else colors.red)
            elements.append(Paragraph(f"<b>Relación Calcio:Fósforo:</b> <font color='{color_cap}'>{msg_cap}</font>", styles['Normal']))
            
            # Límites de inclusión
            alertas_tox = verificar_limites_inclusion(datos['insumos_sel'], datos['tanteos'], datos['modo'])
            if alertas_tox:
                elements.append(Spacer(1, 6))
                elements.append(Paragraph("<b>⚠️ LÍMITES DE INCLUSIÓN SUPERADOS:</b>", styles['Normal']))
                for a in alertas_tox:
                    adv_str = f"• {a['nombre']}: {a['porcentaje_usado']:.1f}% (Máximo recomendado: {a['max_permitido']}%) - <i>Motivo: {a['razon']}</i>"
                    elements.append(Paragraph(f"<font color='red'>{adv_str}</font>", styles['Normal']))
            else:
                elements.append(Spacer(1, 6))
                elements.append(Paragraph("<b>Límites de Inclusión:</b> <font color='green'>✅ Todos los insumos están dentro de los límites recomendados.</font>", styles['Normal']))
            
            elements.append(Spacer(1, 20))
        
        # Instrucciones
        instrucciones = datos.get('instrucciones', '')
        if instrucciones:
            elements.append(Paragraph("Instrucciones de Preparación", styles['Heading2']))
            elements.append(Paragraph(instrucciones.replace('\n', '<br />'), styles['Normal']))

        doc.build(elements)

    @staticmethod
    def export_pdf(filepath, formulacion_nombre, especie, total_kg, resultados, totales, costo_total, instrucciones=""):
        doc = SimpleDocTemplate(filepath, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Título
        elements.append(Paragraph(f"FORMULACIÓN DE RACIÓN - {formulacion_nombre}", styles['Heading1']))
        elements.append(Paragraph(f"Fecha: {datetime.date.today().strftime('%Y-%m-%d')}", styles['Normal']))
        elements.append(Paragraph(f"Especie: {especie}", styles['Normal']))
        elements.append(Paragraph(f"Total: {total_kg:.2f} kg", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # Tabla de Composición
        elements.append(Paragraph("Composición Detallada", styles['Heading2']))
        
        headers = ["Insumo", "% Ración", "Proteína", "EM Kcal", "Costo"]
        data = [headers]
        
        for item in resultados:
            data.append([
                item['nombre'],
                f"{item['porcentaje']:.2f}%",
                f"{item['proteina']:.2f}",
                f"{item['em_kcal']:.2f}",
                f"${item['costo']:.2f}"
            ])
            
        # Totales
        data.append([
            "TOTALES",
            "100.00%",
            f"{totales['proteina']:.2f}",
            f"{totales['em_kcal']:.2f}",
            f"${costo_total:.2f}"
        ])
            
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(t)
        elements.append(Spacer(1, 20))
        
        # Gráfica de Torta
        try:
            labels = [item['nombre'] for item in resultados if item['porcentaje'] > 0]
            sizes = [item['porcentaje'] for item in resultados if item['porcentaje'] > 0]
            
            if labels and sizes:
                fig, ax = plt.subplots(figsize=(6, 4))
                ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 8})
                ax.axis('equal')
                plt.title("Proporción de Insumos")
                
                temp_dir = tempfile.gettempdir()
                chart_path = os.path.join(temp_dir, f"chart_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png")
                plt.savefig(chart_path, bbox_inches='tight', dpi=150)
                plt.close(fig)
                
                img = Image(chart_path, width=400, height=250)
                elements.append(img)
                elements.append(Spacer(1, 20))
        except Exception as e:
            print(f"Error generando gráfica para PDF: {e}")
            
        # Instrucciones de Preparación
        if instrucciones and instrucciones.strip():
            elements.append(Paragraph("Instrucciones de Preparación", styles['Heading2']))
            elements.append(Paragraph(instrucciones.replace('\n', '<br />'), styles['Normal']))

        doc.build(elements)
        
    @staticmethod
    def export_excel(filepath, insumos_base, resultados, totales):
        wb = openpyxl.Workbook()
        
        # Hoja 1: Insumos base
        ws1 = wb.active
        ws1.title = "Insumos Base"
        
        headers_insumos = ["Nombre", "Proteína%", "EM Kcal", "Fibra%", "Grasa%", "Calcio%", 
                           "Fósforo%", "Lisina%", "Metionina%", "Colina mg/kg", "Precio/kg"]
                           
        ws1.append(headers_insumos)
        for ins in insumos_base:
            ws1.append([ins.get('nombre'), ins.get('proteina'), ins.get('em_kcal'), ins.get('fibra'),
                        ins.get('grasa'), ins.get('calcio'), ins.get('fosforo'), ins.get('lisina'),
                        ins.get('metionina'), ins.get('colina_mgr'), ins.get('precio_kg')])
                        
        # Hoja 2: Resultados
        ws2 = wb.create_sheet("Formulación")
        ws2.append(["Insumo", "% Ración", "Proteína", "EM Kcal", "Fibra", "Grasa", "Costo"])
        
        for item in resultados:
            ws2.append([
                item['nombre'], item['porcentaje'], item['proteina'], 
                item['em_kcal'], item['fibra'], item['grasa'], item['costo']
            ])
            
        ws2.append([
            "TOTALES", 100.0, totales.get('proteina', 0), totales.get('em_kcal', 0), 
            totales.get('fibra', 0), totales.get('grasa', 0), totales.get('costo_kg', 0)
        ])
        
        wb.save(filepath)
