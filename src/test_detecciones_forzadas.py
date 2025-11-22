#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST DE DETECCIONES FORZADAS
============================
Script para forzar detecciones y verificar la creación de la base de datos
"""

import sqlite3
import os
import sys
from datetime import datetime
import json
import colorama
from colorama import Fore, Style

# Inicializar colorama
colorama.init()

def crear_base_datos_test():
    """Crear base de datos de prueba con detecciones simuladas"""
    db_path = "ia_continua_detecciones.db"
    
    print(f"{Fore.CYAN}🔧 CREANDO BASE DE DATOS DE PRUEBA")
    print(f"{Fore.CYAN}{'='*50}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Crear tabla de anomalías
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalias_detectadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                anomaly_score REAL NOT NULL,
                price REAL NOT NULL,
                volume REAL NOT NULL,
                details TEXT,
                alert_sent INTEGER DEFAULT 0
            )
        ''')
        
        # Crear tabla de patrones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patrones_detectados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                price REAL NOT NULL,
                details TEXT,
                alert_sent INTEGER DEFAULT 0
            )
        ''')
        
        # Crear tabla de análisis XAI
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analisis_xai (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                opportunity_score REAL NOT NULL,
                price REAL NOT NULL,
                analysis TEXT,
                alert_sent INTEGER DEFAULT 0
            )
        ''')
        
        # Insertar datos de prueba
        timestamp = datetime.now().isoformat()
        
        # Anomalías de prueba
        anomalias_test = [
            (timestamp, 'BTCUSDT', 0.85, 67500.0, 1250000.0, '{"tipo": "volumen_anormal", "descripcion": "Volumen 300% superior al promedio"}', 1),
            (timestamp, 'ETHUSDT', 0.78, 2650.0, 850000.0, '{"tipo": "precio_divergencia", "descripcion": "Divergencia RSI detectada"}', 1),
            (timestamp, 'BNBUSDT', 0.72, 315.0, 450000.0, '{"tipo": "momentum_cambio", "descripcion": "Cambio súbito de momentum"}', 0)
        ]
        
        cursor.executemany('''
            INSERT INTO anomalias_detectadas 
            (timestamp, symbol, anomaly_score, price, volume, details, alert_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', anomalias_test)
        
        # Patrones de prueba
        patrones_test = [
            (timestamp, 'BTCUSDT', 'breakout_alcista', 0.89, 67500.0, '{"resistencia": 67000, "volumen_confirmacion": true}', 1),
            (timestamp, 'ETHUSDT', 'triangulo_simetrico', 0.76, 2650.0, '{"apex_precio": 2640, "direccion_probable": "alcista"}', 1),
            (timestamp, 'ADAUSDT', 'doble_suelo', 0.82, 0.45, '{"soporte": 0.44, "objetivo": 0.52}', 0)
        ]
        
        cursor.executemany('''
            INSERT INTO patrones_detectados 
            (timestamp, symbol, pattern_type, confidence, price, details, alert_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', patrones_test)
        
        # Análisis XAI de prueba
        xai_test = [
            (timestamp, 'BTCUSDT', 0.91, 67500.0, '{"factores": ["momentum_positivo", "volumen_alto", "rsi_neutral"], "probabilidad_alza": 0.78}', 1),
            (timestamp, 'ETHUSDT', 0.73, 2650.0, '{"factores": ["divergencia_macd", "soporte_fuerte"], "probabilidad_alza": 0.65}', 1),
            (timestamp, 'LINKUSDT', 0.68, 14.5, '{"factores": ["correlacion_btc", "volumen_medio"], "probabilidad_alza": 0.58}', 0)
        ]
        
        cursor.executemany('''
            INSERT INTO analisis_xai 
            (timestamp, symbol, opportunity_score, price, analysis, alert_sent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', xai_test)
        
        conn.commit()
        conn.close()
        
        print(f"{Fore.GREEN}✅ Base de datos creada exitosamente")
        print(f"{Fore.WHITE}📁 Archivo: {db_path}")
        print(f"{Fore.WHITE}📊 Anomalías insertadas: {len(anomalias_test)}")
        print(f"{Fore.WHITE}📈 Patrones insertados: {len(patrones_test)}")
        print(f"{Fore.WHITE}🧠 Análisis XAI insertados: {len(xai_test)}")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error creando base de datos: {e}")
        return False

def verificar_base_datos_creada():
    """Verificar que la base de datos se creó correctamente"""
    db_path = "ia_continua_detecciones.db"
    
    print(f"\n{Fore.CYAN}🔍 VERIFICANDO BASE DE DATOS CREADA")
    print(f"{Fore.CYAN}{'='*50}")
    
    if not os.path.exists(db_path):
        print(f"{Fore.RED}❌ Base de datos NO existe")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tablas = [t[0] for t in cursor.fetchall()]
        
        tablas_esperadas = ['anomalias_detectadas', 'patrones_detectados', 'analisis_xai']
        
        print(f"{Fore.WHITE}📋 Tablas encontradas: {len(tablas)}")
        
        for tabla in tablas_esperadas:
            if tabla in tablas:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"{Fore.GREEN}✅ {tabla}: {count} registros")
                
                # Mostrar último registro
                cursor.execute(f"SELECT * FROM {tabla} ORDER BY id DESC LIMIT 1")
                ultimo = cursor.fetchone()
                if ultimo:
                    score_val = ultimo[3] if isinstance(ultimo[3], (int, float)) else 0.0
                    print(f"{Fore.WHITE}   📅 Último: ID {ultimo[0]}, {ultimo[2]} - Score: {score_val:.2f}")
            else:
                print(f"{Fore.RED}❌ {tabla}: NO ENCONTRADA")
        
        conn.close()
        
        # Verificar tamaño del archivo
        file_size = os.path.getsize(db_path) / 1024  # KB
        print(f"{Fore.WHITE}📊 Tamaño archivo: {file_size:.2f} KB")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error verificando: {e}")
        return False

def simular_deteccion_tiempo_real():
    """Simular una detección en tiempo real"""
    print(f"\n{Fore.MAGENTA}🚨 SIMULANDO DETECCIÓN EN TIEMPO REAL")
    print(f"{Fore.MAGENTA}{'='*50}")
    
    try:
        # Importar módulos necesarios
        sys.path.append('.')
        from market_anomaly_detector import MarketAnomalyDetector
        
        # Crear detector
        detector = MarketAnomalyDetector()
        
        # Datos simulados de mercado
        market_data = {
            'symbol': 'BTCUSDT',
            'price': 67800.0,
            'volume': 1500000.0,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"{Fore.WHITE}📊 Datos simulados:")
        print(f"{Fore.WHITE}   Symbol: {market_data['symbol']}")
        print(f"{Fore.WHITE}   Price: ${market_data['price']:,.2f}")
        print(f"{Fore.WHITE}   Volume: {market_data['volume']:,.0f}")
        
        # Simular detección
        print(f"{Fore.YELLOW}🔍 Ejecutando detección...")
        
        # Aquí normalmente se ejecutaría la detección real
        # Por ahora simulamos el resultado
        anomaly_detected = True
        anomaly_score = 0.87
        
        if anomaly_detected:
            print(f"{Fore.GREEN}✅ ANOMALÍA DETECTADA!")
            print(f"{Fore.WHITE}   Score: {anomaly_score:.2f}")
            print(f"{Fore.WHITE}   Tipo: Volumen anormal + Momentum positivo")
            
            # Guardar en base de datos
            db_path = "ia_continua_detecciones.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO anomalias_detectadas 
                (timestamp, symbol, anomaly_score, price, volume, details, alert_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                market_data['timestamp'],
                market_data['symbol'],
                anomaly_score,
                market_data['price'],
                market_data['volume'],
                '{"tipo": "simulacion_test", "descripcion": "Detección simulada para prueba"}',
                1
            ))
            
            conn.commit()
            conn.close()
            
            print(f"{Fore.GREEN}💾 Detección guardada en base de datos")
        else:
            print(f"{Fore.YELLOW}⚪ No se detectaron anomalías")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error en simulación: {e}")
        return False

def main():
    """Función principal"""
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}🧪 TEST DE DETECCIONES FORZADAS - SICAR")
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.WHITE}🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Paso 1: Crear base de datos con datos de prueba
    print(f"\n{Fore.YELLOW}📋 PASO 1: Crear base de datos de prueba")
    if crear_base_datos_test():
        print(f"{Fore.GREEN}✅ Paso 1 completado")
    else:
        print(f"{Fore.RED}❌ Paso 1 falló")
        return
    
    # Paso 2: Verificar base de datos
    print(f"\n{Fore.YELLOW}📋 PASO 2: Verificar base de datos")
    if verificar_base_datos_creada():
        print(f"{Fore.GREEN}✅ Paso 2 completado")
    else:
        print(f"{Fore.RED}❌ Paso 2 falló")
        return
    
    # Paso 3: Simular detección en tiempo real
    print(f"\n{Fore.YELLOW}📋 PASO 3: Simular detección tiempo real")
    if simular_deteccion_tiempo_real():
        print(f"{Fore.GREEN}✅ Paso 3 completado")
    else:
        print(f"{Fore.YELLOW}⚠️ Paso 3 con advertencias")
    
    # Verificación final
    print(f"\n{Fore.YELLOW}📋 VERIFICACIÓN FINAL")
    verificar_base_datos_creada()
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.GREEN}✅ Test de detecciones completado")
    print(f"{Fore.WHITE}💡 La base de datos 'ia_continua_detecciones.db' ahora existe")
    print(f"{Fore.WHITE}💡 El sistema de Fase 2 debería poder leer/escribir normalmente")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()