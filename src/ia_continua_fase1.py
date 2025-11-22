#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SICAR IA CONTINUA - FASE 1: MONITOREO PASIVO
============================================
Sistema de monitoreo 24/7 que detecta oportunidades sin ejecutar trades
Recopila datos para validar efectividad antes de trading real
"""

import asyncio
import json
import logging
import pandas as pd
from datetime import datetime, timezone
import websockets
import sqlite3
from pathlib import Path
import sys
import os
import colorama
from colorama import Fore, Back, Style
import winsound
import time

# Inicializar colorama para Windows
colorama.init()

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from market_anomaly_detector import MarketAnomalyDetector
from advanced_pattern_recognition import AdvancedPatternRecognition
from module_xai import XAIModule
from binance_data_provider import BinanceDataProvider

class IAContinuaFase1:
    """Sistema de IA Continua - Fase 1: Monitoreo Pasivo"""
    
    def __init__(self):
        self.setup_logging()
        self.setup_database()
        self.setup_modules()
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
        self.running = False
        
    def setup_logging(self):
        """Configurar logging para el sistema"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ia_continua_fase1.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_database(self):
        """Configurar base de datos para almacenar detecciones"""
        self.db_path = 'ia_continua_detecciones.db'
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabla para anomalías detectadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anomalias_detectadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT NOT NULL,
                tipo_anomalia TEXT NOT NULL,
                score_anomalia REAL,
                precio_actual REAL,
                volumen_ratio REAL,
                volatilidad REAL,
                detalles TEXT,
                precio_5min_despues REAL,
                precio_15min_despues REAL,
                precio_30min_despues REAL,
                validado BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Tabla para patrones detectados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patrones_detectados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT NOT NULL,
                tipo_patron TEXT NOT NULL,
                confianza REAL,
                precio_actual REAL,
                direccion_predicha TEXT,
                detalles TEXT,
                precio_5min_despues REAL,
                precio_15min_despues REAL,
                precio_30min_despues REAL,
                validado BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Tabla para análisis XAI
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analisis_xai (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol TEXT NOT NULL,
                reporte_cognitivo TEXT,
                score_oportunidad REAL,
                factores_clave TEXT,
                recomendacion TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def setup_modules(self):
        """Inicializar módulos de IA"""
        try:
            self.anomaly_detector = MarketAnomalyDetector()
            self.pattern_recognition = AdvancedPatternRecognition()
            self.xai_module = XAIModule()
            self.data_provider = BinanceDataProvider()
            self.logger.info("✅ Módulos de IA inicializados correctamente")
        except Exception as e:
            self.logger.error(f"❌ Error inicializando módulos: {e}")
            
    async def monitor_symbol(self, symbol):
        """Monitorear un símbolo específico"""
        while self.running:
            try:
                # Obtener datos actuales
                data = await self.get_symbol_data(symbol)
                if data is None:
                    await asyncio.sleep(60)  # Esperar 1 minuto si hay error
                    continue
                
                # Detectar anomalías
                await self.detect_anomalies(symbol, data)
                
                # Detectar patrones
                await self.detect_patterns(symbol, data)
                
                # Análisis XAI cada 5 minutos
                if datetime.now().minute % 5 == 0:
                    await self.analyze_with_xai(symbol, data)
                
                await asyncio.sleep(60)  # Análisis cada minuto
                
            except Exception as e:
                self.logger.error(f"❌ Error monitoreando {symbol}: {e}")
                await asyncio.sleep(60)
                
    async def get_symbol_data(self, symbol):
        """Obtener datos del símbolo"""
        try:
            # Obtener datos de 1 hora para análisis
            klines = self.data_provider.get_historical_data(symbol, '1m', 60)
            if not klines:
                return None
                
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convertir a tipos numéricos
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
                
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo datos para {symbol}: {e}")
            return None
            
    async def detect_anomalies(self, symbol, data):
        """Detectar anomalías de mercado"""
        try:
            # Preparar features para detección de anomalías
            features = self.prepare_anomaly_features(data)
            
            # Detectar anomalías
            is_anomaly, score = self.anomaly_detector.detect_anomaly(features)
            
            if is_anomaly:
                current_price = float(data['close'].iloc[-1])
                volume_ratio = float(data['volume'].iloc[-1]) / float(data['volume'].mean())
                volatility = float(data['close'].pct_change().std())
                
                # Guardar en base de datos
                self.save_anomaly_detection(
                    symbol=symbol,
                    tipo_anomalia="volume_price_anomaly",
                    score=score,
                    precio_actual=current_price,
                    volumen_ratio=volume_ratio,
                    volatilidad=volatility,
                    detalles=f"Anomalía detectada con score {score:.3f}"
                )
                
                self.logger.info(f"🚨 ANOMALÍA DETECTADA - {symbol}: Score {score:.3f}, Precio ${current_price:.4f}")
                
        except Exception as e:
            self.logger.error(f"❌ Error detectando anomalías para {symbol}: {e}")
            
    async def detect_patterns(self, symbol, data):
        """Detectar patrones de trading"""
        try:
            # Detectar patrones usando el sistema avanzado
            patterns = self.pattern_recognition.detect_patterns(data)
            
            for pattern in patterns:
                if pattern['confidence'] > 0.7:  # Solo patrones de alta confianza
                    current_price = float(data['close'].iloc[-1])
                    
                    # Guardar en base de datos
                    self.save_pattern_detection(
                        symbol=symbol,
                        tipo_patron=pattern['type'],
                        confianza=pattern['confidence'],
                        precio_actual=current_price,
                        direccion_predicha=pattern.get('direction', 'unknown'),
                        detalles=json.dumps(pattern)
                    )
                    
                    self.logger.info(f"📈 PATRÓN DETECTADO - {symbol}: {pattern['type']} (Confianza: {pattern['confidence']:.1%})")
                    
        except Exception as e:
            self.logger.error(f"❌ Error detectando patrones para {symbol}: {e}")
            
    async def analyze_with_xai(self, symbol, data):
        """Análisis con XAI cada 5 minutos"""
        try:
            # Generar reporte cognitivo
            market_data = {
                'symbol': symbol,
                'price': float(data['close'].iloc[-1]),
                'volume': float(data['volume'].iloc[-1]),
                'price_change': float(data['close'].pct_change().iloc[-1]),
                'volatility': float(data['close'].pct_change().std())
            }
            
            reporte = self.xai_module.generate_cognitive_report(market_data)
            
            # Calcular score de oportunidad (simplificado)
            score_oportunidad = self.calculate_opportunity_score(data)
            
            # Guardar análisis XAI
            self.save_xai_analysis(
                symbol=symbol,
                reporte_cognitivo=reporte,
                score_oportunidad=score_oportunidad,
                factores_clave="volatility,volume,momentum",
                recomendacion="monitor" if score_oportunidad < 0.7 else "potential_opportunity"
            )
            
            if score_oportunidad > 0.8:
                self.logger.info(f"🧠 XAI OPORTUNIDAD - {symbol}: Score {score_oportunidad:.1%}")
                
        except Exception as e:
            self.logger.error(f"❌ Error en análisis XAI para {symbol}: {e}")
            
    def prepare_anomaly_features(self, data):
        """Preparar features para detección de anomalías"""
        try:
            # Calcular indicadores técnicos básicos
            data['returns'] = data['close'].pct_change()
            data['volume_ratio'] = data['volume'] / data['volume'].rolling(20).mean()
            data['volatility'] = data['returns'].rolling(10).std()
            data['price_range'] = (data['high'] - data['low']) / data['close']
            
            # Tomar la última observación
            latest = data.iloc[-1]
            
            features = [
                latest['returns'] if not pd.isna(latest['returns']) else 0,
                latest['volume_ratio'] if not pd.isna(latest['volume_ratio']) else 1,
                latest['volatility'] if not pd.isna(latest['volatility']) else 0,
                latest['price_range'] if not pd.isna(latest['price_range']) else 0
            ]
            
            return features
            
        except Exception as e:
            self.logger.error(f"❌ Error preparando features: {e}")
            return [0, 1, 0, 0]  # Features por defecto
            
    def calculate_opportunity_score(self, data):
        """Calcular score de oportunidad simplificado"""
        try:
            # Factores que indican oportunidad
            volume_spike = float(data['volume'].iloc[-1]) / float(data['volume'].mean())
            price_momentum = abs(float(data['close'].pct_change().iloc[-1]))
            volatility = float(data['close'].pct_change().std())
            
            # Score combinado (0-1)
            score = min(1.0, (
                (volume_spike - 1) * 0.3 +  # Peso del volumen
                price_momentum * 10 * 0.4 +  # Peso del momentum
                volatility * 5 * 0.3  # Peso de la volatilidad
            ))
            
            return max(0, score)
            
        except Exception as e:
            self.logger.error(f"❌ Error calculando opportunity score: {e}")
            return 0.0
            
    def save_anomaly_detection(self, symbol, tipo_anomalia, score, precio_actual, volumen_ratio, volatilidad, detalles):
        """Guardar detección de anomalía en BD"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO anomalias_detectadas 
                (symbol, tipo_anomalia, score_anomalia, precio_actual, volumen_ratio, volatilidad, detalles)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, tipo_anomalia, score, precio_actual, volumen_ratio, volatilidad, detalles))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando anomalía: {e}")
            
    def save_pattern_detection(self, symbol, tipo_patron, confianza, precio_actual, direccion_predicha, detalles):
        """Guardar detección de patrón en BD"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO patrones_detectados 
                (symbol, tipo_patron, confianza, precio_actual, direccion_predicha, detalles)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, tipo_patron, confianza, precio_actual, direccion_predicha, detalles))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando patrón: {e}")
            
    def save_xai_analysis(self, symbol, reporte_cognitivo, score_oportunidad, factores_clave, recomendacion):
        """Guardar análisis XAI en BD"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analisis_xai 
                (symbol, reporte_cognitivo, score_oportunidad, factores_clave, recomendacion)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, reporte_cognitivo, score_oportunidad, factores_clave, recomendacion))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"❌ Error guardando análisis XAI: {e}")
            
    async def generate_daily_report(self):
        """Generar reporte diario de detecciones"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Estadísticas del día
            today = datetime.now().strftime('%Y-%m-%d')
            
            anomalias_df = pd.read_sql_query(f'''
                SELECT * FROM anomalias_detectadas 
                WHERE DATE(timestamp) = '{today}'
            ''', conn)
            
            patrones_df = pd.read_sql_query(f'''
                SELECT * FROM patrones_detectados 
                WHERE DATE(timestamp) = '{today}'
            ''', conn)
            
            conn.close()
            
            # Generar reporte
            reporte = f"""
🧠 REPORTE DIARIO IA CONTINUA - {today}
{'='*50}

📊 ESTADÍSTICAS:
- Anomalías detectadas: {len(anomalias_df)}
- Patrones detectados: {len(patrones_df)}
- Símbolos monitoreados: {len(self.symbols)}

🚨 TOP ANOMALÍAS:
"""
            
            if len(anomalias_df) > 0:
                top_anomalias = anomalias_df.nlargest(5, 'score_anomalia')
                for _, anomalia in top_anomalias.iterrows():
                    reporte += f"- {anomalia['symbol']}: Score {anomalia['score_anomalia']:.3f} a ${anomalia['precio_actual']:.4f}\n"
            else:
                reporte += "- No se detectaron anomalías significativas\n"
                
            reporte += f"\n📈 TOP PATRONES:\n"
            
            if len(patrones_df) > 0:
                top_patrones = patrones_df.nlargest(5, 'confianza')
                for _, patron in top_patrones.iterrows():
                    reporte += f"- {patron['symbol']}: {patron['tipo_patron']} (Confianza: {patron['confianza']:.1%})\n"
            else:
                reporte += "- No se detectaron patrones de alta confianza\n"
                
            self.logger.info(reporte)
            
            # Guardar reporte en archivo
            with open(f'reporte_ia_continua_{today}.txt', 'w', encoding='utf-8') as f:
                f.write(reporte)
                
        except Exception as e:
            self.logger.error(f"❌ Error generando reporte diario: {e}")
            
    async def start_monitoring(self):
        """Iniciar monitoreo continuo"""
        self.logger.info("🚀 INICIANDO IA CONTINUA - FASE 1: MONITOREO PASIVO")
        self.logger.info(f"📊 Monitoreando símbolos: {', '.join(self.symbols)}")
        
        self.running = True
        
        # Crear tareas para cada símbolo
        tasks = []
        for symbol in self.symbols:
            task = asyncio.create_task(self.monitor_symbol(symbol))
            tasks.append(task)
            
        # Tarea para reporte diario
        daily_report_task = asyncio.create_task(self.daily_report_scheduler())
        tasks.append(daily_report_task)
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("🛑 Deteniendo monitoreo...")
            self.running = False
            
    async def daily_report_scheduler(self):
        """Programador de reportes diarios"""
        while self.running:
            now = datetime.now()
            # Generar reporte a las 23:59
            if now.hour == 23 and now.minute == 59:
                await self.generate_daily_report()
                await asyncio.sleep(120)  # Esperar 2 minutos para evitar duplicados
            else:
                await asyncio.sleep(60)  # Verificar cada minuto

if __name__ == "__main__":
    sistema = IAContinuaFase1()
    asyncio.run(sistema.start_monitoring())