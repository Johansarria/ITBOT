#!/usr/bin/env python3
"""
Sistema de Preparación para Activación del Mercado
Prepara el sistema para cuando el mercado se active con análisis predictivo
"""

import json
import os
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
import threading
import sqlite3
from pathlib import Path

# Importar análisis de orderbook
try:
    from orderbook_analyzer import integrate_with_market_conditions
    ORDERBOOK_ANALYSIS_AVAILABLE = True
except ImportError:
    ORDERBOOK_ANALYSIS_AVAILABLE = False
    logging.warning("Análisis de OrderBook no disponible - funcionando sin análisis de depth")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | PREPARACION | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('preparacion_mercado.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class MarketCondition:
    timestamp: datetime
    overall_score: float  # 0-100
    volatility_level: str  # 'LOW', 'MEDIUM', 'HIGH'
    volume_trend: str     # 'INCREASING', 'DECREASING', 'STABLE'
    price_momentum: str   # 'BULLISH', 'BEARISH', 'NEUTRAL'
    market_phase: str     # 'ACCUMULATION', 'MARKUP', 'DISTRIBUTION', 'MARKDOWN'
    readiness_score: float  # 0-100 (qué tan listo está para activarse)
    recommendations: List[str]

@dataclass
class TradingPreparation:
    capital_allocation: Dict[str, float]
    risk_parameters: Dict[str, float]
    entry_strategies: List[str]
    exit_strategies: List[str]
    position_sizes: Dict[str, float]
    stop_loss_levels: Dict[str, float]
    take_profit_levels: Dict[str, float]

class MarketActivationPreparation:
    def __init__(self):
        self.config = self.load_config()
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 'LINKUSDT']
        self.running = False
        
        # Parámetros de activación
        self.activation_threshold = 70.0  # Score mínimo para considerar activación
        self.min_volume_increase = 50.0   # % aumento mínimo de volumen
        self.min_volatility_for_trading = 2.0  # % volatilidad mínima
        
        # Historial para análisis de tendencias
        self.market_history = []
        self.volume_history = {}
        self.price_history = {}
        
        # Estado de preparación
        self.preparation_status = {
            'capital_ready': False,
            'strategies_loaded': False,
            'risk_parameters_set': False,
            'market_conditions_favorable': False,
            'systems_synchronized': False
        }
        
        # Base de datos para análisis histórico
        self.init_database()
        
    def load_config(self) -> Dict:
        """Cargar configuración"""
        try:
            with open('sicar_config.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando configuración: {e}")
            return {}
    
    def init_database(self):
        """Inicializar base de datos para análisis histórico"""
        try:
            self.db_path = 'market_preparation.db'
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_conditions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    overall_score REAL NOT NULL,
                    volatility_level TEXT NOT NULL,
                    volume_trend TEXT NOT NULL,
                    price_momentum TEXT NOT NULL,
                    market_phase TEXT NOT NULL,
                    readiness_score REAL NOT NULL,
                    recommendations TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS preparation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Base de datos de preparación inicializada")
            
        except Exception as e:
            logger.error(f"❌ Error inicializando base de datos: {e}")
    
    def get_comprehensive_market_data(self) -> Dict[str, Dict]:
        """Obtener datos completos del mercado"""
        market_data = {}
        
        for symbol in self.symbols:
            try:
                # Datos de ticker 24h
                ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
                ticker_response = requests.get(ticker_url, timeout=10)
                ticker_data = ticker_response.json()
                
                # Datos de velas para análisis técnico
                klines_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=168"  # 7 días
                klines_response = requests.get(klines_url, timeout=10)
                klines_data = klines_response.json()
                
                # Datos de profundidad del libro de órdenes
                depth_url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=100"
                depth_response = requests.get(depth_url, timeout=10)
                depth_data = depth_response.json()
                
                # Procesar datos de orderbook si está disponible el análisis
                orderbook_metrics = {}
                if ORDERBOOK_ANALYSIS_AVAILABLE and depth_data:
                    try:
                        orderbook_metrics = integrate_with_market_conditions(depth_data, symbol)
                        if orderbook_metrics:
                            logger.info(f"📊 OrderBook analizado para {symbol}: Spread={orderbook_metrics.get('spread_pct', 0):.3f}%")
                    except Exception as e:
                        logger.error(f"Error analizando orderbook para {symbol}: {e}")
                
                market_data[symbol] = {
                    'ticker': ticker_data,
                    'klines': klines_data,
                    'depth': depth_data,
                    'orderbook_metrics': orderbook_metrics,
                    'timestamp': datetime.now()
                }
                
            except Exception as e:
                logger.error(f"Error obteniendo datos para {symbol}: {e}")
        
        return market_data
    
    def calculate_market_volatility(self, klines_data: List) -> float:
        """Calcular volatilidad del mercado"""
        try:
            if len(klines_data) < 24:
                return 0.0
            
            # Convertir a DataFrame
            df = pd.DataFrame(klines_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convertir precios a números
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            
            # Calcular volatilidad como desviación estándar de los retornos
            df['returns'] = df['close'].pct_change()
            volatility = df['returns'].std() * 100  # En porcentaje
            
            return volatility if not np.isnan(volatility) else 0.0
            
        except Exception as e:
            logger.error(f"Error calculando volatilidad: {e}")
            return 0.0
    
    def analyze_volume_trend(self, symbol: str, ticker_data: Dict) -> str:
        """Analizar tendencia de volumen"""
        try:
            current_volume = float(ticker_data['quoteVolume'])
            
            # Actualizar historial de volumen
            if symbol not in self.volume_history:
                self.volume_history[symbol] = []
            
            self.volume_history[symbol].append(current_volume)
            
            # Mantener últimas 24 horas (asumiendo datos cada hora)
            if len(self.volume_history[symbol]) > 24:
                self.volume_history[symbol] = self.volume_history[symbol][-24:]
            
            if len(self.volume_history[symbol]) < 3:
                return 'STABLE'
            
            # Calcular tendencia
            recent_avg = np.mean(self.volume_history[symbol][-6:])  # Últimas 6 horas
            older_avg = np.mean(self.volume_history[symbol][-12:-6])  # 6 horas anteriores
            
            if older_avg > 0:
                change_percent = ((recent_avg - older_avg) / older_avg) * 100
                
                if change_percent > 20:
                    return 'INCREASING'
                elif change_percent < -20:
                    return 'DECREASING'
            
            return 'STABLE'
            
        except Exception as e:
            logger.error(f"Error analizando volumen para {symbol}: {e}")
            return 'STABLE'
    
    def determine_price_momentum(self, klines_data: List) -> str:
        """Determinar momentum de precio"""
        try:
            if len(klines_data) < 12:
                return 'NEUTRAL'
            
            # Obtener precios de cierre recientes
            recent_closes = [float(kline[4]) for kline in klines_data[-12:]]
            
            # Calcular medias móviles simples
            sma_short = np.mean(recent_closes[-6:])  # 6 períodos
            sma_long = np.mean(recent_closes[-12:])  # 12 períodos
            
            current_price = recent_closes[-1]
            
            # Determinar momentum
            if current_price > sma_short > sma_long:
                return 'BULLISH'
            elif current_price < sma_short < sma_long:
                return 'BEARISH'
            else:
                return 'NEUTRAL'
                
        except Exception as e:
            logger.error(f"Error determinando momentum: {e}")
            return 'NEUTRAL'
    
    def identify_market_phase(self, market_data: Dict) -> str:
        """Identificar fase del mercado"""
        try:
            bullish_count = 0
            bearish_count = 0
            neutral_count = 0
            
            for symbol, data in market_data.items():
                if 'klines' in data:
                    momentum = self.determine_price_momentum(data['klines'])
                    
                    if momentum == 'BULLISH':
                        bullish_count += 1
                    elif momentum == 'BEARISH':
                        bearish_count += 1
                    else:
                        neutral_count += 1
            
            total = bullish_count + bearish_count + neutral_count
            
            if total == 0:
                return 'NEUTRAL'
            
            bullish_ratio = bullish_count / total
            bearish_ratio = bearish_count / total
            
            if bullish_ratio > 0.6:
                return 'MARKUP'  # Fase alcista
            elif bearish_ratio > 0.6:
                return 'MARKDOWN'  # Fase bajista
            elif bullish_ratio > 0.4:
                return 'ACCUMULATION'  # Acumulación
            else:
                return 'DISTRIBUTION'  # Distribución
                
        except Exception as e:
            logger.error(f"Error identificando fase del mercado: {e}")
            return 'NEUTRAL'
    
    def calculate_market_readiness(self, condition: MarketCondition) -> float:
        """Calcular qué tan listo está el mercado para activarse"""
        readiness_score = 0.0
        
        # Puntuación base del mercado
        readiness_score += condition.overall_score * 0.3
        
        # Bonus por volatilidad adecuada
        if condition.volatility_level == 'MEDIUM':
            readiness_score += 20
        elif condition.volatility_level == 'HIGH':
            readiness_score += 10
        
        # Bonus por volumen creciente
        if condition.volume_trend == 'INCREASING':
            readiness_score += 25
        elif condition.volume_trend == 'STABLE':
            readiness_score += 10
        
        # Bonus por momentum claro
        if condition.price_momentum in ['BULLISH', 'BEARISH']:
            readiness_score += 15
        
        # Bonus por fases favorables
        if condition.market_phase in ['MARKUP', 'ACCUMULATION']:
            readiness_score += 20
        elif condition.market_phase == 'MARKDOWN':
            readiness_score += 10  # Oportunidades de venta en corto
        
        return min(100, max(0, readiness_score))
    
    def analyze_market_conditions(self, market_data: Dict) -> MarketCondition:
        """Analizar condiciones completas del mercado"""
        try:
            # Calcular métricas agregadas
            total_volume = 0
            total_volatility = 0
            price_changes = []
            
            for symbol, data in market_data.items():
                if 'ticker' in data:
                    ticker = data['ticker']
                    total_volume += float(ticker['quoteVolume'])
                    price_changes.append(float(ticker['priceChangePercent']))
                
                if 'klines' in data:
                    volatility = self.calculate_market_volatility(data['klines'])
                    total_volatility += volatility
            
            # Calcular puntuación general del mercado
            avg_price_change = np.mean(price_changes) if price_changes else 0
            avg_volatility = total_volatility / len(market_data) if market_data else 0
            
            # Puntuación base
            overall_score = 50  # Neutral
            
            # Ajustar por cambio de precio promedio
            if abs(avg_price_change) > 5:
                overall_score += 20
            elif abs(avg_price_change) > 2:
                overall_score += 10
            
            # Ajustar por volumen total
            if total_volume > 5000000000:  # > 5B USDT
                overall_score += 15
            elif total_volume > 2000000000:  # > 2B USDT
                overall_score += 10
            
            # Determinar nivel de volatilidad
            if avg_volatility > 8:
                volatility_level = 'HIGH'
            elif avg_volatility > 3:
                volatility_level = 'MEDIUM'
            else:
                volatility_level = 'LOW'
            
            # Analizar tendencias
            volume_trend = self.analyze_volume_trend('BTCUSDT', market_data.get('BTCUSDT', {}).get('ticker', {}))
            price_momentum = self.determine_price_momentum(market_data.get('BTCUSDT', {}).get('klines', []))
            market_phase = self.identify_market_phase(market_data)
            
            # Crear condición del mercado
            condition = MarketCondition(
                timestamp=datetime.now(),
                overall_score=min(100, max(0, overall_score)),
                volatility_level=volatility_level,
                volume_trend=volume_trend,
                price_momentum=price_momentum,
                market_phase=market_phase,
                readiness_score=0,  # Se calculará después
                recommendations=[]
            )
            
            # Calcular puntuación de preparación
            condition.readiness_score = self.calculate_market_readiness(condition)
            
            # Generar recomendaciones
            condition.recommendations = self.generate_recommendations(condition)
            
            return condition
            
        except Exception as e:
            logger.error(f"Error analizando condiciones del mercado: {e}")
            return MarketCondition(
                timestamp=datetime.now(),
                overall_score=0,
                volatility_level='LOW',
                volume_trend='STABLE',
                price_momentum='NEUTRAL',
                market_phase='NEUTRAL',
                readiness_score=0,
                recommendations=['Error en análisis']
            )
    
    def generate_recommendations(self, condition: MarketCondition) -> List[str]:
        """Generar recomendaciones basadas en las condiciones"""
        recommendations = []
        
        # Recomendaciones por puntuación de preparación
        if condition.readiness_score >= 80:
            recommendations.append("🟢 MERCADO LISTO: Condiciones óptimas para activación")
            recommendations.append("🚀 Activar trading automático con parámetros conservadores")
        elif condition.readiness_score >= 60:
            recommendations.append("🟡 MERCADO CASI LISTO: Monitorear de cerca")
            recommendations.append("⚠️ Preparar estrategias de entrada")
        else:
            recommendations.append("🔴 MERCADO NO LISTO: Mantener en modo observación")
            recommendations.append("📊 Continuar análisis y esperar mejores condiciones")
        
        # Recomendaciones específicas por volatilidad
        if condition.volatility_level == 'HIGH':
            recommendations.append("⚡ Alta volatilidad: Reducir tamaños de posición")
            recommendations.append("🛡️ Usar stops más ajustados")
        elif condition.volatility_level == 'LOW':
            recommendations.append("😴 Baja volatilidad: Considerar estrategias de rango")
        
        # Recomendaciones por volumen
        if condition.volume_trend == 'INCREASING':
            recommendations.append("📈 Volumen creciente: Confirma movimientos de precio")
        elif condition.volume_trend == 'DECREASING':
            recommendations.append("📉 Volumen decreciente: Cuidado con falsos breakouts")
        
        # Recomendaciones por momentum
        if condition.price_momentum == 'BULLISH':
            recommendations.append("🐂 Momentum alcista: Favorecer posiciones largas")
        elif condition.price_momentum == 'BEARISH':
            recommendations.append("🐻 Momentum bajista: Considerar posiciones cortas")
        
        return recommendations
    
    def prepare_trading_parameters(self, condition: MarketCondition) -> TradingPreparation:
        """Preparar parámetros de trading basados en condiciones"""
        try:
            # Asignación de capital basada en preparación
            base_allocation = 0.1  # 10% base
            
            if condition.readiness_score >= 80:
                allocation_multiplier = 1.0
            elif condition.readiness_score >= 60:
                allocation_multiplier = 0.7
            else:
                allocation_multiplier = 0.3
            
            # Distribución por símbolo
            capital_allocation = {}
            for symbol in self.symbols:
                if symbol == 'BTCUSDT':
                    capital_allocation[symbol] = base_allocation * allocation_multiplier * 0.4  # 40% a BTC
                elif symbol == 'ETHUSDT':
                    capital_allocation[symbol] = base_allocation * allocation_multiplier * 0.3  # 30% a ETH
                else:
                    capital_allocation[symbol] = base_allocation * allocation_multiplier * 0.3 / (len(self.symbols) - 2)
            
            # Parámetros de riesgo
            risk_parameters = {
                'max_position_size': 0.05 if condition.volatility_level == 'HIGH' else 0.1,
                'stop_loss_percent': 3.0 if condition.volatility_level == 'HIGH' else 2.0,
                'take_profit_percent': 6.0 if condition.volatility_level == 'HIGH' else 4.0,
                'max_daily_loss': 0.02,  # 2% del capital
                'max_open_positions': 3 if condition.volatility_level == 'HIGH' else 5
            }
            
            # Estrategias de entrada
            entry_strategies = []
            if condition.price_momentum == 'BULLISH':
                entry_strategies.extend(['breakout_long', 'pullback_long'])
            elif condition.price_momentum == 'BEARISH':
                entry_strategies.extend(['breakdown_short', 'bounce_short'])
            else:
                entry_strategies.extend(['range_trading', 'mean_reversion'])
            
            # Estrategias de salida
            exit_strategies = ['trailing_stop', 'profit_target', 'time_based']
            
            return TradingPreparation(
                capital_allocation=capital_allocation,
                risk_parameters=risk_parameters,
                entry_strategies=entry_strategies,
                exit_strategies=exit_strategies,
                position_sizes={symbol: capital_allocation[symbol] for symbol in capital_allocation},
                stop_loss_levels={symbol: risk_parameters['stop_loss_percent'] for symbol in self.symbols},
                take_profit_levels={symbol: risk_parameters['take_profit_percent'] for symbol in self.symbols}
            )
            
        except Exception as e:
            logger.error(f"Error preparando parámetros de trading: {e}")
            return TradingPreparation({}, {}, [], [], {}, {}, {})
    
    def save_market_condition(self, condition: MarketCondition):
        """Guardar condición del mercado en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO market_conditions 
                (timestamp, overall_score, volatility_level, volume_trend, price_momentum, 
                 market_phase, readiness_score, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                condition.timestamp.isoformat(),
                condition.overall_score,
                condition.volatility_level,
                condition.volume_trend,
                condition.price_momentum,
                condition.market_phase,
                condition.readiness_score,
                json.dumps(condition.recommendations)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error guardando condición del mercado: {e}")
    
    def display_market_analysis(self, condition: MarketCondition, preparation: TradingPreparation):
        """Mostrar análisis completo del mercado"""
        print("\n" + "="*100)
        print("🎯 ANÁLISIS DE PREPARACIÓN PARA ACTIVACIÓN DEL MERCADO")
        print("="*100)
        
        # Estado general
        readiness_emoji = "🟢" if condition.readiness_score >= 70 else "🟡" if condition.readiness_score >= 50 else "🔴"
        print(f"\n📊 ESTADO GENERAL DEL MERCADO")
        print(f"   {readiness_emoji} Puntuación de Preparación: {condition.readiness_score:.1f}/100")
        print(f"   📈 Puntuación General: {condition.overall_score:.1f}/100")
        print(f"   ⚡ Volatilidad: {condition.volatility_level}")
        print(f"   📊 Tendencia de Volumen: {condition.volume_trend}")
        print(f"   🎯 Momentum de Precio: {condition.price_momentum}")
        print(f"   🔄 Fase del Mercado: {condition.market_phase}")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES:")
        for i, rec in enumerate(condition.recommendations, 1):
            print(f"   {i}. {rec}")
        
        # Parámetros de trading preparados
        print(f"\n⚙️ PARÁMETROS DE TRADING PREPARADOS:")
        print(f"   💰 Asignación de Capital:")
        for symbol, allocation in preparation.capital_allocation.items():
            print(f"      {symbol}: {allocation*100:.1f}%")
        
        print(f"   🛡️ Gestión de Riesgo:")
        for param, value in preparation.risk_parameters.items():
            if 'percent' in param:
                print(f"      {param}: {value:.1f}%")
            else:
                print(f"      {param}: {value}")
        
        print(f"   📈 Estrategias de Entrada: {', '.join(preparation.entry_strategies)}")
        print(f"   📉 Estrategias de Salida: {', '.join(preparation.exit_strategies)}")
        
        # Estado de preparación del sistema
        print(f"\n🔧 ESTADO DE PREPARACIÓN DEL SISTEMA:")
        for component, status in self.preparation_status.items():
            emoji = "✅" if status else "❌"
            print(f"   {emoji} {component.replace('_', ' ').title()}")
        
        print("="*100)
    
    def check_activation_conditions(self, condition: MarketCondition) -> bool:
        """Verificar si se cumplen las condiciones para activación"""
        activation_criteria = [
            condition.readiness_score >= self.activation_threshold,
            condition.volatility_level in ['MEDIUM', 'HIGH'],
            condition.volume_trend in ['INCREASING', 'STABLE'],
            condition.overall_score >= 60
        ]
        
        return all(activation_criteria)
    
    def update_preparation_status(self, condition: MarketCondition):
        """Actualizar estado de preparación del sistema"""
        # Verificar capital
        try:
            with open('data/paper_trading_session.json', 'r') as f:
                session = json.load(f)
            self.preparation_status['capital_ready'] = session.get('current_capital', 0) >= 200
        except:
            self.preparation_status['capital_ready'] = False
        
        # Verificar estrategias
        self.preparation_status['strategies_loaded'] = len(self.symbols) > 0
        
        # Verificar parámetros de riesgo
        self.preparation_status['risk_parameters_set'] = True  # Siempre calculamos parámetros
        
        # Verificar condiciones del mercado
        self.preparation_status['market_conditions_favorable'] = condition.readiness_score >= 50
        
        # Verificar sincronización de sistemas
        self.preparation_status['systems_synchronized'] = all([
            os.path.exists('sicar_config.json'),
            os.path.exists('data/paper_trading_session.json')
        ])
    
    def run_continuous_preparation(self):
        """Ejecutar preparación continua"""
        logger.info("🎯 Iniciando sistema de preparación para activación del mercado...")
        self.running = True
        
        while self.running:
            try:
                print(f"\n🔍 {datetime.now().strftime('%H:%M:%S')} - Analizando preparación del mercado...")
                
                # Obtener datos del mercado
                market_data = self.get_comprehensive_market_data()
                
                if market_data:
                    # Analizar condiciones
                    condition = self.analyze_market_conditions(market_data)
                    
                    # Preparar parámetros de trading
                    preparation = self.prepare_trading_parameters(condition)
                    
                    # Actualizar estado de preparación
                    self.update_preparation_status(condition)
                    
                    # Guardar análisis
                    self.save_market_condition(condition)
                    
                    # Mostrar análisis
                    self.display_market_analysis(condition, preparation)
                    
                    # Verificar condiciones de activación
                    if self.check_activation_conditions(condition):
                        print("\n🚨 ¡CONDICIONES DE ACTIVACIÓN CUMPLIDAS!")
                        print("🚀 El mercado está listo para trading automático")
                        
                        # Aquí se podría activar automáticamente el trading
                        # self.activate_trading(preparation)
                    
                    # Actualizar historial
                    self.market_history.append(condition)
                    if len(self.market_history) > 100:
                        self.market_history = self.market_history[-100:]
                
                # Esperar antes del siguiente análisis
                time.sleep(300)  # Análisis cada 5 minutos
                
            except KeyboardInterrupt:
                logger.info("🛑 Deteniendo sistema de preparación...")
                break
            except Exception as e:
                logger.error(f"❌ Error en preparación: {e}")
                time.sleep(60)
        
        self.running = False

def main():
    """Función principal"""
    print("🎯 SISTEMA DE PREPARACIÓN PARA ACTIVACIÓN DEL MERCADO")
    print("="*60)
    
    preparation_system = MarketActivationPreparation()
    
    try:
        preparation_system.run_continuous_preparation()
    except KeyboardInterrupt:
        print("\n🛑 Sistema detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
    
    return 0

if __name__ == "__main__":
    exit(main())