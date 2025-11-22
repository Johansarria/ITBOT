#!/usr/bin/env python3
"""
ALERTA CRÍTICA: Monitoreo de Rompimiento Bajista BTCUSDT
Basado en el análisis que detectó un rompimiento bajista inminente con score 90
"""

import json
import time
import requests
import logging
from datetime import datetime
from typing import Dict, Optional
import sqlite3

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | BTC_BREAKOUT | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('btc_breakout_alert.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BTCBreakoutAlert:
    def __init__(self):
        # Niveles críticos identificados en el análisis comparativo
        self.entry_level = 110128.09      # Nivel de entrada del rompimiento
        self.resistance_level = 110291.17  # Resistencia fuerte
        self.stop_loss = 110350.00        # Stop loss sugerido
        self.take_profit_1 = 109800.00    # Primer objetivo
        self.take_profit_2 = 109500.00    # Segundo objetivo
        
        # Configuración de alertas
        self.alert_triggered = False
        self.breakout_confirmed = False
        self.position_active = False
        
        # Base de datos
        self.init_database()
        
    def init_database(self):
        """Inicializar base de datos para el seguimiento"""
        try:
            conn = sqlite3.connect('btc_breakout_monitoring.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS breakout_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    price REAL NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    action_required TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Base de datos de monitoreo BTC inicializada")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
    
    def get_btc_price(self) -> Optional[float]:
        """Obtener precio actual de BTCUSDT"""
        try:
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            data = response.json()
            return float(data['price'])
            
        except Exception as e:
            logger.error(f"Error obteniendo precio BTC: {e}")
            return None
    
    def get_market_data(self) -> Optional[Dict]:
        """Obtener datos completos del mercado"""
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            return {
                'price': float(data['lastPrice']),
                'volume': float(data['quoteVolume']),
                'change_24h': float(data['priceChangePercent']),
                'high_24h': float(data['highPrice']),
                'low_24h': float(data['lowPrice']),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado: {e}")
            return None
    
    def log_alert(self, alert_type: str, message: str, action: str, price: float):
        """Registrar alerta en la base de datos"""
        try:
            conn = sqlite3.connect('btc_breakout_monitoring.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO breakout_alerts (timestamp, price, alert_type, message, action_required)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                price,
                alert_type,
                message,
                action
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error registrando alerta: {e}")
    
    def check_breakout_conditions(self, market_data: Dict) -> str:
        """Verificar condiciones de rompimiento"""
        price = market_data['price']
        volume = market_data['volume']
        
        # Verificar si el precio está cerca del nivel de entrada
        distance_to_entry = abs(price - self.entry_level)
        distance_percent = (distance_to_entry / self.entry_level) * 100
        
        if distance_percent <= 0.1:  # Muy cerca del nivel crítico
            return "CRITICAL_PROXIMITY"
        elif price <= self.entry_level and not self.breakout_confirmed:
            return "BREAKOUT_TRIGGERED"
        elif price >= self.resistance_level:
            return "RESISTANCE_TEST"
        elif price <= self.take_profit_1 and self.breakout_confirmed:
            return "TARGET_1_REACHED"
        elif price <= self.take_profit_2 and self.breakout_confirmed:
            return "TARGET_2_REACHED"
        else:
            return "MONITORING"
    
    def send_critical_alert(self, alert_type: str, price: float, message: str):
        """Enviar alerta crítica"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        print("\n" + "="*80)
        print("🚨 ALERTA CRÍTICA BTC ROMPIMIENTO BAJISTA 🚨")
        print("="*80)
        print(f"⏰ Hora: {timestamp}")
        print(f"💰 Precio: ${price:,.2f}")
        print(f"🔔 Tipo: {alert_type}")
        print(f"📢 Mensaje: {message}")
        print("="*80)
        
        # Registrar en log
        logger.critical(f"🚨 {alert_type}: ${price:,.2f} - {message}")
        
        # Guardar en base de datos
        self.log_alert(alert_type, message, "IMMEDIATE_ACTION_REQUIRED", price)
    
    def monitor_breakout(self):
        """Monitorear el rompimiento en tiempo real"""
        logger.info("🚀 Iniciando monitoreo de rompimiento bajista BTCUSDT...")
        logger.info(f"📊 Nivel de entrada: ${self.entry_level:,.2f}")
        logger.info(f"🛡️ Resistencia: ${self.resistance_level:,.2f}")
        logger.info(f"🎯 Objetivo 1: ${self.take_profit_1:,.2f}")
        logger.info(f"🎯 Objetivo 2: ${self.take_profit_2:,.2f}")
        
        while True:
            try:
                market_data = self.get_market_data()
                if not market_data:
                    time.sleep(5)
                    continue
                
                price = market_data['price']
                condition = self.check_breakout_conditions(market_data)
                
                # Mostrar precio actual cada 30 segundos
                if int(time.time()) % 30 == 0:
                    distance = abs(price - self.entry_level)
                    print(f"⏰ {datetime.now().strftime('%H:%M:%S')} | "
                          f"BTC: ${price:,.2f} | "
                          f"Distancia al rompimiento: ${distance:.2f} | "
                          f"Estado: {condition}")
                
                # Procesar condiciones
                if condition == "CRITICAL_PROXIMITY":
                    if not self.alert_triggered:
                        self.send_critical_alert(
                            "PROXIMIDAD_CRÍTICA",
                            price,
                            f"BTC está a ${abs(price - self.entry_level):.2f} del nivel de rompimiento!"
                        )
                        self.alert_triggered = True
                
                elif condition == "BREAKOUT_TRIGGERED":
                    self.send_critical_alert(
                        "ROMPIMIENTO_CONFIRMADO",
                        price,
                        f"¡ROMPIMIENTO BAJISTA CONFIRMADO! Precio: ${price:,.2f} < ${self.entry_level:,.2f}"
                    )
                    self.breakout_confirmed = True
                
                elif condition == "RESISTANCE_TEST":
                    self.send_critical_alert(
                        "PRUEBA_RESISTENCIA",
                        price,
                        f"BTC probando resistencia en ${self.resistance_level:,.2f}"
                    )
                
                elif condition == "TARGET_1_REACHED":
                    self.send_critical_alert(
                        "OBJETIVO_1_ALCANZADO",
                        price,
                        f"¡Primer objetivo alcanzado! ${self.take_profit_1:,.2f}"
                    )
                
                elif condition == "TARGET_2_REACHED":
                    self.send_critical_alert(
                        "OBJETIVO_2_ALCANZADO",
                        price,
                        f"¡Segundo objetivo alcanzado! ${self.take_profit_2:,.2f}"
                    )
                
                time.sleep(5)  # Verificar cada 5 segundos
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoreo detenido por el usuario")
                break
            except Exception as e:
                logger.error(f"❌ Error en monitoreo: {e}")
                time.sleep(10)

def main():
    """Función principal"""
    print("🚨 SISTEMA DE ALERTA CRÍTICA - ROMPIMIENTO BAJISTA BTCUSDT")
    print("="*70)
    print("📊 Basado en análisis comparativo con score de rompimiento: 90")
    print("🎯 Configuración de trading:")
    print("   • Entrada: $110,128.09")
    print("   • Stop Loss: $110,350.00")
    print("   • Objetivo 1: $109,800.00")
    print("   • Objetivo 2: $109,500.00")
    print("="*70)
    
    monitor = BTCBreakoutAlert()
    
    try:
        monitor.monitor_breakout()
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())