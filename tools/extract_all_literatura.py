#!/usr/bin/env python3
"""
Extractor COMPLETO de Literatura de Trading
Procesar TODOS los PDFs de la carpeta literatura
"""

import os
import sys
from pathlib import Path
try:
    import PyPDF2
except ImportError:
    print("PyPDF2 no encontrado. Instalando...")
    os.system("pip install PyPDF2")
    import PyPDF2

def extract_pdf_text(pdf_path, max_pages=5):
    """Extraer texto de un PDF (máximo max_pages páginas)"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            
            text = f"DOCUMENTO: {pdf_path.name}\n"
            text += f"PÁGINAS TOTALES: {total_pages}\n"
            text += f"PÁGINAS EXTRAÍDAS: {min(max_pages, total_pages)}\n"
            text += "="*60 + "\n\n"
            
            pages_to_extract = min(max_pages, total_pages)
            
            for page_num in range(pages_to_extract):
                try:
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    text += f"--- PÁGINA {page_num + 1} ---\n"
                    text += page_text
                    text += "\n\n"
                except Exception as e:
                    text += f"\n--- ERROR EN PÁGINA {page_num + 1}: {str(e)} ---\n\n"
            
            return text, total_pages
    except Exception as e:
        return f"Error leyendo PDF {pdf_path.name}: {str(e)}\n\n", 0

def process_all_literatura():
    """Procesar TODOS los PDFs de la carpeta literatura"""
    literatura_path = Path("/home/johan/itbot_linux/literatura")
    
    if not literatura_path.exists():
        print(f"❌ Carpeta no encontrada: {literatura_path}")
        return
    
    # Obtener TODOS los PDFs
    all_pdfs = [f for f in literatura_path.iterdir() 
                if f.is_file() and f.suffix.lower() == '.pdf']
    
    print(f"📚 PROCESANDO TODA LA LITERATURA DE TRADING")
    print(f"📂 Carpeta: {literatura_path}")
    print(f"📄 Total PDFs encontrados: {len(all_pdfs)}")
    print("="*70)
    
    results = {}
    processed_count = 0
    total_pages_extracted = 0
    
    for pdf_file in sorted(all_pdfs):
        try:
            print(f"\n🔍 Procesando: {pdf_file.name}")
            text, total_pages = extract_pdf_text(pdf_file, max_pages=5)
            
            if total_pages > 0:
                results[pdf_file.name] = {
                    'text': text,
                    'total_pages': total_pages,
                    'extracted_pages': min(5, total_pages)
                }
                processed_count += 1
                total_pages_extracted += min(5, total_pages)
                print(f"   ✅ Extraído: {min(5, total_pages)}/{total_pages} páginas")
            else:
                print(f"   ❌ Error procesando: {pdf_file.name}")
                
        except Exception as e:
            print(f"   ❌ Error con {pdf_file.name}: {str(e)}")
            continue
    
    # Guardar TODOS los resultados
    output_file = "/home/johan/itbot_linux/data/literatura_completa_extracts.txt"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== EXTRACTOS COMPLETOS DE LITERATURA DE TRADING ===\n")
        f.write(f"Fecha: {os.popen('date').read().strip()}\n")
        f.write(f"Total PDFs procesados: {processed_count}\n")
        f.write(f"Total páginas extraídas: {total_pages_extracted}\n\n")
        
        for pdf_name, result in results.items():
            f.write(f"\n{'='*120}\n")
            f.write(result['text'])
            f.write(f"\n{'='*120}\n")
    
    print(f"\n🎉 PROCESAMIENTO COMPLETO:")
    print(f"📊 PDFs procesados: {processed_count}/{len(all_pdfs)}")
    print(f"📄 Total páginas extraídas: {total_pages_extracted}")
    print(f"💾 Resultados guardados en: {output_file}")
    
    # Resumen por categorías
    print(f"\n📚 CATEGORÍAS IDENTIFICADAS:")
    
    categories = {
        'Scalping/Day Trading': [],
        'Análisis Técnico': [],
        'Trading Algorítmico': [],
        'Criptomonedas': [],
        'Psicología/Mental': [],
        'Manuales/Cursos': [],
        'Python/Programación': [],
        'Otros': []
    }
    
    for pdf_name in results.keys():
        name_lower = pdf_name.lower()
        if 'scalping' in name_lower or 'day trading' in name_lower:
            categories['Scalping/Day Trading'].append(pdf_name)
        elif 'analisis' in name_lower or 'técnico' in name_lower:
            categories['Análisis Técnico'].append(pdf_name)
        elif 'algorit' in name_lower or 'python' in name_lower:
            categories['Trading Algorítmico'].append(pdf_name)
        elif 'crypto' in name_lower or 'bitcoin' in name_lower or 'criptomon' in name_lower:
            categories['Criptomonedas'].append(pdf_name)
        elif 'psicol' in name_lower or 'mental' in name_lower or 'emocional' in name_lower:
            categories['Psicología/Mental'].append(pdf_name)
        elif 'manual' in name_lower or 'curso' in name_lower or 'guia' in name_lower:
            categories['Manuales/Cursos'].append(pdf_name)
        elif 'python' in name_lower:
            categories['Python/Programación'].append(pdf_name)
        else:
            categories['Otros'].append(pdf_name)
    
    for category, books in categories.items():
        if books:
            print(f"\n📖 {category} ({len(books)} libros):")
            for book in books[:3]:  # Mostrar solo primeros 3
                print(f"   • {book[:60]}...")
            if len(books) > 3:
                print(f"   • ... y {len(books)-3} más")
    
    return results

if __name__ == "__main__":
    process_all_literatura()
