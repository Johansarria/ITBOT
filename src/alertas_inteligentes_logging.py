#!/usr/bin/env python3
"""
Sistema de Alertas Inteligentes con Logging Avanzado
Detecta cambios significativos del mercado y los registra para análisis posterior
"""

import json
import os
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import threading
from dataclasses import dataclass, asdict
import sqlite3
import smtplib
try:
    from email.mime.text import MIMEText as MimeText
    from email.mime.multipart import MIMEMultipart as MimeMultipart
except ImportError:
    # Fallback para versiones más antiguas
    from email.MIMEText import MIMEText as MimeText
    from email.MIMEMultipart import MIMEMultipart as MimeMultipart

# Configurar logging avanzado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | ALERTAS | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('alertas_inteligentes.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MarketAlert:
    id: str
    symbol: str
    alert_type: str  # 'PRICE_SPIKE', 'VOLUME_SURGE', 'VOLATILITY_HIGH', 'TREND_CHANGE'
    severity: str    # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    message: str
    current_value: float
    previous_value: float
    change_percent: float
    timestamp: datetime
    metadata: Dict
    
    def to_dict(self):
        return {
            'id': self.id,
            'symbol': self.symbol,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'current_value': self.current_value,
            'previous_value': self.previous_value,
            'change_percent': self.change_percent,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

class IntelligentAlertsSystem:
    def __init__(self):
        self.config = self.load_config()
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 'LINKUSDT', 'LTCUSDT']
        self.running = False
        
        # Configuración de alertas
        self.price_spike_threshold = 5.0    # % cambio de precio
        self.volume_surge_threshold = 200.0  # % aumento de volumen
        self.volatility_threshold = 10.0     # % volatilidad
        
        # Historial de datos para comparación
        self.price_history = {}
        self.volume_history = {}
        self.last_alerts = {}
        
        # Base de datos para logging
        self.init_database()
        
        # Configuración de notificaciones
        self.notification_methods = ['console', 'file', 'database']
        
    def load_config(self) -> Dict:
        """Cargar configuración"""
        try:
            with open('sicar_config.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            return {}
    
    def init_database(self):
        """Inicializar base de datos para logging"""
        try:
            self.db_path = 'alertas_database.db'
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_alerts (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    previous_value REAL NOT NULL,
                    change_percent REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    price REAL NOT NULL,
                    volume REAL NOT NULL,
                    change_24h REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Base de datos de alertas inicializada")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Obtener datos de mercado"""
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            return {
                'symbol': symbol,
                'price': float(data['lastPrice']),
                'volume': float(data['quoteVolume']),
                'change_24h': float(data['priceChangePercent']),
                'high_24h': float(data['highPrice']),
                'low_24h': float(data['lowPrice']),
                'trades_count': int(data['count']),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo datos para {symbol}: {e}")
            return None
    
    def log_market_data(self, market_data: Dict):
        """Registrar datos de mercado en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO market_data_log (symbol, price, volume, change_24h, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                market_data['symbol'],
                market_data['price'],
                market_data['volume'],
                market_data['change_24h'],
                market_data['timestamp'].isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error registrando datos de mercado: {e}")
    
    def detect_price_spike(self, symbol: str, current_data: Dict) -> Optional[MarketAlert]:
        """Detectar picos de precio significativos"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        current_price = current_data['price']
        self.price_history[symbol].append(current_price)
        
        # Mantener historial de últimos 10 puntos
        if len(self.price_history[symbol]) > 10:
            self.price_history[symbol] = self.price_history[symbol][-10:]
        
        if len(self.price_history[symbol]) < 3:
            return None
        
        # Calcular cambio promedio vs precio actual
        avg_price = sum(self.price_history[symbol][:-1]) / len(self.price_history[symbol][:-1])
        change_percent = ((current_price - avg_price) / avg_price) * 100
        
        if abs(change_percent) >= self.price_spike_threshold:
            severity = self.determine_severity(abs(change_percent), [5, 10, 20])
            
            alert_id = f"PRICE_{symbol}_{int(time.time())}"
            direction = "ALZA" if change_percent > 0 else "BAJA"
            
            return MarketAlert(
                id=alert_id,
                symbol=symbol,
                alert_type='PRICE_SPIKE',
                severity=severity,
                message=f"🚨 PICO DE PRECIO: {symbol} {direction} de {change_percent:+.2f}% (${current_price:.2f})",
                current_value=current_price,
                previous_value=avg_price,
                change_percent=change_percent,
                timestamp=datetime.now(),
                metadata={
                    'direction': direction,
                    'avg_price': avg_price,
                    'threshold_used': self.price_spike_threshold
                }
            )
        
        return None
    
    def detect_volume_surge(self, symbol: str, current_data: Dict) -> Optional[MarketAlert]:
        """Detectar aumentos súbitos de volumen"""
        if symbol not in self.volume_history:
            self.volume_history[symbol] = []
        
        current_volume = current_data['volume']
        self.volume_history[symbol].append(current_volume)
        
        # Mantener historial de últimos 5 puntos
        if len(self.volume_history[symbol]) > 5:
            self.volume_history[symbol] = self.volume_history[symbol][-5:]
        
        if len(self.volume_history[symbol]) < 3:
            return None
        
        # Calcular volumen promedio vs actual
        avg_volume = sum(self.volume_history[symbol][:-1]) / len(self.volume_history[symbol][:-1])
        
        if avg_volume > 0:
            change_percent = ((current_volume - avg_volume) / avg_volume) * 100
            
            if change_percent >= self.volume_surge_threshold:
                severity = self.determine_severity(change_percent, [200, 500, 1000])
                
                alert_id = f"VOLUME_{symbol}_{int(time.time())}"
                
                return MarketAlert(
                    id=alert_id,
                    symbol=symbol,
                    alert_type='VOLUME_SURGE',
                    severity=severity,
                    message=f"📈 AUMENTO DE VOLUMEN: {symbol} +{change_percent:.1f}% (${current_volume/1000000:.1f}M)",
                    current_value=current_volume,
                    previous_value=avg_volume,
                    change_percent=change_percent,
                    timestamp=datetime.now(),
                    metadata={
                        'avg_volume': avg_volume,
                        'volume_millions': current_volume / 1000000,
                        'threshold_used': self.volume_surge_threshold
                    }
                )
        
        return None
    
    def detect_high_volatility(self, symbol: str, current_data: Dict) -> Optional[MarketAlert]:
        """Detectar alta volatilidad"""
        high_24h = current_data['high_24h']
        low_24h = current_data['low_24h']
        current_price = current_data['price']
        
        if low_24h > 0:
            volatility = ((high_24h - low_24h) / low_24h) * 100
            
            if volatility >= self.volatility_threshold:
                severity = self.determine_severity(volatility, [10, 20, 40])
                
                alert_id = f"VOLATILITY_{symbol}_{int(time.time())}"
                
                return MarketAlert(
                    id=alert_id,
                    symbol=symbol,
                    alert_type='VOLATILITY_HIGH',
                    severity=severity,
                    message=f"⚡ ALTA VOLATILIDAD: {symbol} {volatility:.1f}% (${low_24h:.2f} - ${high_24h:.2f})",
                    current_value=volatility,
                    previous_value=0,
                    change_percent=volatility,
                    timestamp=datetime.now(),
                    metadata={
                        'high_24h': high_24h,
                        'low_24h': low_24h,
                        'current_price': current_price,
                        'threshold_used': self.volatility_threshold
                    }
                )
        
        return None
    
    def detect_trend_change(self, symbol: str, current_data: Dict) -> Optional[MarketAlert]:
        """Detectar cambios de tendencia"""
        change_24h = current_data['change_24h']
        
        # Detectar cambios significativos de tendencia
        if abs(change_24h) >= 15.0:  # Cambio mayor al 15%
            severity = self.determine_severity(abs(change_24h), [15, 25, 40])
            
            alert_id = f"TREND_{symbol}_{int(time.time())}"
            trend = "ALCISTA" if change_24h > 0 else "BAJISTA"
            
            return MarketAlert(
                id=alert_id,
                symbol=symbol,
                alert_type='TREND_CHANGE',
                severity=severity,
                message=f"🔄 CAMBIO DE TENDENCIA: {symbol} tendencia {trend} {change_24h:+.1f}% en 24h",
                current_value=change_24h,
                previous_value=0,
                change_percent=change_24h,
                timestamp=datetime.now(),
                metadata={
                    'trend_direction': trend,
                    'change_24h': change_24h,
                    'threshold_used': 15.0
                }
            )
        
        return None
    
    def determine_severity(self, value: float, thresholds: List[float]) -> str:
        """Determinar severidad basada en umbrales"""
        if value >= thresholds[2]:
            return 'CRITICAL'
        elif value >= thresholds[1]:
            return 'HIGH'
        elif value >= thresholds[0]:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def should_send_alert(self, alert: MarketAlert) -> bool:
        """Verificar si se debe enviar la alerta (evitar spam)"""
        key = f"{alert.symbol}_{alert.alert_type}"
        current_time = datetime.now()
        
        # Verificar si ya se envió una alerta similar recientemente
        if key in self.last_alerts:
            time_diff = (current_time - self.last_alerts[key]).total_seconds()
            
            # Cooldown basado en severidad
            cooldown_seconds = {
                'LOW': 300,      # 5 minutos
                'MEDIUM': 180,   # 3 minutos
                'HIGH': 120,     # 2 minutos
                'CRITICAL': 60   # 1 minuto
            }
            
            if time_diff < cooldown_seconds.get(alert.severity, 300):
                return False
        
        self.last_alerts[key] = current_time
        return True
    
    def save_alert_to_database(self, alert: MarketAlert):
        """Guardar alerta en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO market_alerts 
                (id, symbol, alert_type, severity, message, current_value, previous_value, 
                 change_percent, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert.id,
                alert.symbol,
                alert.alert_type,
                alert.severity,
                alert.message,
                alert.current_value,
                alert.previous_value,
                alert.change_percent,
                alert.timestamp.isoformat(),
                json.dumps(alert.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error guardando alerta en BD: {e}")
    
    def save_alert_to_file(self, alert: MarketAlert):
        """Guardar alerta en archivo JSON"""
        try:
            alerts_file = 'alertas_historial.json'
            
            # Cargar alertas existentes
            if os.path.exists(alerts_file):
                with open(alerts_file, 'r') as f:
                    alerts_data = json.load(f)
            else:
                alerts_data = []
            
            # Agregar nueva alerta
            alerts_data.append(alert.to_dict())
            
            # Mantener solo las últimas 1000 alertas
            if len(alerts_data) > 1000:
                alerts_data = alerts_data[-1000:]
            
            # Guardar
            with open(alerts_file, 'w') as f:
                json.dump(alerts_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error guardando alerta en archivo: {e}")
    
    def display_alert(self, alert: MarketAlert):
        """Mostrar alerta en consola con formato avanzado"""
        # Emojis por severidad
        severity_emojis = {
            'LOW': '🟡',
            'MEDIUM': '🟠',
            'HIGH': '🔴',
            'CRITICAL': '🚨'
        }
        
        # Emojis por tipo
        type_emojis = {
            'PRICE_SPIKE': '💰',
            'VOLUME_SURGE': '📈',
            'VOLATILITY_HIGH': '⚡',
            'TREND_CHANGE': '🔄'
        }
        
        emoji = severity_emojis.get(alert.severity, '⚠️')
        type_emoji = type_emojis.get(alert.alert_type, '📊')
        
        print(f"\n{emoji} {type_emoji} ALERTA {alert.severity}")
        print("─" * 80)
        print(f"🕐 {alert.timestamp.strftime('%H:%M:%S')} | {alert.message}")
        print(f"📊 Cambio: {alert.change_percent:+.2f}% | Valor actual: {alert.current_value:.2f}")
        
        # Información adicional según el tipo
        if alert.metadata:
            if alert.alert_type == 'VOLUME_SURGE':
                print(f"💧 Volumen: ${alert.metadata.get('volume_millions', 0):.1f}M USDT")
            elif alert.alert_type == 'VOLATILITY_HIGH':
                print(f"📏 Rango 24h: ${alert.metadata.get('low_24h', 0):.2f} - ${alert.metadata.get('high_24h', 0):.2f}")
        
        print("─" * 80)
    
    def process_alerts(self, alerts: List[MarketAlert]):
        """Procesar y enviar alertas"""
        for alert in alerts:
            if self.should_send_alert(alert):
                # Mostrar en consola
                if 'console' in self.notification_methods:
                    self.display_alert(alert)
                
                # Guardar en archivo
                if 'file' in self.notification_methods:
                    self.save_alert_to_file(alert)
                
                # Guardar en base de datos
                if 'database' in self.notification_methods:
                    self.save_alert_to_database(alert)
                
                # Log
                logger.info(f"ALERTA {alert.severity}: {alert.message}")
    
    def analyze_market(self) -> List[MarketAlert]:
        """Analizar mercado y generar alertas"""
        alerts = []
        
        for symbol in self.symbols:
            try:
                market_data = self.get_market_data(symbol)
                if not market_data:
                    continue
                
                # Registrar datos de mercado
                self.log_market_data(market_data)
                
                # Detectar diferentes tipos de alertas
                detectors = [
                    self.detect_price_spike,
                    self.detect_volume_surge,
                    self.detect_high_volatility,
                    self.detect_trend_change
                ]
                
                for detector in detectors:
                    alert = detector(symbol, market_data)
                    if alert:
                        alerts.append(alert)
                
            except Exception as e:
                logger.error(f"Error analizando {symbol}: {e}")
        
        return alerts
    
    def get_alert_statistics(self) -> Dict:
        """Obtener estadísticas de alertas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Contar alertas por tipo y severidad
            cursor.execute('''
                SELECT alert_type, severity, COUNT(*) 
                FROM market_alerts 
                WHERE timestamp > datetime('now', '-24 hours')
                GROUP BY alert_type, severity
            ''')
            
            stats = {}
            for row in cursor.fetchall():
                alert_type, severity, count = row
                if alert_type not in stats:
                    stats[alert_type] = {}
                stats[alert_type][severity] = count
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def display_statistics(self):
        """Mostrar estadísticas de alertas"""
        stats = self.get_alert_statistics()
        
        if stats:
            print("\n📊 ESTADÍSTICAS DE ALERTAS (ÚLTIMAS 24H)")
            print("─" * 50)
            
            for alert_type, severities in stats.items():
                total = sum(severities.values())
                print(f"{alert_type}: {total} alertas")
                for severity, count in severities.items():
                    print(f"  {severity}: {count}")
            print("─" * 50)
    
    def run_continuous_monitoring(self):
        """Ejecutar monitoreo continuo"""
        logger.info("🔔 Iniciando sistema de alertas inteligentes...")
        self.running = True
        
        while self.running:
            try:
                print(f"\n🔍 {datetime.now().strftime('%H:%M:%S')} - Analizando mercado para alertas...")
                
                # Analizar mercado
                alerts = self.analyze_market()
                
                # Procesar alertas
                if alerts:
                    self.process_alerts(alerts)
                    print(f"✅ {len(alerts)} alertas procesadas")
                else:
                    print("✅ No se detectaron alertas significativas")
                
                # Mostrar estadísticas cada 10 ciclos
                if int(time.time()) % 600 == 0:  # Cada 10 minutos
                    self.display_statistics()
                
                # Esperar antes del siguiente análisis
                time.sleep(60)  # Análisis cada minuto
                
            except KeyboardInterrupt:
                logger.info("🛑 Deteniendo sistema de alertas...")
                break
            except Exception as e:
                logger.error(f"❌ Error en monitoreo: {e}")
                time.sleep(30)
        
        self.running = False

def main():
    """Función principal"""
    print("🔔 SISTEMA DE ALERTAS INTELIGENTES CON LOGGING")
    print("="*60)
    
    alerts_system = IntelligentAlertsSystem()
    
    try:
        alerts_system.run_continuous_monitoring()
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())