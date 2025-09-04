#!/usr/bin/env python3
"""
Extractor COMPLETO de Literatura de Trading
Procesar TODOS los PDFs y EPUBs de la carpeta literatura
"""

import os
import sys
from pathlib import Path
import subprocess

# Instalar librerías necesarias
def install_dependencies():
    """Instalar PyPDF2 y ebooklib para manejar PDFs y EPUBs"""
    try:
        import PyPDF2
        import ebooklib
        from ebooklib import epub
    except ImportError:
        print("📦 Instalando librerías necesarias...")
        subprocess.run([sys.executable, "-m", "pip", "install", "PyPDF2", "EbookLib"], check=True)
        import PyPDF2
        import ebooklib
        from ebooklib import epub
    return PyPDF2, ebooklib, epub

def extract_pdf_text(pdf_path, max_pages=5):
    """Extraer texto de un PDF (máximo max_pages páginas)"""
    PyPDF2, _, _ = install_dependencies()
    
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            
            text = f"DOCUMENTO PDF: {pdf_path.name}\n"
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

def extract_epub_text(epub_path, max_chapters=5):
    """Extraer texto de un EPUB (máximo max_chapters capítulos)"""
    _, ebooklib, epub = install_dependencies()
    
    try:
        book = epub.read_epub(str(epub_path))
        
        text = f"DOCUMENTO EPUB: {epub_path.name}\n"
        
        # Obtener información básica
        title = book.get_metadata('DC', 'title')
        author = book.get_metadata('DC', 'creator')
        
        if title:
            text += f"TÍTULO: {title[0][0] if title else 'N/A'}\n"
        if author:
            text += f"AUTOR: {author[0][0] if author else 'N/A'}\n"
        
        # Obtener capítulos
        chapters = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                chapters.append(item)
        
        total_chapters = len(chapters)
        chapters_to_extract = min(max_chapters, total_chapters)
        
        text += f"CAPÍTULOS TOTALES: {total_chapters}\n"
        text += f"CAPÍTULOS EXTRAÍDOS: {chapters_to_extract}\n"
        text += "="*60 + "\n\n"
        
        for i, chapter in enumerate(chapters[:chapters_to_extract]):
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(chapter.get_content(), 'html.parser')
                chapter_text = soup.get_text()
                
                text += f"--- CAPÍTULO {i + 1} ---\n"
                text += chapter_text[:2000]  # Primeros 2000 caracteres
                text += "\n...\n\n"
                
            except ImportError:
                # Si no hay BeautifulSoup, intentar extracción básica
                chapter_content = chapter.get_content().decode('utf-8')
                # Remover tags HTML básicos
                import re
                clean_text = re.sub('<[^<]+?>', '', chapter_content)
                text += f"--- CAPÍTULO {i + 1} ---\n"
                text += clean_text[:2000]  # Primeros 2000 caracteres
                text += "\n...\n\n"
            except Exception as e:
                text += f"\n--- ERROR EN CAPÍTULO {i + 1}: {str(e)} ---\n\n"
        
        return text, total_chapters
    except Exception as e:
        return f"Error leyendo EPUB {epub_path.name}: {str(e)}\n\n", 0

def process_all_literatura():
    """Procesar TODOS los PDFs y EPUBs de la carpeta literatura"""
    literatura_path = Path("/home/johan/itbot_linux/literatura")
    
    if not literatura_path.exists():
        print(f"❌ Carpeta no encontrada: {literatura_path}")
        return
    
    # Obtener TODOS los PDFs y EPUBs
    all_files = []
    for f in literatura_path.iterdir():
        if f.is_file() and f.suffix.lower() in ['.pdf', '.epub']:
            all_files.append(f)
    
    print(f"📚 PROCESANDO TODA LA LITERATURA DE TRADING")
    print(f"📂 Carpeta: {literatura_path}")
    print(f"📄 Total archivos encontrados: {len(all_files)}")
    
    # Separar por tipo
    pdfs = [f for f in all_files if f.suffix.lower() == '.pdf']
    epubs = [f for f in all_files if f.suffix.lower() == '.epub']
    
    print(f"📄 PDFs: {len(pdfs)}")
    print(f"📖 EPUBs: {len(epubs)}")
    print("="*70)
    
    results = {}
    processed_count = 0
    total_content_extracted = 0
    
    # Procesar PDFs
    for pdf_file in sorted(pdfs):
        try:
            print(f"\n🔍 Procesando PDF: {pdf_file.name}")
            text, total_pages = extract_pdf_text(pdf_file, max_pages=5)
            
            if total_pages > 0:
                results[pdf_file.name] = {
                    'text': text,
                    'type': 'PDF',
                    'total_units': total_pages,
                    'extracted_units': min(5, total_pages)
                }
                processed_count += 1
                total_content_extracted += min(5, total_pages)
                print(f"   ✅ Extraído: {min(5, total_pages)}/{total_pages} páginas")
            else:
                print(f"   ❌ Error procesando: {pdf_file.name}")
                
        except Exception as e:
            print(f"   ❌ Error con {pdf_file.name}: {str(e)}")
            continue
    
    # Procesar EPUBs
    for epub_file in sorted(epubs):
        try:
            print(f"\n📖 Procesando EPUB: {epub_file.name}")
            text, total_chapters = extract_epub_text(epub_file, max_chapters=5)
            
            if total_chapters > 0:
                results[epub_file.name] = {
                    'text': text,
                    'type': 'EPUB',
                    'total_units': total_chapters,
                    'extracted_units': min(5, total_chapters)
                }
                processed_count += 1
                total_content_extracted += min(5, total_chapters)
                print(f"   ✅ Extraído: {min(5, total_chapters)}/{total_chapters} capítulos")
            else:
                print(f"   ❌ Error procesando: {epub_file.name}")
                
        except Exception as e:
            print(f"   ❌ Error con {epub_file.name}: {str(e)}")
            continue
    
    # Guardar TODOS los resultados
    output_file = "/home/johan/itbot_linux/data/literatura_completa_todos_formatos.txt"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== EXTRACTOS COMPLETOS DE LITERATURA DE TRADING ===\n")
        f.write("=== PDFs + EPUBs ===\n")
        f.write(f"Fecha: {os.popen('date').read().strip()}\n")
        f.write(f"Total archivos procesados: {processed_count}\n")
        f.write(f"Total contenido extraído: {total_content_extracted} unidades\n\n")
        
        for file_name, result in results.items():
            f.write(f"\n{'='*120}\n")
            f.write(result['text'])
            f.write(f"\n{'='*120}\n")
    
    print(f"\n🎉 PROCESAMIENTO COMPLETO:")
    print(f"📊 Archivos procesados: {processed_count}/{len(all_files)}")
    print(f"📄 Total contenido extraído: {total_content_extracted} unidades")
    print(f"💾 Resultados guardados en: {output_file}")
    
    # Resumen por categorías mejorado
    print(f"\n📚 CATEGORÍAS IDENTIFICADAS:")
    
    categories = {
        'Scalping/Day Trading': [],
        'Análisis Técnico': [],
        'Trading Algorítmico/Python': [],
        'Criptomonedas/Crypto': [],
        'Psicología/Mental': [],
        'Manuales Generales': [],
        'Forex/Divisas': [],
        'Opciones/Derivados': [],
        'Otros': []
    }
    
    for file_name in results.keys():
        name_lower = file_name.lower()
        if 'scalping' in name_lower or 'day trading' in name_lower:
            categories['Scalping/Day Trading'].append(file_name)
        elif 'analisis' in name_lower or 'técnico' in name_lower or 'velas' in name_lower:
            categories['Análisis Técnico'].append(file_name)
        elif 'algorit' in name_lower or 'python' in name_lower or 'programming' in name_lower:
            categories['Trading Algorítmico/Python'].append(file_name)
        elif 'crypto' in name_lower or 'bitcoin' in name_lower or 'criptomon' in name_lower or 'cryptocurrency' in name_lower:
            categories['Criptomonedas/Crypto'].append(file_name)
        elif 'psicol' in name_lower or 'mental' in name_lower or 'emocional' in name_lower:
            categories['Psicología/Mental'].append(file_name)
        elif 'forex' in name_lower or 'divisas' in name_lower:
            categories['Forex/Divisas'].append(file_name)
        elif 'option' in name_lower or 'opciones' in name_lower:
            categories['Opciones/Derivados'].append(file_name)
        elif 'manual' in name_lower or 'curso' in name_lower or 'guia' in name_lower:
            categories['Manuales Generales'].append(file_name)
        else:
            categories['Otros'].append(file_name)
    
    for category, books in categories.items():
        if books:
            print(f"\n📖 {category} ({len(books)} archivos):")
            for book in books[:3]:  # Mostrar solo primeros 3
                print(f"   • {book[:70]}...")
            if len(books) > 3:
                print(f"   • ... y {len(books)-3} más")
    
    return results

if __name__ == "__main__":
    try:
        # Instalar BeautifulSoup para mejor parsing de EPUB
        subprocess.run([sys.executable, "-m", "pip", "install", "beautifulsoup4"], check=True)
    except:
        print("⚠️  BeautifulSoup no instalado, usando parser básico")
    
    process_all_literatura()
