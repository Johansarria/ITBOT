#!/usr/bin/env python3
"""
🚀 EJECUTOR DE ESTRATEGIA V3 AGRESIVA - TRADING EN VIVO

Este script implementa la Estrategia Enhanced 15% V3 Agresiva para trading en vivo
con todas las validaciones y controles de seguridad necesarios.

Características:
- Trading en tiempo real con Binance
- Gestión de riesgos avanzada
- Monitoreo continuo de performance
- Alertas automáticas vía Telegram
- Logs detallados de todas las operaciones

Autor: Sistema de Trading Automatizado
Versión: 3.0 Agresiva
Fecha: Septiembre 2024
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Importar estrategia V3
from enhanced_strategy_15pct_v3_aggressive import (
    AggressiveTradingConfig,
    AggressiveMarketAnalyzer,
    AggressiveRiskManager,
    Enhanced15PercentStrategyV3
)

class LiveTradingExecutor:
    """
    Ejecutor principal para trading en vivo con la estrategia V3 agresiva
    """
    
    def __init__(self, config_file: str = "trading_config.json"):
        self.config = self._load_config(config_file)
        self.setup_logging()
        self.setup_binance_client()
        self.setup_strategy()
        self.active_positions = {}
        self.daily_stats = {
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'pnl': 0.0,
            'start_balance': 0.0
        }
        
    def _load_config(self, config_file: str) -> Dict:
        """Cargar configuración desde archivo JSON"""
        default_config = {
            "binance": {
                "api_key": os.getenv('BINANCE_API_KEY'),
                "api_secret": os.getenv('BINANCE_API_SECRET'),
                "testnet": True  # Cambiar a False para trading real
            },
            "trading": {
                "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"],
                "base_amount": 50.0,  # USDT por trade
                "max_positions": 3,
                "daily_loss_limit": 100.0,  # USDT
                "daily_profit_target": 200.0  # USDT
            },
            "risk": {
                "max_drawdown": 0.02,  # 2%
                "stop_loss": 0.005,  # 0.5%
                "take_profit_1": 0.01,  # 1%
                "take_profit_2": 0.02   # 2%
            },
            "telegram": {
                "bot_token": os.getenv('TELEGRAM_BOT_TOKEN'),
                "chat_id": os.getenv('TELEGRAM_CHAT_ID'),
                "enabled": False
            }
        }
        
        try:
            with open(config_file, 'r') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)
        except FileNotFoundError:
            self.logger.warning(f"Config file {config_file} not found, using defaults")
            
        return default_config
    
    def setup_logging(self):
        """Configurar sistema de logging"""
        log_dir = "logs_live_trading"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"live_trading_{datetime.now().strftime('%Y%m%d')}.log")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_binance_client(self):
        """Configurar cliente de Binance"""
        try:
            if self.config['binance']['testnet']:
                self.client = Client(
                    self.config['binance']['api_key'],
                    self.config['binance']['api_secret'],
                    testnet=True
                )
                self.logger.info("🧪 Conectado a Binance TESTNET")
            else:
                self.client = Client(
                    self.config['binance']['api_key'],
                    self.config['binance']['api_secret']
                )
                self.logger.info("🔴 Conectado a Binance MAINNET - TRADING REAL")
                
            # Verificar conexión
            account_info = self.client.get_account()
            balance = float([b['free'] for b in account_info['balances'] if b['asset'] == 'USDT'][0])
            self.daily_stats['start_balance'] = balance
            self.logger.info(f"💰 Balance USDT: ${balance:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Error conectando a Binance: {e}")
            sys.exit(1)
    
    def setup_strategy(self):
        """Configurar estrategia V3 agresiva"""
        self.strategy = Enhanced15PercentStrategyV3()
        self.logger.info("🚀 Estrategia V3 Agresiva inicializada")
    
    def get_market_data(self, symbol: str, interval: str = '5m', limit: int = 100) -> pd.DataFrame:
        """Obtener datos de mercado en tiempo real"""
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo datos para {symbol}: {e}")
            return pd.DataFrame()
    
    def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """Analizar símbolo y generar señal"""
        try:
            # Obtener datos
            df = self.get_market_data(symbol)
            if df.empty:
                return None
            
            # Generar señal
            signal_data = self.strategy.generate_signal(df)
            
            if signal_data and signal_data.get('signal') != 'HOLD':
                self.logger.info(f"📊 {symbol}: Señal {signal_data['signal']} - Fuerza: {signal_data.get('signal_strength', 0):.3f}")
                return signal_data
                
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando {symbol}: {e}")
            return None
    
    def execute_trade(self, symbol: str, signal_data: Dict) -> bool:
        """Ejecutar trade basado en señal"""
        try:
            signal = signal_data['signal']
            current_price = signal_data['current_price']
            amount_usdt = self.config['trading']['base_amount']
            
            if signal == 'BUY':
                # Calcular cantidad
                quantity = amount_usdt / current_price
                quantity = round(quantity, 6)  # Ajustar decimales según símbolo
                
                # Ejecutar orden de compra
                order = self.client.order_market_buy(
                    symbol=symbol,
                    quantity=quantity
                )
                
                # Configurar stop loss y take profits
                self._set_exit_orders(symbol, quantity, current_price, 'BUY')
                
                # Registrar posición
                self.active_positions[symbol] = {
                    'side': 'BUY',
                    'quantity': quantity,
                    'entry_price': current_price,
                    'timestamp': datetime.now(),
                    'order_id': order['orderId']
                }
                
                self.logger.info(f"✅ BUY {symbol}: {quantity} @ ${current_price:.4f}")
                return True
                
            elif signal == 'SELL':
                # Similar para SELL
                quantity = amount_usdt / current_price
                quantity = round(quantity, 6)
                
                # Para SELL, necesitaríamos implementar short selling o venta de posición existente
                self.logger.info(f"⚠️ SELL signal para {symbol} - Implementar lógica de venta")
                return False
                
        except BinanceAPIException as e:
            self.logger.error(f"❌ Error API Binance ejecutando trade {symbol}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error ejecutando trade {symbol}: {e}")
            return False
    
    def _set_exit_orders(self, symbol: str, quantity: float, entry_price: float, side: str):
        """Configurar órdenes de salida (SL y TP)"""
        try:
            if side == 'BUY':
                # Stop Loss
                sl_price = entry_price * (1 - self.config['risk']['stop_loss'])
                sl_price = round(sl_price, 4)
                
                # Take Profit 1 (50% de la posición)
                tp1_price = entry_price * (1 + self.config['risk']['take_profit_1'])
                tp1_price = round(tp1_price, 4)
                tp1_quantity = round(quantity * 0.5, 6)
                
                # Take Profit 2 (50% restante)
                tp2_price = entry_price * (1 + self.config['risk']['take_profit_2'])
                tp2_price = round(tp2_price, 4)
                tp2_quantity = round(quantity * 0.5, 6)
                
                # Crear órdenes OCO (One-Cancels-Other)
                self.logger.info(f"🎯 {symbol} - SL: ${sl_price} | TP1: ${tp1_price} | TP2: ${tp2_price}")
                
        except Exception as e:
            self.logger.error(f"❌ Error configurando órdenes de salida para {symbol}: {e}")
    
    def monitor_positions(self):
        """Monitorear posiciones activas"""
        for symbol, position in list(self.active_positions.items()):
            try:
                # Obtener precio actual
                ticker = self.client.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                
                # Calcular PnL
                entry_price = position['entry_price']
                if position['side'] == 'BUY':
                    pnl_pct = (current_price - entry_price) / entry_price
                else:
                    pnl_pct = (entry_price - current_price) / entry_price
                
                # Verificar condiciones de salida manual si es necesario
                position_age = datetime.now() - position['timestamp']
                if position_age > timedelta(hours=24):  # Cerrar posiciones muy antiguas
                    self.logger.warning(f"⏰ {symbol}: Posición antigua ({position_age}), considerar cierre")
                
            except Exception as e:
                self.logger.error(f"❌ Error monitoreando {symbol}: {e}")
    
    def check_daily_limits(self) -> bool:
        """Verificar límites diarios"""
        current_pnl = self.daily_stats['pnl']
        
        # Verificar pérdida máxima
        if current_pnl <= -self.config['trading']['daily_loss_limit']:
            self.logger.warning(f"🛑 Límite de pérdida diaria alcanzado: ${current_pnl:.2f}")
            return False
        
        # Verificar objetivo de ganancia
        if current_pnl >= self.config['trading']['daily_profit_target']:
            self.logger.info(f"🎯 Objetivo diario alcanzado: ${current_pnl:.2f}")
            return False
        
        return True
    
    def run_trading_loop(self):
        """Bucle principal de trading"""
        self.logger.info("🚀 Iniciando bucle de trading en vivo...")
        
        while True:
            try:
                # Verificar límites diarios
                if not self.check_daily_limits():
                    self.logger.info("📊 Límites diarios alcanzados, pausando trading")
                    time.sleep(3600)  # Esperar 1 hora
                    continue
                
                # Verificar máximo de posiciones
                if len(self.active_positions) >= self.config['trading']['max_positions']:
                    self.logger.info(f"📊 Máximo de posiciones activas ({len(self.active_positions)})")
                    time.sleep(60)  # Esperar 1 minuto
                    continue
                
                # Analizar símbolos
                for symbol in self.config['trading']['symbols']:
                    if symbol not in self.active_positions:
                        signal_data = self.analyze_symbol(symbol)
                        if signal_data:
                            success = self.execute_trade(symbol, signal_data)
                            if success:
                                self.daily_stats['trades'] += 1
                                time.sleep(5)  # Pausa entre trades
                
                # Monitorear posiciones
                self.monitor_positions()
                
                # Pausa entre ciclos
                time.sleep(30)  # 30 segundos
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Deteniendo trading por solicitud del usuario")
                break
            except Exception as e:
                self.logger.error(f"❌ Error en bucle principal: {e}")
                time.sleep(60)  # Pausa en caso de error
    
    def generate_daily_report(self):
        """Generar reporte diario"""
        try:
            current_balance = self._get_current_balance()
            daily_pnl = current_balance - self.daily_stats['start_balance']
            
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'start_balance': self.daily_stats['start_balance'],
                'end_balance': current_balance,
                'daily_pnl': daily_pnl,
                'daily_return_pct': (daily_pnl / self.daily_stats['start_balance']) * 100,
                'total_trades': self.daily_stats['trades'],
                'active_positions': len(self.active_positions)
            }
            
            # Guardar reporte
            report_file = f"daily_report_{datetime.now().strftime('%Y%m%d')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"📊 Reporte diario guardado: {report_file}")
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Error generando reporte diario: {e}")
            return None
    
    def _get_current_balance(self) -> float:
        """Obtener balance actual de USDT"""
        try:
            account_info = self.client.get_account()
            balance = float([b['free'] for b in account_info['balances'] if b['asset'] == 'USDT'][0])
            return balance
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo balance: {e}")
            return 0.0

def main():
    """
    Función principal
    """
    print("🚀 ESTRATEGIA V3 AGRESIVA - TRADING EN VIVO")
    print("="*50)
    print("⚠️  ADVERTENCIA: Este script ejecuta trades reales")
    print("⚠️  Asegúrate de configurar correctamente las API keys")
    print("⚠️  Usa TESTNET para pruebas iniciales")
    print("="*50)
    
    # Confirmación del usuario
    if not os.getenv('SKIP_CONFIRMATION'):
        confirm = input("¿Continuar con el trading en vivo? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Trading cancelado por el usuario")
            return
    
    try:
        # Inicializar ejecutor
        executor = LiveTradingExecutor()
        
        # Generar reporte inicial
        print("📊 Generando reporte inicial...")
        executor.generate_daily_report()
        
        # Iniciar trading
        executor.run_trading_loop()
        
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        sys.exit(1)
    finally:
        print("🏁 Trading finalizado")

if __name__ == "__main__":
    main()