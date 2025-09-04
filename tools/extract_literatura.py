#!/usr/bin/env python3
"""
Extractor de texto de PDFs de literatura de trading
"""
import os
import sys
import PyPDF2
from pathlib import Path

def extract_pdf_text(pdf_path, max_pages=20):
    """Extrae texto de un PDF, limitando a max_pages páginas"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            total_pages = len(pdf_reader.pages)
            pages_to_read = min(max_pages, total_pages)
            
            text = ""
            for page_num in range(pages_to_read):
                try:
                    page = pdf_reader.pages[page_num]
                    text += f"\n--- PÁGINA {page_num + 1} ---\n"
                    text += page.extract_text()
                    text += "\n"
                except Exception as e:
                    text += f"\n--- ERROR EN PÁGINA {page_num + 1}: {str(e)} ---\n"
            
            return text, total_pages
    except Exception as e:
        return f"Error leyendo PDF: {str(e)}", 0

def main():
    literatura_path = Path("/home/johan/itbot_linux/literatura")
    
    # PDFs más relevantes para estrategias de trading
    priority_pdfs = [
        "5 Pasos para Realizar Scalping Criptomonedas, Semillero de Ingresos.pdf",
        "06. Análisis técnico sistemas automáticos de trading autor Kevin Guadilla Estévez.pdf", 
        "08. El trading algorítmico en los mercados financieros. Estrategia Basada en la Volatilidad de los Precios de las Opciones autor Isabel Martín Hinojosa.pdf",
        "DAY TRADING EN UNA SEMANA - BORJA MUÑOZ.pdf",
        "Curso de Trading Institucional.pdf",
        "Python para finanzas y trading.pdf",
        "TRADING AVANZADO - LA ESPIRAL LOGARITMICA.pdf",
        "Crypto Trading Pro (Alan No.pdf",
        "The Day Trading Bible Form Rookie to Veteran within 4 Weeks Best Intraday Strategies and Setups to profit from Outsta.epub"
    ]
    
    results = {}
    
    for pdf_name in priority_pdfs:
        pdf_path = literatura_path / pdf_name
        
        if pdf_path.exists() and pdf_path.suffix.lower() == '.pdf':
            print(f"\n🔍 Procesando: {pdf_name}")
            text, total_pages = extract_pdf_text(pdf_path, max_pages=10)
            results[pdf_name] = {
                'text': text,
                'total_pages': total_pages,
                'extracted_pages': min(10, total_pages)
            }
            print(f"   ✅ Extraído: {results[pdf_name]['extracted_pages']}/{total_pages} páginas")
        else:
            print(f"   ❌ No encontrado: {pdf_name}")
    
    # Guardar resultados
    output_file = "/home/johan/itbot_linux/data/literatura_extracts.txt"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== EXTRACTOS DE LITERATURA DE TRADING ===\n")
        f.write(f"Fecha: {os.popen('date').read().strip()}\n\n")
        
        for pdf_name, result in results.items():
            f.write(f"\n{'='*60}\n")
            f.write(f"DOCUMENTO: {pdf_name}\n")
            f.write(f"PÁGINAS TOTALES: {result['total_pages']}\n")
            f.write(f"PÁGINAS EXTRAÍDAS: {result['extracted_pages']}\n")
            f.write(f"{'='*60}\n")
            f.write(result['text'])
            f.write(f"\n{'='*60}\n\n")
    
    print(f"\n💾 Resultados guardados en: {output_file}")
    print(f"📚 PDFs procesados: {len(results)}")
    
    # Mostrar un resumen de los primeros párrafos más relevantes
    print(f"\n📋 RESUMEN DE CONTENIDOS ENCONTRADOS:")
    for pdf_name, result in results.items():
        text_preview = result['text'][:500].replace('\n', ' ')
        if len(text_preview) > 0:
            print(f"\n📖 {pdf_name[:50]}...")
            print(f"   🔤 Preview: {text_preview[:200]}...")

if __name__ == "__main__":
    main()
