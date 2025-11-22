#!/usr/bin/env python3
"""
Backtester Multi-Asset para SICAR
=================================

Backtester avanzado que maneja múltiples clases de activos:
- Criptomonedas (24/7)
- Forex (24/5 con sesiones)
- Índices (horarios regionales)
- Commodities (24/5 mayoría)

Características:
- Gestión de horarios de mercado por activo
- Parámetros de riesgo específicos por clase
- Análisis de correlaciones en tiempo real
- Rebalanceo automático de portfolio
- Métricas especializadas por activo

Año: 2025
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
import json
import warnings
warnings.filterwarnings('ignore')

from multi_asset_data_system import MultiAssetDataSystem

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiAssetBacktester:
    """
    Backtester especializado para múltiples clases de activos
    """
    
    def __init__(self, initial_capital: float = 10000, config_file: str = None):
        """
        Inicializar backtester multi-asset
        
        Args:
            initial_capital: Capital inicial en USD
            config_file: Archivo de configuración multi-asset
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        
        # Inicializar sistema de datos
        self.data_system = MultiAssetDataSystem(config_file)
        self.config = self.data_system.config
        
        # Portfolio por clase de activo
        self.portfolio = {
            'cryptocurrencies': {},
            'forex': {},
            'indices': {},
            'commodities': {}
        }
        
        # Posiciones activas
        self.positions = {}
        
        # Historial de trades
        self.trade_history = []
        
        # Métricas por clase de activo
        self.asset_metrics = {
            'cryptocurrencies': {'trades': 0, 'wins': 0, 'total_return': 0.0},
            'forex': {'trades': 0, 'wins': 0, 'total_return': 0.0},
            'indices': {'trades': 0, 'wins': 0, 'total_return': 0.0},
            'commodities': {'trades': 0, 'wins': 0, 'total_return': 0.0}
        }
        
        # Parámetros de riesgo por clase de activo
        self.risk_params = self.config.get('risk_management', {}).get('parameters', {})
        
        # Cache de datos para optimización
        self.data_cache = {}
        
        logger.info("🚀 Backtester Multi-Asset inicializado")
        logger.info(f"💰 Capital inicial: ${initial_capital:,.2f}")
        
    def load_data_for_symbol(self, symbol: str, interval: str = '4h', 
                           limit: int = 1000) -> Optional[pd.DataFrame]:
        """
        Cargar datos para un símbolo específico
        
        Args:
            symbol: Símbolo del activo
            interval: Intervalo de tiempo
            limit: Número de velas
            
        Returns:
            DataFrame con datos OHLCV
        """
        cache_key = f"{symbol}_{interval}_{limit}"
        
        if cache_key in self.data_cache:
            logger.info(f"💾 Datos de {symbol} obtenidos del cache")
            return self.data_cache[cache_key]
        
        logger.info(f"📊 Cargando datos para {symbol}...")
        data = self.data_system.get_multi_asset_data(symbol, interval, limit)
        
        if data is not None:
            # Asegurar que el DataFrame tenga las columnas necesarias
            if 'timestamp' not in data.columns and data.index.name != 'timestamp':
                data.reset_index(inplace=True)
                if 'timestamp' not in data.columns:
                    data['timestamp'] = pd.date_range(
                        start=datetime.now() - timedelta(hours=len(data)*4),
                        periods=len(data),
                        freq='4H'
                    )
            
            # Normalizar nombres de columnas
            column_mapping = {
                'Open': 'open', 'High': 'high', 'Low': 'low', 
                'Close': 'close', 'Volume': 'volume'
            }
            data.rename(columns=column_mapping, inplace=True)
            
            # Asegurar que tenemos las columnas básicas
            required_columns = ['open', 'high', 'low', 'close']
            if all(col in data.columns for col in required_columns):
                self.data_cache[cache_key] = data
                logger.info(f"✅ Datos cargados para {symbol}: {len(data)} velas")
                return data
            else:
                logger.error(f"❌ Datos de {symbol} no tienen columnas requeridas: {data.columns.tolist()}")
                return None
        else:
            logger.error(f"❌ No se pudieron cargar datos para {symbol}")
            return None
            
    def calculate_position_size(self, symbol: str, price: float, 
                              volatility: float = None) -> float:
        """
        Calcular tamaño de posición basado en la clase de activo
        
        Args:
            symbol: Símbolo del activo
            price: Precio actual
            volatility: Volatilidad del activo (opcional)
            
        Returns:
            Tamaño de posición en USD
        """
        asset_class = self.data_system.get_asset_class(symbol)
        risk_config = self.risk_params.get(asset_class, {})
        
        # Parámetros por defecto si no están configurados
        max_position_size = risk_config.get('max_position_size', 0.02)  # 2%
        volatility_multiplier = risk_config.get('volatility_multiplier', 1.0)
        
        # Tamaño base de posición
        base_position_size = self.current_capital * max_position_size
        
        # Ajustar por volatilidad si está disponible
        if volatility is not None:
            # Reducir tamaño si la volatilidad es alta
            volatility_adjustment = 1.0 / (1.0 + volatility * volatility_multiplier)
            base_position_size *= volatility_adjustment
        
        # Asegurar que no excedemos límites
        max_position_value = min(base_position_size, self.current_capital * 0.1)  # Máximo 10%
        
        return max_position_value
        
    def is_market_open_for_trading(self, symbol: str, timestamp: datetime) -> bool:
        """
        Verificar si el mercado está abierto para trading en un timestamp específico
        
        Args:
            symbol: Símbolo del activo
            timestamp: Timestamp a verificar
            
        Returns:
            True si el mercado está abierto
        """
        asset_class = self.data_system.get_asset_class(symbol)
        
        # Criptomonedas siempre abiertas
        if asset_class == 'cryptocurrencies':
            return True
        
        # Verificar día de la semana (0=Lunes, 6=Domingo)
        weekday = timestamp.weekday()
        if weekday >= 5:  # Sábado o Domingo
            return False
        
        # Verificar horarios específicos por clase de activo
        market_config = self.data_system.market_hours.get(asset_class, {})
        
        if asset_class == 'forex':
            # Forex: verificar si alguna sesión está abierta
            current_time = timestamp.strftime('%H:%M')
            for session, hours in market_config.get('sessions', {}).items():
                start = hours['start']
                end = hours['end']
                
                if start > end:  # Sesión que cruza medianoche
                    if current_time >= start or current_time <= end:
                        return True
                else:
                    if start <= current_time <= end:
                        return True
            return False
        
        elif asset_class in ['indices', 'commodities']:
            # Horarios generales (simplificado)
            return 8 <= timestamp.hour <= 20  # 8 AM - 8 PM UTC
        
        return True  # Default: abierto
        
    def calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calcular indicadores técnicos para el backtesting
        
        Args:
            data: DataFrame con datos OHLCV
            
        Returns:
            DataFrame con indicadores añadidos
        """
        df = data.copy()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Medias móviles
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Volatilidad
        df['volatility'] = df['close'].pct_change().rolling(window=20).std() * np.sqrt(252)
        
        return df
        
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        Generar señales de trading específicas por clase de activo
        
        Args:
            data: DataFrame con datos e indicadores
            symbol: Símbolo del activo
            
        Returns:
            DataFrame con señales añadidas
        """
        df = data.copy()
        asset_class = self.data_system.get_asset_class(symbol)
        
        # Inicializar señales
        df['signal'] = 0
        df['signal_strength'] = 0.0
        
        # Estrategias específicas por clase de activo
        if asset_class == 'cryptocurrencies':
            # Estrategia más agresiva para crypto
            buy_condition = (
                (df['rsi'] < 30) &  # Sobreventa
                (df['close'] > df['sma_20']) &  # Tendencia alcista
                (df['macd'] > df['macd_signal'])  # MACD positivo
            )
            sell_condition = (
                (df['rsi'] > 70) |  # Sobrecompra
                (df['close'] < df['sma_20'])  # Ruptura de tendencia
            )
            
        elif asset_class == 'forex':
            # Estrategia más conservadora para forex
            buy_condition = (
                (df['rsi'] < 40) &
                (df['close'] > df['sma_50']) &
                (df['macd_histogram'] > 0)
            )
            sell_condition = (
                (df['rsi'] > 60) |
                (df['close'] < df['sma_50'])
            )
            
        elif asset_class in ['indices', 'commodities']:
            # Estrategia balanceada para índices y commodities
            buy_condition = (
                (df['rsi'] < 35) &
                (df['close'] > df['bb_lower']) &
                (df['close'] > df['sma_20'])
            )
            sell_condition = (
                (df['rsi'] > 65) |
                (df['close'] < df['bb_lower'])
            )
        else:
            # Estrategia por defecto
            buy_condition = (df['rsi'] < 30) & (df['close'] > df['sma_20'])
            sell_condition = (df['rsi'] > 70) | (df['close'] < df['sma_20'])
        
        # Aplicar señales
        df.loc[buy_condition, 'signal'] = 1
        df.loc[sell_condition, 'signal'] = -1
        
        # Calcular fuerza de la señal
        df.loc[df['signal'] == 1, 'signal_strength'] = (
            (50 - df['rsi']) / 50 * 0.5 +  # RSI component
            (df['macd_histogram'] / df['macd_histogram'].abs().max()) * 0.3 +  # MACD component
            0.2  # Base strength
        ).clip(0, 1)
        
        df.loc[df['signal'] == -1, 'signal_strength'] = (
            (df['rsi'] - 50) / 50 * 0.5 +
            (-df['macd_histogram'] / df['macd_histogram'].abs().max()) * 0.3 +
            0.2
        ).clip(0, 1)
        
        return df
        
    def execute_trade(self, symbol: str, signal: int, price: float, 
                     timestamp: datetime, signal_strength: float = 1.0) -> bool:
        """
        Ejecutar una operación de trading
        
        Args:
            symbol: Símbolo del activo
            signal: 1 para compra, -1 para venta
            price: Precio de ejecución
            timestamp: Timestamp de la operación
            signal_strength: Fuerza de la señal (0-1)
            
        Returns:
            True si la operación se ejecutó exitosamente
        """
        asset_class = self.data_system.get_asset_class(symbol)
        
        # Verificar si el mercado está abierto
        if not self.is_market_open_for_trading(symbol, timestamp):
            return False
        
        # Verificar si ya tenemos una posición
        if symbol in self.positions:
            # Cerrar posición existente si la señal es opuesta
            existing_position = self.positions[symbol]
            if (existing_position['side'] == 'long' and signal == -1) or \
               (existing_position['side'] == 'short' and signal == 1):
                self._close_position(symbol, price, timestamp)
            else:
                return False  # No abrir posición en la misma dirección
        
        # Calcular tamaño de posición
        volatility = self._get_recent_volatility(symbol)
        position_size = self.calculate_position_size(symbol, price, volatility)
        
        # Ajustar por fuerza de la señal
        position_size *= signal_strength
        
        # Verificar capital disponible
        if position_size > self.current_capital * 0.95:  # Dejar 5% de margen
            return False
        
        # Ejecutar la operación
        side = 'long' if signal == 1 else 'short'
        quantity = position_size / price
        
        # Registrar posición
        self.positions[symbol] = {
            'side': side,
            'quantity': quantity,
            'entry_price': price,
            'entry_time': timestamp,
            'position_size': position_size,
            'asset_class': asset_class,
            'signal_strength': signal_strength
        }
        
        # Actualizar capital
        self.current_capital -= position_size
        
        # Registrar trade
        trade = {
            'symbol': symbol,
            'asset_class': asset_class,
            'side': side,
            'quantity': quantity,
            'entry_price': price,
            'entry_time': timestamp,
            'position_size': position_size,
            'signal_strength': signal_strength,
            'status': 'open'
        }
        
        self.trade_history.append(trade)
        
        logger.info(f"📈 {side.upper()} {symbol}: {quantity:.6f} @ ${price:.4f} "
                   f"(${position_size:.2f}, strength: {signal_strength:.2f})")
        
        return True
        
    def _close_position(self, symbol: str, price: float, timestamp: datetime) -> float:
        """
        Cerrar una posición existente
        
        Args:
            symbol: Símbolo del activo
            price: Precio de cierre
            timestamp: Timestamp de cierre
            
        Returns:
            PnL de la operación
        """
        if symbol not in self.positions:
            return 0.0
        
        position = self.positions[symbol]
        
        # Calcular PnL
        if position['side'] == 'long':
            pnl = (price - position['entry_price']) * position['quantity']
        else:  # short
            pnl = (position['entry_price'] - price) * position['quantity']
        
        # Actualizar capital
        self.current_capital += position['position_size'] + pnl
        
        # Actualizar métricas por clase de activo
        asset_class = position['asset_class']
        self.asset_metrics[asset_class]['trades'] += 1
        self.asset_metrics[asset_class]['total_return'] += pnl
        
        if pnl > 0:
            self.asset_metrics[asset_class]['wins'] += 1
        
        # Actualizar historial de trades
        for trade in reversed(self.trade_history):
            if (trade['symbol'] == symbol and trade['status'] == 'open'):
                trade.update({
                    'exit_price': price,
                    'exit_time': timestamp,
                    'pnl': pnl,
                    'return_pct': (pnl / position['position_size']) * 100,
                    'status': 'closed'
                })
                break
        
        # Remover posición
        del self.positions[symbol]
        
        logger.info(f"📉 CLOSE {symbol}: PnL ${pnl:.2f} "
                   f"({(pnl/position['position_size']*100):+.2f}%)")
        
        return pnl
        
    def _get_recent_volatility(self, symbol: str) -> float:
        """Obtener volatilidad reciente de un símbolo"""
        if symbol in self.data_cache:
            data = self.data_cache[f"{symbol}_4h_1000"]
            if data is not None and 'volatility' in data.columns:
                return data['volatility'].iloc[-1] if not pd.isna(data['volatility'].iloc[-1]) else 0.2
        return 0.2  # Volatilidad por defecto
        
    def run_backtest(self, symbols: List[str], start_date: str = None, 
                    end_date: str = None) -> Dict:
        """
        Ejecutar backtest multi-asset
        
        Args:
            symbols: Lista de símbolos a testear
            start_date: Fecha de inicio (opcional)
            end_date: Fecha de fin (opcional)
            
        Returns:
            Diccionario con resultados del backtest
        """
        logger.info(f"🚀 Iniciando backtest multi-asset con {len(symbols)} símbolos")
        
        # Cargar datos para todos los símbolos
        symbol_data = {}
        for symbol in symbols:
            data = self.load_data_for_symbol(symbol)
            if data is not None:
                # Calcular indicadores
                data = self.calculate_technical_indicators(data)
                # Generar señales
                data = self.generate_signals(data, symbol)
                symbol_data[symbol] = data
            else:
                logger.warning(f"⚠️ No se pudieron cargar datos para {symbol}")
        
        if not symbol_data:
            logger.error("❌ No se pudieron cargar datos para ningún símbolo")
            return {}
        
        # Obtener rango de fechas común
        min_length = min(len(data) for data in symbol_data.values())
        logger.info(f"📊 Procesando {min_length} velas por símbolo")
        
        # Ejecutar backtest
        for i in range(50, min_length):  # Empezar después de calcular indicadores
            current_time = datetime.now() - timedelta(hours=(min_length-i)*4)
            
            # Procesar señales para cada símbolo
            for symbol, data in symbol_data.items():
                if i < len(data):
                    row = data.iloc[i]
                    
                    if row['signal'] != 0 and not pd.isna(row['signal_strength']):
                        self.execute_trade(
                            symbol=symbol,
                            signal=int(row['signal']),
                            price=row['close'],
                            timestamp=current_time,
                            signal_strength=row['signal_strength']
                        )
        
        # Cerrar todas las posiciones abiertas
        final_time = datetime.now()
        for symbol in list(self.positions.keys()):
            if symbol in symbol_data:
                final_price = symbol_data[symbol]['close'].iloc[-1]
                self._close_position(symbol, final_price, final_time)
        
        # Calcular resultados
        results = self._calculate_results()
        
        logger.info("✅ Backtest completado")
        return results
        
    def _calculate_results(self) -> Dict:
        """Calcular resultados del backtest"""
        total_return = self.current_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        # Estadísticas generales
        total_trades = len([t for t in self.trade_history if t['status'] == 'closed'])
        winning_trades = len([t for t in self.trade_history 
                            if t['status'] == 'closed' and t['pnl'] > 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Estadísticas por clase de activo
        asset_stats = {}
        for asset_class, metrics in self.asset_metrics.items():
            if metrics['trades'] > 0:
                asset_stats[asset_class] = {
                    'trades': metrics['trades'],
                    'win_rate': (metrics['wins'] / metrics['trades']) * 100,
                    'total_return': metrics['total_return'],
                    'avg_return_per_trade': metrics['total_return'] / metrics['trades']
                }
        
        results = {
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'asset_class_stats': asset_stats,
            'trade_history': self.trade_history
        }
        
        return results
        
    def print_results(self, results: Dict):
        """Imprimir resultados del backtest"""
        print("\n" + "="*60)
        print("📊 RESULTADOS BACKTEST MULTI-ASSET")
        print("="*60)
        
        print(f"\n💰 RENDIMIENTO GENERAL:")
        print(f"   • Capital inicial: ${results['initial_capital']:,.2f}")
        print(f"   • Capital final: ${results['final_capital']:,.2f}")
        print(f"   • Retorno total: ${results['total_return']:,.2f}")
        print(f"   • Retorno %: {results['total_return_pct']:+.2f}%")
        
        print(f"\n📈 ESTADÍSTICAS DE TRADING:")
        print(f"   • Total trades: {results['total_trades']}")
        print(f"   • Trades ganadores: {results['winning_trades']}")
        print(f"   • Win rate: {results['win_rate']:.1f}%")
        
        print(f"\n🏷️  RENDIMIENTO POR CLASE DE ACTIVO:")
        for asset_class, stats in results['asset_class_stats'].items():
            print(f"   • {asset_class.title()}:")
            print(f"     - Trades: {stats['trades']}")
            print(f"     - Win rate: {stats['win_rate']:.1f}%")
            print(f"     - Retorno total: ${stats['total_return']:,.2f}")
            print(f"     - Retorno promedio/trade: ${stats['avg_return_per_trade']:,.2f}")
        
        print("\n" + "="*60)

def main():
    """Función principal de demostración"""
    print("🚀 Iniciando Backtester Multi-Asset SICAR...")
    
    try:
        # Inicializar backtester
        backtester = MultiAssetBacktester(initial_capital=10000)
        
        # Símbolos para testear (solo validados)
        test_symbols = backtester.data_system.get_validated_symbols('cryptocurrencies')
        
        if not test_symbols:
            print("⚠️ No hay símbolos validados disponibles")
            return
        
        # Limitar a los primeros 3 símbolos para la demo
        test_symbols = test_symbols[:3]
        print(f"🧪 Testeando símbolos: {test_symbols}")
        
        # Ejecutar backtest
        results = backtester.run_backtest(test_symbols)
        
        if results:
            # Mostrar resultados
            backtester.print_results(results)
        else:
            print("❌ No se pudieron obtener resultados del backtest")
        
        return backtester
        
    except Exception as e:
        logger.error(f"❌ Error en backtest multi-asset: {e}")
        return None

if __name__ == "__main__":
    backtester = main()