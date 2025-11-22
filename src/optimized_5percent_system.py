#!/usr/bin/env python3
"""
SISTEMA OPTIMIZADO PARA 5% MENSUAL SIN APALANCAMIENTO
====================================================

Sistema mejorado que utiliza estrategias más conservadoras y efectivas:
1. Filtros de calidad más estrictos
2. Gestión de riesgo mejorada
3. Selección de mejores oportunidades
4. Timing de entrada/salida optimizado
5. Diversificación inteligente
6. Compounding conservador
"""

import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('optimized_5percent_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Optimized5PercentSystem:
    """Sistema optimizado para lograr 5% mensual de forma conservadora"""
    
    def __init__(self):
        self.name = "OPTIMIZED 5% MONTHLY SYSTEM"
        self.target_monthly_return = 0.05  # 5% mensual
        self.initial_capital = 10000
        
        # Configuración conservadora
        self.max_daily_trades = 3  # Máximo 3 trades por día
        self.min_win_rate = 0.65   # Mínimo 65% win rate
        self.max_risk_per_trade = 0.01  # Máximo 1% riesgo por trade
        self.min_reward_risk_ratio = 3.0  # Mínimo 3:1 reward/risk
        
        # Filtros de calidad estrictos
        self.quality_filters = {
            'min_volume_spike': 2.0,      # Mínimo 2x volumen promedio
            'min_price_movement': 0.5,     # Mínimo 0.5% movimiento
            'max_spread': 0.1,             # Máximo 0.1% spread
            'min_liquidity': 1000000,      # Mínimo $1M liquidez
            'trend_confirmation': True,     # Requiere confirmación de tendencia
            'momentum_alignment': True      # Requiere alineación de momentum
        }
        
        # Símbolos de alta calidad (más estables)
        self.premium_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT'  # Solo los más líquidos y estables
        ]
        
        # Métricas de rendimiento
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'daily_returns': []
        }
        
        logger.info(f"🎯 {self.name} INICIALIZADO")
        logger.info(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        logger.info(f"🎯 Objetivo: {self.target_monthly_return*100}% mensual")
        logger.info(f"🛡️ Máximo riesgo por trade: {self.max_risk_per_trade*100}%")
        logger.info(f"📊 Win rate mínimo: {self.min_win_rate*100}%")

    def generate_high_quality_data(self, symbol: str, days: int = 90) -> pd.DataFrame:
        """Genera datos de alta calidad para backtesting"""
        try:
            # Parámetros optimizados para símbolos premium
            premium_params = {
                'BTCUSDT': {
                    'base_price': 45000,
                    'daily_volatility': 0.025,  # 2.5% volatilidad diaria
                    'trend_strength': 0.0001,
                    'mean_reversion': 0.1
                },
                'ETHUSDT': {
                    'base_price': 2500,
                    'daily_volatility': 0.03,   # 3% volatilidad diaria
                    'trend_strength': 0.0002,
                    'mean_reversion': 0.12
                },
                'BNBUSDT': {
                    'base_price': 300,
                    'daily_volatility': 0.035,  # 3.5% volatilidad diaria
                    'trend_strength': 0.0001,
                    'mean_reversion': 0.15
                }
            }
            
            params = premium_params.get(symbol, premium_params['BTCUSDT'])
            
            # Generar datos por hora para mayor precisión
            hours = days * 24
            np.random.seed(hash(symbol) % 2**32)
            
            # Generar precios con patrones realistas
            prices = [params['base_price']]
            volatility = params['daily_volatility'] / 24**0.5  # Ajustar para horas
            
            for i in range(hours):
                # Componente de tendencia
                trend = params['trend_strength']
                
                # Componente de mean reversion
                current_price = prices[-1]
                distance_from_base = (current_price - params['base_price']) / params['base_price']
                mean_reversion = -distance_from_base * params['mean_reversion']
                
                # Componente aleatoria con clustering de volatilidad
                if i > 0:
                    prev_return = (prices[-1] - prices[-2]) / prices[-2]
                    vol_clustering = 1 + 0.5 * abs(prev_return) / volatility
                else:
                    vol_clustering = 1
                
                random_component = np.random.normal(0, volatility * vol_clustering)
                
                # Precio siguiente
                total_return = trend + mean_reversion + random_component
                new_price = current_price * (1 + total_return)
                prices.append(max(new_price, params['base_price'] * 0.5))  # Floor price
            
            # Crear timestamps
            start_date = datetime.now() - timedelta(days=days)
            timestamps = pd.date_range(start=start_date, periods=hours, freq='1H')
            
            # Crear OHLCV data
            data = []
            for i in range(hours):
                if i == 0:
                    open_price = prices[i]
                else:
                    open_price = prices[i-1]
                
                close_price = prices[i]
                
                # High/Low con volatilidad intraday
                intraday_vol = abs(np.random.normal(0, volatility * 0.5))
                high_price = max(open_price, close_price) * (1 + intraday_vol)
                low_price = min(open_price, close_price) * (1 - intraday_vol)
                
                # Volumen correlacionado con volatilidad
                price_change = abs(close_price - open_price) / open_price
                base_volume = np.random.lognormal(16, 0.5)  # Mayor volumen base
                volume = base_volume * (1 + price_change * 10)
                
                data.append({
                    'timestamp': timestamps[i],
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error generando datos para {symbol}: {e}")
            return pd.DataFrame()

    def calculate_advanced_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos avanzados y filtros de calidad"""
        try:
            df = data.copy()
            
            # Indicadores de tendencia
            df['ema_8'] = df['close'].ewm(span=8).mean()
            df['ema_21'] = df['close'].ewm(span=21).mean()
            df['ema_55'] = df['close'].ewm(span=55).mean()
            
            # Indicadores de momentum
            df['rsi'] = self.calculate_rsi(df['close'], 14)
            df['stoch_k'], df['stoch_d'] = self.calculate_stochastic(df)
            
            # MACD optimizado
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Indicadores de volumen
            df['volume_sma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            df['vwap'] = (df['close'] * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum()
            
            # Filtros de calidad
            df['price_change'] = df['close'].pct_change()
            df['volatility'] = df['price_change'].rolling(20).std()
            df['atr'] = self.calculate_atr(df)
            
            # Señales de calidad
            df['trend_quality'] = self.calculate_trend_quality(df)
            df['momentum_quality'] = self.calculate_momentum_quality(df)
            df['volume_quality'] = self.calculate_volume_quality(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores avanzados: {e}")
            return data

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI optimizado"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_stochastic(self, data: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calcula Stochastic Oscillator"""
        low_min = data['low'].rolling(window=k_period).min()
        high_max = data['high'].rolling(window=k_period).max()
        k_percent = 100 * ((data['close'] - low_min) / (high_max - low_min))
        d_percent = k_percent.rolling(window=d_period).mean()
        return k_percent, d_percent

    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average True Range"""
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        return atr

    def calculate_trend_quality(self, data: pd.DataFrame) -> pd.Series:
        """Calcula calidad de tendencia"""
        # Alineación de EMAs
        ema_alignment = (
            (data['ema_8'] > data['ema_21']) & 
            (data['ema_21'] > data['ema_55'])
        ).astype(int)
        
        # Fuerza de tendencia
        trend_strength = abs(data['ema_8'] - data['ema_55']) / data['ema_55']
        
        # Calidad combinada
        quality = ema_alignment * trend_strength
        return quality

    def calculate_momentum_quality(self, data: pd.DataFrame) -> pd.Series:
        """Calcula calidad de momentum"""
        # RSI en zona óptima
        rsi_quality = ((data['rsi'] > 40) & (data['rsi'] < 80)).astype(int)
        
        # MACD positivo
        macd_quality = (data['macd'] > data['macd_signal']).astype(int)
        
        # Stochastic no sobrecomprado
        stoch_quality = (data['stoch_k'] < 80).astype(int)
        
        # Calidad combinada
        quality = (rsi_quality + macd_quality + stoch_quality) / 3
        return quality

    def calculate_volume_quality(self, data: pd.DataFrame) -> pd.Series:
        """Calcula calidad de volumen"""
        # Volumen por encima del promedio
        volume_above_avg = (data['volume_ratio'] > 1.5).astype(int)
        
        # Precio por encima de VWAP
        price_above_vwap = (data['close'] > data['vwap']).astype(int)
        
        # Calidad combinada
        quality = (volume_above_avg + price_above_vwap) / 2
        return quality

    def generate_high_quality_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Genera señales de alta calidad con filtros estrictos"""
        try:
            df = data.copy()
            
            # Señal base de entrada
            entry_conditions = (
                (df['trend_quality'] > 0.02) &           # Tendencia clara
                (df['momentum_quality'] > 0.6) &         # Momentum fuerte
                (df['volume_quality'] > 0.5) &           # Volumen confirmatorio
                (df['bb_position'] > 0.2) &              # No oversold
                (df['bb_position'] < 0.8) &              # No overbought
                (df['volume_ratio'] >= self.quality_filters['min_volume_spike']) &
                (abs(df['price_change']) >= self.quality_filters['min_price_movement']/100)
            )
            
            # Señal de salida
            exit_conditions = (
                (df['trend_quality'] < 0.01) |           # Tendencia debilitándose
                (df['momentum_quality'] < 0.4) |         # Momentum débil
                (df['bb_position'] > 0.9) |              # Overbought
                (df['rsi'] > 80)                         # RSI overbought
            )
            
            # Aplicar señales
            df['entry_signal'] = entry_conditions.astype(int)
            df['exit_signal'] = exit_conditions.astype(int)
            
            # Calcular calidad de señal
            df['signal_quality'] = (
                df['trend_quality'] + 
                df['momentum_quality'] + 
                df['volume_quality']
            ) / 3
            
            # Filtrar solo señales de alta calidad
            df['high_quality_entry'] = (
                (df['entry_signal'] == 1) & 
                (df['signal_quality'] > 0.7)
            ).astype(int)
            
            return df
            
        except Exception as e:
            logger.error(f"Error generando señales para {symbol}: {e}")
            return data

    def simulate_conservative_trading(self, symbol: str, data: pd.DataFrame) -> List[Dict]:
        """Simula trading conservador con gestión de riesgo estricta"""
        try:
            trades = []
            position = None
            entry_price = 0
            entry_time = None
            stop_loss_price = 0
            take_profit_price = 0
            
            daily_trades_count = 0
            current_date = None
            
            for i, (timestamp, row) in enumerate(data.iterrows()):
                current_price = row['close']
                current_date_check = timestamp.date()
                
                # Reset contador diario
                if current_date != current_date_check:
                    daily_trades_count = 0
                    current_date = current_date_check
                
                # Gestión de posición existente
                if position is not None:
                    # Stop Loss / Take Profit
                    should_exit = False
                    exit_reason = ""
                    
                    if current_price <= stop_loss_price:
                        should_exit = True
                        exit_reason = "stop_loss"
                    elif current_price >= take_profit_price:
                        should_exit = True
                        exit_reason = "take_profit"
                    elif row.get('exit_signal', 0) == 1:
                        should_exit = True
                        exit_reason = "signal_exit"
                    
                    # Cerrar posición
                    if should_exit:
                        pnl_pct = (current_price - entry_price) / entry_price
                        
                        trade = {
                            'symbol': symbol,
                            'entry_time': entry_time,
                            'exit_time': timestamp,
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'pnl_pct': pnl_pct,
                            'exit_reason': exit_reason,
                            'duration_hours': (timestamp - entry_time).total_seconds() / 3600
                        }
                        trades.append(trade)
                        position = None
                
                # Buscar nueva entrada
                if (position is None and 
                    row.get('high_quality_entry', 0) == 1 and 
                    daily_trades_count < self.max_daily_trades):
                    
                    # Calcular stop loss y take profit
                    atr = row.get('atr', current_price * 0.02)
                    stop_distance = max(atr * 2, current_price * self.max_risk_per_trade)
                    
                    entry_price = current_price
                    stop_loss_price = entry_price - stop_distance
                    take_profit_price = entry_price + (stop_distance * self.min_reward_risk_ratio)
                    
                    position = 'long'
                    entry_time = timestamp
                    daily_trades_count += 1
            
            return trades
            
        except Exception as e:
            logger.error(f"Error simulando trading para {symbol}: {e}")
            return []

    def calculate_conservative_performance(self, all_trades: List[Dict]) -> Dict:
        """Calcula rendimiento con enfoque conservador"""
        try:
            if not all_trades:
                return {
                    'initial_capital': self.initial_capital,
                    'final_capital': self.initial_capital,
                    'meets_target': False,
                    'monthly_return': 0,
                    'total_return': 0,
                    'win_rate': 0,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0
                }
            
            # Estadísticas básicas
            total_trades = len(all_trades)
            winning_trades = len([t for t in all_trades if t['pnl_pct'] > 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Calcular retornos con compounding conservador
            capital = self.initial_capital
            daily_returns = []
            
            # Procesar trades secuencialmente
            for trade in all_trades:
                # Tamaño de posición conservador (máximo 10% del capital)
                position_size = min(capital * 0.1, capital * self.max_risk_per_trade * 10)
                
                # Calcular PnL del trade
                trade_pnl = position_size * trade['pnl_pct']
                
                # Aplicar ganancia/pérdida
                old_capital = capital
                capital += trade_pnl
                
                # Calcular retorno
                if old_capital > 0:
                    trade_return = trade_pnl / old_capital
                    daily_returns.append(trade_return)
            
            # Calcular métricas finales
            total_return = (capital - self.initial_capital) / self.initial_capital
            
            if len(daily_returns) > 0:
                avg_daily_return = np.mean(daily_returns)
                # Estimar retorno mensual (asumiendo ~20 días de trading por mes)
                monthly_return = (1 + avg_daily_return) ** 20 - 1
                
                # Volatilidad y Sharpe
                volatility = np.std(daily_returns) if len(daily_returns) > 1 else 0
                sharpe_ratio = avg_daily_return / volatility if volatility > 0 else 0
                
                # Drawdown
                capital_series = [self.initial_capital]
                running_capital = self.initial_capital
                for ret in daily_returns:
                    running_capital *= (1 + ret)
                    capital_series.append(running_capital)
                
                capital_series = pd.Series(capital_series)
                rolling_max = capital_series.expanding().max()
                drawdown = (capital_series - rolling_max) / rolling_max
                max_drawdown = drawdown.min()
            else:
                monthly_return = 0
                sharpe_ratio = 0
                max_drawdown = 0
            
            performance = {
                'initial_capital': self.initial_capital,
                'final_capital': capital,
                'total_return': total_return,
                'monthly_return': monthly_return,
                'win_rate': win_rate,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'meets_target': monthly_return >= self.target_monthly_return and win_rate >= self.min_win_rate
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error calculando rendimiento conservador: {e}")
            return {
                'initial_capital': self.initial_capital,
                'final_capital': self.initial_capital,
                'meets_target': False,
                'monthly_return': 0,
                'total_return': 0,
                'win_rate': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0
            }

    def run_optimized_system(self) -> Dict:
        """Ejecuta sistema optimizado completo"""
        logger.info("🎯 INICIANDO SISTEMA OPTIMIZADO PARA 5% MENSUAL")
        
        try:
            all_trades = []
            symbol_performance = {}
            
            # Análisis por símbolo premium
            for symbol in self.premium_symbols:
                logger.info(f"📊 Analizando {symbol} con filtros de calidad...")
                
                # Generar datos de alta calidad
                data = self.generate_high_quality_data(symbol, 90)  # 3 meses
                
                if data.empty:
                    continue
                
                # Calcular indicadores avanzados
                data = self.calculate_advanced_indicators(data)
                
                # Generar señales de alta calidad
                data = self.generate_high_quality_signals(data, symbol)
                
                # Simular trading conservador
                symbol_trades = self.simulate_conservative_trading(symbol, data)
                all_trades.extend(symbol_trades)
                
                # Estadísticas por símbolo
                if symbol_trades:
                    symbol_pnl = [t['pnl_pct'] for t in symbol_trades]
                    symbol_performance[symbol] = {
                        'total_trades': len(symbol_trades),
                        'win_rate': len([p for p in symbol_pnl if p > 0]) / len(symbol_pnl),
                        'avg_pnl': np.mean(symbol_pnl),
                        'best_trade': max(symbol_pnl),
                        'worst_trade': min(symbol_pnl)
                    }
            
            # Calcular rendimiento conservador
            performance = self.calculate_conservative_performance(all_trades)
            
            # Compilar resultados
            results = {
                'system_name': self.name,
                'analysis_timestamp': datetime.now().isoformat(),
                'target_monthly_return': self.target_monthly_return,
                'performance': performance,
                'symbol_performance': symbol_performance,
                'quality_filters': self.quality_filters,
                'risk_management': {
                    'max_risk_per_trade': self.max_risk_per_trade,
                    'min_win_rate': self.min_win_rate,
                    'min_reward_risk_ratio': self.min_reward_risk_ratio,
                    'max_daily_trades': self.max_daily_trades
                }
            }
            
            # Log resultados
            if performance:
                logger.info(f"✅ SISTEMA OPTIMIZADO COMPLETADO")
                logger.info(f"💰 Capital final: ${performance['final_capital']:,.2f}")
                logger.info(f"📈 Retorno total: {performance['total_return']*100:.2f}%")
                logger.info(f"🎯 Retorno mensual: {performance['monthly_return']*100:.2f}%")
                logger.info(f"🏆 Cumple objetivo: {'SÍ' if performance['meets_target'] else 'NO'}")
                logger.info(f"📊 Total trades: {performance['total_trades']}")
                logger.info(f"🎲 Win rate: {performance['win_rate']*100:.1f}%")
                logger.info(f"📉 Max drawdown: {performance['max_drawdown']*100:.2f}%")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en sistema optimizado: {e}")
            return {}

def main():
    """Función principal"""
    print("🎯 SISTEMA OPTIMIZADO PARA 5% MENSUAL SIN APALANCAMIENTO")
    print("=" * 60)
    
    # Crear sistema optimizado
    system = Optimized5PercentSystem()
    
    # Ejecutar análisis
    results = system.run_optimized_system()
    
    if results and results.get('performance'):
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"optimized_5percent_results_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        perf = results['performance']
        
        print(f"\n📊 RESULTADOS GUARDADOS EN: {filename}")
        print(f"💰 Capital inicial: ${perf['initial_capital']:,.2f}")
        print(f"💰 Capital final: ${perf['final_capital']:,.2f}")
        print(f"📈 Retorno total: {perf['total_return']*100:.2f}%")
        print(f"🎯 Retorno mensual: {perf['monthly_return']*100:.2f}%")
        print(f"🏆 Cumple objetivo 5%: {'✅ SÍ' if perf['meets_target'] else '❌ NO'}")
        print(f"📊 Total trades: {perf['total_trades']}")
        print(f"🎲 Win rate: {perf['win_rate']*100:.1f}%")
        print(f"📉 Max drawdown: {perf['max_drawdown']*100:.2f}%")
        
        if perf['meets_target']:
            print("\n🎉 ¡SISTEMA OPTIMIZADO EXITOSO!")
            print("✅ Logra 5% mensual con gestión de riesgo conservadora")
        else:
            print("\n⚠️  Sistema requiere ajustes adicionales")
            print("💡 Sugerencias: Ajustar filtros de calidad o parámetros de riesgo")
    
    else:
        print("❌ Error en el sistema optimizado")

if __name__ == "__main__":
    main()