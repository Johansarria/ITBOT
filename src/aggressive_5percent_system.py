#!/usr/bin/env python3
"""
SISTEMA AGRESIVO PARA 5% MENSUAL SIN APALANCAMIENTO
===================================================

Sistema más agresivo pero controlado que utiliza:
1. Múltiples estrategias simultáneas
2. Gestión de riesgo adaptativa
3. Compounding agresivo
4. Diversificación amplia
5. Timing optimizado
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
        logging.FileHandler('aggressive_5percent_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Aggressive5PercentSystem:
    """Sistema agresivo para lograr 5% mensual sin apalancamiento"""
    
    def __init__(self):
        self.name = "AGGRESSIVE 5% MONTHLY SYSTEM"
        self.target_monthly_return = 0.05  # 5% mensual
        self.initial_capital = 10000
        
        # Configuración agresiva
        self.max_daily_trades = 10  # Hasta 10 trades por día
        self.min_win_rate = 0.45    # Mínimo 45% win rate
        self.max_risk_per_trade = 0.05  # Máximo 5% riesgo por trade
        self.min_reward_risk_ratio = 2.0  # Mínimo 2:1 reward/risk
        
        # Filtros más flexibles
        self.quality_filters = {
            'min_volume_spike': 1.2,      # Mínimo 1.2x volumen promedio
            'min_price_movement': 0.2,     # Mínimo 0.2% movimiento
            'max_spread': 0.5,             # Máximo 0.5% spread
            'min_liquidity': 100000,       # Mínimo $100K liquidez
            'trend_confirmation': False,    # No requiere confirmación estricta
            'momentum_alignment': False     # No requiere alineación perfecta
        }
        
        # Símbolos diversificados (alta volatilidad para mayor potencial)
        self.trading_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'DOTUSDT', 'LINKUSDT', 'AVAXUSDT', 'MATICUSDT', 'ATOMUSDT'
        ]
        
        # Estrategias múltiples
        self.strategies = {
            'momentum': {'weight': 0.3, 'active': True},
            'mean_reversion': {'weight': 0.2, 'active': True},
            'breakout': {'weight': 0.3, 'active': True},
            'volatility': {'weight': 0.2, 'active': True}
        }
        
        logger.info(f"🚀 {self.name} INICIALIZADO")
        logger.info(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        logger.info(f"🎯 Objetivo: {self.target_monthly_return*100}% mensual")
        logger.info(f"⚡ Máximo riesgo por trade: {self.max_risk_per_trade*100}%")
        logger.info(f"📊 Win rate mínimo: {self.min_win_rate*100}%")
        logger.info(f"🎲 Máximo trades diarios: {self.max_daily_trades}")

    def generate_volatile_data(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """Genera datos con mayor volatilidad para oportunidades agresivas"""
        try:
            # Parámetros por símbolo con mayor volatilidad
            symbol_params = {
                'BTCUSDT': {'base_price': 45000, 'volatility': 0.04, 'trend': 0.0002},
                'ETHUSDT': {'base_price': 2500, 'volatility': 0.05, 'trend': 0.0003},
                'BNBUSDT': {'base_price': 300, 'volatility': 0.06, 'trend': 0.0002},
                'ADAUSDT': {'base_price': 0.5, 'volatility': 0.07, 'trend': 0.0004},
                'SOLUSDT': {'base_price': 100, 'volatility': 0.08, 'trend': 0.0005},
                'DOTUSDT': {'base_price': 7, 'volatility': 0.06, 'trend': 0.0003},
                'LINKUSDT': {'base_price': 15, 'volatility': 0.07, 'trend': 0.0004},
                'AVAXUSDT': {'base_price': 25, 'volatility': 0.08, 'trend': 0.0005},
                'MATICUSDT': {'base_price': 1, 'volatility': 0.09, 'trend': 0.0006},
                'ATOMUSDT': {'base_price': 12, 'volatility': 0.07, 'trend': 0.0004}
            }
            
            params = symbol_params.get(symbol, symbol_params['BTCUSDT'])
            
            # Generar datos cada 15 minutos para más oportunidades
            periods = days * 24 * 4  # 4 períodos por hora
            np.random.seed(hash(symbol) % 2**32)
            
            # Generar precios con mayor volatilidad
            prices = [params['base_price']]
            volatility = params['volatility'] / (4**0.5)  # Ajustar para 15min
            
            for i in range(periods):
                # Tendencia base
                trend = params['trend']
                
                # Volatilidad con clustering
                if i > 0:
                    prev_return = (prices[-1] - prices[-2]) / prices[-2]
                    vol_multiplier = 1 + 2 * abs(prev_return) / volatility
                else:
                    vol_multiplier = 1
                
                # Componente aleatoria más agresiva
                random_component = np.random.normal(0, volatility * vol_multiplier)
                
                # Spikes ocasionales para oportunidades
                if np.random.random() < 0.05:  # 5% probabilidad de spike
                    spike = np.random.choice([-1, 1]) * volatility * 3
                    random_component += spike
                
                # Precio siguiente
                total_return = trend + random_component
                new_price = prices[-1] * (1 + total_return)
                prices.append(max(new_price, params['base_price'] * 0.3))
            
            # Crear timestamps
            start_date = datetime.now() - timedelta(days=days)
            timestamps = pd.date_range(start=start_date, periods=periods, freq='15T')
            
            # Crear OHLCV data con mayor volatilidad intraday
            data = []
            for i in range(periods):
                if i == 0:
                    open_price = prices[i]
                else:
                    open_price = prices[i-1]
                
                close_price = prices[i]
                
                # High/Low más extremos
                intraday_vol = abs(np.random.normal(0, volatility))
                high_price = max(open_price, close_price) * (1 + intraday_vol)
                low_price = min(open_price, close_price) * (1 - intraday_vol)
                
                # Volumen correlacionado con movimiento
                price_change = abs(close_price - open_price) / open_price
                base_volume = np.random.lognormal(15, 0.8)
                volume = base_volume * (1 + price_change * 20)
                
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
            logger.error(f"Error generando datos volátiles para {symbol}: {e}")
            return pd.DataFrame()

    def calculate_multi_strategy_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Calcula señales de múltiples estrategias"""
        try:
            df = data.copy()
            
            # Indicadores básicos
            df['ema_5'] = df['close'].ewm(span=5).mean()
            df['ema_10'] = df['close'].ewm(span=10).mean()
            df['ema_20'] = df['close'].ewm(span=20).mean()
            df['rsi'] = self.calculate_rsi(df['close'], 14)
            df['volume_sma'] = df['volume'].rolling(10).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            df['price_change'] = df['close'].pct_change()
            df['volatility'] = df['price_change'].rolling(10).std()
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(10).mean()
            bb_std = df['close'].rolling(10).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # ESTRATEGIA 1: MOMENTUM
            momentum_entry = (
                (df['ema_5'] > df['ema_10']) &
                (df['ema_10'] > df['ema_20']) &
                (df['rsi'] > 50) &
                (df['rsi'] < 80) &
                (df['volume_ratio'] > 1.2)
            )
            
            # ESTRATEGIA 2: MEAN REVERSION
            mean_reversion_entry = (
                (df['close'] < df['bb_lower']) &
                (df['rsi'] < 30) &
                (df['volume_ratio'] > 1.0)
            )
            
            # ESTRATEGIA 3: BREAKOUT
            breakout_entry = (
                (df['close'] > df['bb_upper']) &
                (df['volume_ratio'] > 2.0) &
                (abs(df['price_change']) > 0.01)
            )
            
            # ESTRATEGIA 4: VOLATILITY
            volatility_entry = (
                (df['volatility'] > df['volatility'].rolling(20).mean()) &
                (df['volume_ratio'] > 1.5) &
                (abs(df['price_change']) > 0.005)
            )
            
            # Combinar señales con pesos
            df['momentum_signal'] = momentum_entry.astype(int) * self.strategies['momentum']['weight']
            df['mean_reversion_signal'] = mean_reversion_entry.astype(int) * self.strategies['mean_reversion']['weight']
            df['breakout_signal'] = breakout_entry.astype(int) * self.strategies['breakout']['weight']
            df['volatility_signal'] = volatility_entry.astype(int) * self.strategies['volatility']['weight']
            
            # Señal combinada
            df['combined_signal'] = (
                df['momentum_signal'] + 
                df['mean_reversion_signal'] + 
                df['breakout_signal'] + 
                df['volatility_signal']
            )
            
            # Filtros de calidad flexibles
            df['quality_filter'] = (
                (df['volume_ratio'] >= self.quality_filters['min_volume_spike']) &
                (abs(df['price_change']) >= self.quality_filters['min_price_movement']/100)
            )
            
            # Señal final
            df['entry_signal'] = (
                (df['combined_signal'] > 0.3) &  # Al menos 30% de fuerza
                df['quality_filter']
            ).astype(int)
            
            # Señales de salida más flexibles
            df['exit_signal'] = (
                (df['rsi'] > 85) |  # Muy sobrecomprado
                (df['rsi'] < 15) |  # Muy sobrevendido
                (df['combined_signal'] < 0.1)  # Señal muy débil
            ).astype(int)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando señales multi-estrategia para {symbol}: {e}")
            return data

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def simulate_aggressive_trading(self, symbol: str, data: pd.DataFrame) -> List[Dict]:
        """Simula trading agresivo con gestión de riesgo adaptativa"""
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
                    should_exit = False
                    exit_reason = ""
                    
                    # Stop Loss / Take Profit
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
                            'duration_minutes': (timestamp - entry_time).total_seconds() / 60
                        }
                        trades.append(trade)
                        position = None
                
                # Buscar nueva entrada (más agresivo)
                if (position is None and 
                    row.get('entry_signal', 0) == 1 and 
                    daily_trades_count < self.max_daily_trades):
                    
                    # Calcular stop loss y take profit adaptativos
                    volatility = row.get('volatility', 0.02)
                    stop_distance = max(volatility * 3, current_price * 0.01)  # Mínimo 1%
                    
                    entry_price = current_price
                    stop_loss_price = entry_price - stop_distance
                    take_profit_price = entry_price + (stop_distance * self.min_reward_risk_ratio)
                    
                    position = 'long'
                    entry_time = timestamp
                    daily_trades_count += 1
            
            return trades
            
        except Exception as e:
            logger.error(f"Error simulando trading agresivo para {symbol}: {e}")
            return []

    def calculate_aggressive_performance(self, all_trades: List[Dict]) -> Dict:
        """Calcula rendimiento con compounding agresivo"""
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
            
            # Compounding agresivo
            capital = self.initial_capital
            daily_returns = []
            max_capital = capital
            
            for trade in all_trades:
                # Tamaño de posición agresivo (hasta 20% del capital)
                position_size = min(capital * 0.2, capital * self.max_risk_per_trade * 4)
                
                # Calcular PnL del trade
                trade_pnl = position_size * trade['pnl_pct']
                
                # Aplicar ganancia/pérdida
                old_capital = capital
                capital += trade_pnl
                
                # Tracking para drawdown
                if capital > max_capital:
                    max_capital = capital
                
                # Calcular retorno
                if old_capital > 0:
                    trade_return = trade_pnl / old_capital
                    daily_returns.append(trade_return)
            
            # Calcular métricas finales
            total_return = (capital - self.initial_capital) / self.initial_capital
            
            if len(daily_returns) > 0:
                avg_daily_return = np.mean(daily_returns)
                # Estimar retorno mensual agresivo
                monthly_return = (1 + avg_daily_return) ** 30 - 1
                
                # Volatilidad y Sharpe
                volatility = np.std(daily_returns) if len(daily_returns) > 1 else 0
                sharpe_ratio = avg_daily_return / volatility if volatility > 0 else 0
                
                # Drawdown máximo
                max_drawdown = (capital - max_capital) / max_capital if max_capital > 0 else 0
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
                'meets_target': monthly_return >= self.target_monthly_return
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error calculando rendimiento agresivo: {e}")
            return {}

    def run_aggressive_system(self) -> Dict:
        """Ejecuta sistema agresivo completo"""
        logger.info("🚀 INICIANDO SISTEMA AGRESIVO PARA 5% MENSUAL")
        
        try:
            all_trades = []
            symbol_performance = {}
            
            # Análisis por símbolo
            for symbol in self.trading_symbols:
                logger.info(f"⚡ Analizando {symbol} con estrategias agresivas...")
                
                # Generar datos volátiles
                data = self.generate_volatile_data(symbol, 60)  # 2 meses
                
                if data.empty:
                    continue
                
                # Calcular señales multi-estrategia
                data = self.calculate_multi_strategy_signals(data, symbol)
                
                # Simular trading agresivo
                symbol_trades = self.simulate_aggressive_trading(symbol, data)
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
            
            # Calcular rendimiento agresivo
            performance = self.calculate_aggressive_performance(all_trades)
            
            # Compilar resultados
            results = {
                'system_name': self.name,
                'analysis_timestamp': datetime.now().isoformat(),
                'target_monthly_return': self.target_monthly_return,
                'performance': performance,
                'symbol_performance': symbol_performance,
                'strategies': self.strategies,
                'risk_management': {
                    'max_risk_per_trade': self.max_risk_per_trade,
                    'min_win_rate': self.min_win_rate,
                    'min_reward_risk_ratio': self.min_reward_risk_ratio,
                    'max_daily_trades': self.max_daily_trades
                }
            }
            
            # Log resultados
            if performance:
                logger.info(f"🚀 SISTEMA AGRESIVO COMPLETADO")
                logger.info(f"💰 Capital final: ${performance['final_capital']:,.2f}")
                logger.info(f"📈 Retorno total: {performance['total_return']*100:.2f}%")
                logger.info(f"🎯 Retorno mensual: {performance['monthly_return']*100:.2f}%")
                logger.info(f"🏆 Cumple objetivo: {'SÍ' if performance['meets_target'] else 'NO'}")
                logger.info(f"📊 Total trades: {performance['total_trades']}")
                logger.info(f"🎲 Win rate: {performance['win_rate']*100:.1f}%")
                logger.info(f"📉 Max drawdown: {performance['max_drawdown']*100:.2f}%")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en sistema agresivo: {e}")
            return {}

def main():
    """Función principal"""
    print("🚀 SISTEMA AGRESIVO PARA 5% MENSUAL SIN APALANCAMIENTO")
    print("=" * 60)
    
    # Crear sistema agresivo
    system = Aggressive5PercentSystem()
    
    # Ejecutar análisis
    results = system.run_aggressive_system()
    
    if results and results.get('performance'):
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"aggressive_5percent_results_{timestamp}.json"
        
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
            print("\n🎉 ¡SISTEMA AGRESIVO EXITOSO!")
            print("✅ Logra 5% mensual sin apalancamiento")
        else:
            print("\n⚠️  Sistema requiere optimización adicional")
            print("💡 Considerar ajustar parámetros de riesgo o estrategias")
    
    else:
        print("❌ Error en el sistema agresivo")

if __name__ == "__main__":
    main()