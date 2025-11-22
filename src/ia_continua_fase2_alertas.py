#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SICAR IA CONTINUA - FASE 2: ALERTAS INTELIGENTES POR CONSOLA
===========================================================
Sistema de alertas en tiempo real con notificaciones visuales y sonoras
Detecta oportunidades de alta calidad y las presenta de forma clara
"""

import asyncio
import json
import logging
import pandas as pd
from datetime import datetime, timezone, timedelta
import sqlite3
from pathlib import Path
import sys
import os
import colorama
from colorama import Fore, Back, Style
import winsound
import time
import threading
from collections import deque

# Inicializar colorama para Windows
colorama.init()

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from market_anomaly_detector import MarketAnomalyDetector
from advanced_pattern_recognition import AdvancedPatternRecognition
from module_xai import generate_cognitive_report
from binance_data_provider import BinanceDataProvider

class ConsoleAlertSystem:
    """Sistema de alertas por consola con colores y sonidos"""
    
    def __init__(self):
        self.alert_history = deque(maxlen=50)  # Últimas 50 alertas
        self.stats = {
            'total_alerts': 0,
            'high_priority': 0,
            'medium_priority': 0,
            'low_priority': 0,
            'anomalies': 0,
            'patterns': 0,
            'xai_opportunities': 0
        }
        
    def clear_screen(self):
        """Limpiar pantalla"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def print_header(self):
        """Imprimir header del sistema"""
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}🧠 SICAR IA CONTINUA - FASE 2: ALERTAS INTELIGENTES")
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.WHITE}🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Estado: {Fore.GREEN}ACTIVO{Style.RESET_ALL}")
        print()
        
    def print_stats(self):
        """Imprimir estadísticas en tiempo real"""
        print(f"{Fore.MAGENTA}📊 ESTADÍSTICAS EN TIEMPO REAL:")
        print(f"{Fore.WHITE}├─ Total Alertas: {Fore.YELLOW}{self.stats['total_alerts']}")
        print(f"{Fore.WHITE}├─ 🔴 Alta Prioridad: {Fore.RED}{self.stats['high_priority']}")
        print(f"{Fore.WHITE}├─ 🟡 Media Prioridad: {Fore.YELLOW}{self.stats['medium_priority']}")
        print(f"{Fore.WHITE}├─ 🟢 Baja Prioridad: {Fore.GREEN}{self.stats['low_priority']}")
        print(f"{Fore.WHITE}├─ 🚨 Anomalías: {Fore.RED}{self.stats['anomalies']}")
        print(f"{Fore.WHITE}├─ 📈 Patrones: {Fore.BLUE}{self.stats['patterns']}")
        print(f"{Fore.WHITE}└─ 🧠 Oportunidades XAI: {Fore.CYAN}{self.stats['xai_opportunities']}")
        print()
        
    def print_recent_alerts(self):
        """Imprimir alertas recientes"""
        print(f"{Fore.MAGENTA}🔔 ALERTAS RECIENTES (Últimas 10):")
        if not self.alert_history:
            print(f"{Fore.LIGHTBLACK_EX}   No hay alertas recientes...")
        else:
            for alert in list(self.alert_history)[-10:]:
                priority_color = {
                    'HIGH': Fore.RED,
                    'MEDIUM': Fore.YELLOW,
                    'LOW': Fore.GREEN
                }.get(alert['priority'], Fore.WHITE)
                
                print(f"{Fore.WHITE}├─ {priority_color}{alert['timestamp']} | {alert['symbol']} | {alert['type']}")
                print(f"{Fore.WHITE}│  {Fore.LIGHTBLACK_EX}{alert['message']}")
        print()
        
    def show_alert(self, alert_type, symbol, message, priority='MEDIUM', details=None):
        """Mostrar alerta con formato visual"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Colores según prioridad
        colors = {
            'HIGH': {'fg': Fore.RED, 'bg': Back.RED, 'icon': '🚨'},
            'MEDIUM': {'fg': Fore.YELLOW, 'bg': Back.YELLOW, 'icon': '⚠️'},
            'LOW': {'fg': Fore.GREEN, 'bg': Back.GREEN, 'icon': '💡'}
        }
        
        color = colors.get(priority, colors['MEDIUM'])
        
        # Sonido según prioridad
        if priority == 'HIGH':
            try:
                winsound.Beep(1000, 500)  # Frecuencia alta, duración media
            except:
                pass
        elif priority == 'MEDIUM':
            try:
                winsound.Beep(800, 300)
            except:
                pass
                
        # Mostrar alerta
        print(f"\n{color['bg']}{Fore.BLACK} {color['icon']} ALERTA {priority} {Style.RESET_ALL}")
        print(f"{color['fg']}┌─ {timestamp} | {symbol} | {alert_type}")
        print(f"{color['fg']}├─ {message}")
        if details:
            for key, value in details.items():
                print(f"{color['fg']}├─ {key}: {value}")
        print(f"{color['fg']}└─{'─'*50}{Style.RESET_ALL}")
        
        # Guardar en historial
        self.alert_history.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'type': alert_type,
            'message': message,
            'priority': priority,
            'details': details
        })
        
        # Actualizar estadísticas
        self.stats['total_alerts'] += 1
        if priority == 'HIGH':
            self.stats['high_priority'] += 1
        elif priority == 'MEDIUM':
            self.stats['medium_priority'] += 1
        else:
            self.stats['low_priority'] += 1
            
        if alert_type == 'ANOMALIA':
            self.stats['anomalies'] += 1
        elif alert_type == 'PATRON':
            self.stats['patterns'] += 1
        elif alert_type == 'XAI_OPORTUNIDAD':
            self.stats['xai_opportunities'] += 1

class IAContinuaFase2:
    """Sistema de IA Continua - Fase 2: Alertas Inteligentes"""
    
    def __init__(self):
        self.setup_logging()
        self.setup_database()
        self.setup_modules()
        self.alert_system = ConsoleAlertSystem()
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT']
        self.running = False
        self.last_prices = {}
        
        # Filtros de calidad para alertas
        self.quality_filters = {
            'min_anomaly_score': 0.7,
            'min_pattern_confidence': 0.75,
            'min_xai_opportunity_score': 0.8,
            'min_volume_ratio': 1.5,
            'cooldown_minutes': 5  # Evitar spam de alertas del mismo símbolo
        }
        
        self.last_alert_time = {}  # Control de cooldown
        
    def setup_logging(self):
        """Configurar logging silencioso"""
        logging.basicConfig(
            level=logging.WARNING,  # Solo errores y warnings
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ia_continua_fase2.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_database(self):
        """Usar la misma BD de Fase 1"""
        self.db_path = 'ia_continua_detecciones.db'
        
    def setup_modules(self):
        """Inicializar módulos de IA"""
        try:
            self.anomaly_detector = MarketAnomalyDetector()
            self.pattern_recognition = AdvancedPatternRecognition()
            self.data_provider = BinanceDataProvider()
        except Exception as e:
            self.logger.error(f"Error inicializando módulos: {e}")
            
    def can_send_alert(self, symbol):
        """Verificar si se puede enviar alerta (control de cooldown)"""
        now = datetime.now()
        if symbol in self.last_alert_time:
            time_diff = (now - self.last_alert_time[symbol]).total_seconds() / 60
            if time_diff < self.quality_filters['cooldown_minutes']:
                return False
        return True
        
    def update_alert_time(self, symbol):
        """Actualizar tiempo de última alerta"""
        self.last_alert_time[symbol] = datetime.now()
        
    async def monitor_symbol_with_alerts(self, symbol):
        """Monitorear símbolo con sistema de alertas"""
        while self.running:
            try:
                # Obtener datos actuales
                data = await self.get_symbol_data(symbol)
                if data is None:
                    await asyncio.sleep(60)
                    continue
                
                current_price = float(data['close'].iloc[-1])
                self.last_prices[symbol] = current_price
                
                # Detectar anomalías con alertas
                await self.detect_anomalies_with_alerts(symbol, data)
                
                # Detectar patrones con alertas
                await self.detect_patterns_with_alerts(symbol, data)
                
                # Análisis XAI con alertas cada 5 minutos
                if datetime.now().minute % 5 == 0:
                    await self.analyze_xai_with_alerts(symbol, data)
                
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Error monitoreando {symbol}: {e}")
                await asyncio.sleep(60)
                
    async def get_symbol_data(self, symbol):
        """Obtener datos del símbolo (mismo que Fase 1)"""
        try:
            klines = self.data_provider.get_historical_data(symbol, '1m', 60)
            if not klines:
                return None
                
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
                
            return df
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos para {symbol}: {e}")
            return None
            
    async def detect_anomalies_with_alerts(self, symbol, data):
        """Detectar anomalías y enviar alertas"""
        try:
            if not self.can_send_alert(symbol):
                return
                
            features = self.prepare_anomaly_features(data)
            is_anomaly, score = self.anomaly_detector.detect_anomaly(features)
            
            if is_anomaly and score >= self.quality_filters['min_anomaly_score']:
                current_price = float(data['close'].iloc[-1])
                volume_ratio = float(data['volume'].iloc[-1]) / float(data['volume'].mean())
                
                if volume_ratio >= self.quality_filters['min_volume_ratio']:
                    # Determinar prioridad
                    if score >= 0.9 and volume_ratio >= 3.0:
                        priority = 'HIGH'
                    elif score >= 0.8 and volume_ratio >= 2.0:
                        priority = 'MEDIUM'
                    else:
                        priority = 'LOW'
                    
                    # Enviar alerta
                    self.alert_system.show_alert(
                        alert_type='ANOMALIA',
                        symbol=symbol,
                        message=f"Anomalía de mercado detectada - Score: {score:.1%}",
                        priority=priority,
                        details={
                            'Precio': f"${current_price:.4f}",
                            'Volumen Ratio': f"{volume_ratio:.1f}x",
                            'Score Anomalía': f"{score:.1%}",
                            'Acción Sugerida': 'MONITOREAR CLOSELY' if priority == 'HIGH' else 'OBSERVAR'
                        }
                    )
                    
                    self.update_alert_time(symbol)
                    
                    # Guardar en BD
                    self.save_anomaly_detection(symbol, score, current_price, volume_ratio)
                    
        except Exception as e:
            self.logger.error(f"Error detectando anomalías para {symbol}: {e}")
            
    async def detect_patterns_with_alerts(self, symbol, data):
        """Detectar patrones y enviar alertas"""
        try:
            if not self.can_send_alert(symbol):
                return
                
            patterns = self.pattern_recognition.detect_patterns(data)
            
            for pattern in patterns:
                if pattern['confidence'] >= self.quality_filters['min_pattern_confidence']:
                    current_price = float(data['close'].iloc[-1])
                    
                    # Determinar prioridad
                    if pattern['confidence'] >= 0.9:
                        priority = 'HIGH'
                    elif pattern['confidence'] >= 0.8:
                        priority = 'MEDIUM'
                    else:
                        priority = 'LOW'
                    
                    # Enviar alerta
                    self.alert_system.show_alert(
                        alert_type='PATRON',
                        symbol=symbol,
                        message=f"Patrón {pattern['type']} detectado - Confianza: {pattern['confidence']:.1%}",
                        priority=priority,
                        details={
                            'Precio': f"${current_price:.4f}",
                            'Tipo Patrón': pattern['type'],
                            'Confianza': f"{pattern['confidence']:.1%}",
                            'Dirección': pattern.get('direction', 'N/A'),
                            'Acción Sugerida': 'CONSIDERAR ENTRADA' if priority == 'HIGH' else 'MONITOREAR'
                        }
                    )
                    
                    self.update_alert_time(symbol)
                    
                    # Guardar en BD
                    self.save_pattern_detection(symbol, pattern, current_price)
                    break  # Solo una alerta por símbolo por ciclo
                    
        except Exception as e:
            self.logger.error(f"Error detectando patrones para {symbol}: {e}")
            
    async def analyze_xai_with_alerts(self, symbol, data):
        """Análisis XAI con alertas"""
        try:
            market_data = {
                'symbol': symbol,
                'price': float(data['close'].iloc[-1]),
                'volume': float(data['volume'].iloc[-1]),
                'price_change': float(data['close'].pct_change().iloc[-1]),
                'volatility': float(data['close'].pct_change().std())
            }
            
            score_oportunidad = self.calculate_opportunity_score(data)
            
            if score_oportunidad >= self.quality_filters['min_xai_opportunity_score']:
                if not self.can_send_alert(symbol):
                    return
                    
                reporte = generate_cognitive_report(
                    market_data, 
                    "MONITOR", 
                    "continuous_ai", 
                    score_oportunidad,
                    {"source": "fase2_alerts", "timestamp": datetime.now().isoformat()}
                )
                
                # Determinar prioridad
                if score_oportunidad >= 0.95:
                    priority = 'HIGH'
                elif score_oportunidad >= 0.85:
                    priority = 'MEDIUM'
                else:
                    priority = 'LOW'
                
                # Enviar alerta
                self.alert_system.show_alert(
                    alert_type='XAI_OPORTUNIDAD',
                    symbol=symbol,
                    message=f"Oportunidad XAI detectada - Score: {score_oportunidad:.1%}",
                    priority=priority,
                    details={
                        'Precio': f"${market_data['price']:.4f}",
                        'Score Oportunidad': f"{score_oportunidad:.1%}",
                        'Cambio Precio': f"{market_data['price_change']:.2%}",
                        'Volatilidad': f"{market_data['volatility']:.2%}",
                        'Recomendación': 'ALTA PROBABILIDAD' if priority == 'HIGH' else 'EVALUAR'
                    }
                )
                
                self.update_alert_time(symbol)
                
                # Guardar en BD
                self.save_xai_analysis(symbol, reporte, score_oportunidad)
                
        except Exception as e:
            self.logger.error(f"Error en análisis XAI para {symbol}: {e}")
            
    def prepare_anomaly_features(self, data):
        """Preparar features para detección de anomalías"""
        try:
            data['returns'] = data['close'].pct_change()
            data['volume_ratio'] = data['volume'] / data['volume'].rolling(20).mean()
            data['volatility'] = data['returns'].rolling(10).std()
            data['price_range'] = (data['high'] - data['low']) / data['close']
            
            latest = data.iloc[-1]
            
            features = [
                latest['returns'] if not pd.isna(latest['returns']) else 0,
                latest['volume_ratio'] if not pd.isna(latest['volume_ratio']) else 1,
                latest['volatility'] if not pd.isna(latest['volatility']) else 0,
                latest['price_range'] if not pd.isna(latest['price_range']) else 0
            ]
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error preparando features: {e}")
            return [0, 1, 0, 0]
            
    def calculate_opportunity_score(self, data):
        """Calcular score de oportunidad"""
        try:
            volume_spike = float(data['volume'].iloc[-1]) / float(data['volume'].mean())
            price_momentum = abs(float(data['close'].pct_change().iloc[-1]))
            volatility = float(data['close'].pct_change().std())
            
            score = min(1.0, (
                (volume_spike - 1) * 0.3 +
                price_momentum * 10 * 0.4 +
                volatility * 5 * 0.3
            ))
            
            return max(0, score)
            
        except Exception as e:
            self.logger.error(f"Error calculando opportunity score: {e}")
            return 0.0
            
    def save_anomaly_detection(self, symbol, score, precio_actual, volumen_ratio):
        """Guardar detección de anomalía"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO anomalias_detectadas 
                (symbol, tipo_anomalia, score_anomalia, precio_actual, volumen_ratio, volatilidad, detalles)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, "high_quality_anomaly", score, precio_actual, volumen_ratio, 0, f"Alerta Fase 2 - Score {score:.3f}"))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error guardando anomalía: {e}")
            
    def save_pattern_detection(self, symbol, pattern, precio_actual):
        """Guardar detección de patrón"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO patrones_detectados 
                (symbol, tipo_patron, confianza, precio_actual, direccion_predicha, detalles)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, pattern['type'], pattern['confidence'], precio_actual, 
                  pattern.get('direction', 'unknown'), f"Alerta Fase 2 - {json.dumps(pattern)}"))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error guardando patrón: {e}")
            
    def save_xai_analysis(self, symbol, reporte, score_oportunidad):
        """Guardar análisis XAI"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analisis_xai 
                (symbol, reporte_cognitivo, score_oportunidad, factores_clave, recomendacion)
                VALUES (?, ?, ?, ?, ?)
            ''', (symbol, reporte, score_oportunidad, "high_quality_factors", 
                  "high_opportunity" if score_oportunidad >= 0.9 else "monitor"))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error guardando análisis XAI: {e}")
            
    async def update_console_display(self):
        """Actualizar display de consola cada 30 segundos"""
        while self.running:
            try:
                self.alert_system.clear_screen()
                self.alert_system.print_header()
                
                # Mostrar precios actuales
                print(f"{Fore.MAGENTA}💰 PRECIOS ACTUALES:")
                for symbol, price in self.last_prices.items():
                    print(f"{Fore.WHITE}├─ {symbol}: {Fore.GREEN}${price:.4f}")
                print()
                
                self.alert_system.print_stats()
                self.alert_system.print_recent_alerts()
                
                print(f"{Fore.CYAN}{'─'*80}")
                print(f"{Fore.LIGHTBLACK_EX}Próxima actualización en 30 segundos... | Ctrl+C para detener")
                print(f"{Fore.CYAN}{'─'*80}{Style.RESET_ALL}")
                
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error actualizando display: {e}")
                await asyncio.sleep(30)
                
    async def start_monitoring_with_alerts(self):
        """Iniciar monitoreo con sistema de alertas"""
        print(f"{Fore.GREEN}🚀 INICIANDO IA CONTINUA - FASE 2: ALERTAS INTELIGENTES")
        print(f"{Fore.YELLOW}📊 Monitoreando símbolos: {', '.join(self.symbols)}")
        print(f"{Fore.CYAN}⚙️ Filtros de calidad activados")
        print(f"{Fore.WHITE}{'='*80}{Style.RESET_ALL}")
        
        self.running = True
        
        # Crear tareas
        tasks = []
        
        # Monitoreo de símbolos
        for symbol in self.symbols:
            task = asyncio.create_task(self.monitor_symbol_with_alerts(symbol))
            tasks.append(task)
            
        # Actualización de consola
        display_task = asyncio.create_task(self.update_console_display())
        tasks.append(display_task)
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}🛑 Deteniendo sistema de alertas...")
            self.running = False
            print(f"{Fore.GREEN}✅ Sistema detenido correctamente{Style.RESET_ALL}")

if __name__ == "__main__":
    sistema = IAContinuaFase2()
    asyncio.run(sistema.start_monitoring_with_alerts())