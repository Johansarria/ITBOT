#!/usr/bin/env python3
"""
SISTEMA REALISTA PARA 5% MENSUAL SIN APALANCAMIENTO
===================================================

Sistema balanceado y realista que utiliza:
1. Gestión de riesgo prudente
2. Compounding controlado
3. Diversificación inteligente
4. Parámetros sostenibles
5. Validación rigurosa
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
        logging.FileHandler('realistic_5percent_system.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Realistic5PercentSystem:
    """Sistema realista para lograr 5% mensual de forma sostenible"""
    
    def __init__(self):
        self.name = "REALISTIC 5% MONTHLY SYSTEM"
        self.target_monthly_return = 0.05  # 5% mensual
        self.initial_capital = 10000
        
        # Configuración realista
        self.max_daily_trades = 5      # Máximo 5 trades por día
        self.min_win_rate = 0.55       # Mínimo 55% win rate
        self.max_risk_per_trade = 0.02 # Máximo 2% riesgo por trade
        self.max_position_size = 0.15  # Máximo 15% del capital por posición
        self.min_reward_risk_ratio = 2.5  # Mínimo 2.5:1 reward/risk
        
        # Filtros balanceados
        self.quality_filters = {
            'min_volume_spike': 1.5,      # Mínimo 1.5x volumen promedio
            'min_price_movement': 0.3,     # Mínimo 0.3% movimiento
            'max_spread': 0.2,             # Máximo 0.2% spread
            'min_confidence': 0.6,         # Mínimo 60% confianza
            'trend_alignment': True        # Requiere alineación de tendencia
        }
        
        # Símbolos balanceados (liquidez + oportunidad)
        self.balanced_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT'
        ]
        
        # Control de compounding
        self.compounding_limit = 0.5   # Máximo 50% de ganancia se reinvierte
        self.drawdown_limit = 0.15     # Máximo 15% drawdown
        
        logger.info(f"⚖️ {self.name} INICIALIZADO")
        logger.info(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        logger.info(f"🎯 Objetivo: {self.target_monthly_return*100}% mensual")
        logger.info(f"🛡️ Máximo riesgo por trade: {self.max_risk_per_trade*100}%")
        logger.info(f"📊 Win rate mínimo: {self.min_win_rate*100}%")
        logger.info(f"🔄 Límite compounding: {self.compounding_limit*100}%")

    def generate_realistic_data(self, symbol: str, days: int = 90) -> pd.DataFrame:
        """Genera datos realistas basados en patrones de mercado reales"""
        try:
            # Parámetros realistas por símbolo
            symbol_params = {
                'BTCUSDT': {
                    'base_price': 45000,
                    'daily_volatility': 0.025,  # 2.5% diario
                    'trend_strength': 0.0001,
                    'mean_reversion': 0.1,
                    'volume_base': 17
                },
                'ETHUSDT': {
                    'base_price': 2500,
                    'daily_volatility': 0.03,   # 3% diario
                    'trend_strength': 0.0002,
                    'mean_reversion': 0.12,
                    'volume_base': 16.5
                },
                'BNBUSDT': {
                    'base_price': 300,
                    'daily_volatility': 0.035,  # 3.5% diario
                    'trend_strength': 0.0001,
                    'mean_reversion': 0.15,
                    'volume_base': 16
                },
                'ADAUSDT': {
                    'base_price': 0.5,
                    'daily_volatility': 0.04,   # 4% diario
                    'trend_strength': 0.0003,
                    'mean_reversion': 0.18,
                    'volume_base': 15.5
                },
                'SOLUSDT': {
                    'base_price': 100,
                    'daily_volatility': 0.05,   # 5% diario
                    'trend_strength': 0.0004,
                    'mean_reversion': 0.2,
                    'volume_base': 15
                }
            }
            
            params = symbol_params.get(symbol, symbol_params['BTCUSDT'])
            
            # Generar datos cada hora
            hours = days * 24
            np.random.seed(hash(symbol) % 2**32)
            
            # Generar precios con patrones realistas
            prices = [params['base_price']]
            volatility = params['daily_volatility'] / 24**0.5
            
            for i in range(hours):
                # Componente de tendencia
                trend = params['trend_strength']
                
                # Mean reversion
                current_price = prices[-1]
                distance_from_base = (current_price - params['base_price']) / params['base_price']
                mean_reversion = -distance_from_base * params['mean_reversion']
                
                # Volatility clustering realista
                if i > 0:
                    prev_return = (prices[-1] - prices[-2]) / prices[-2]
                    vol_clustering = 1 + 0.3 * abs(prev_return) / volatility
                else:
                    vol_clustering = 1
                
                # Componente aleatoria
                random_component = np.random.normal(0, volatility * vol_clustering)
                
                # Eventos especiales ocasionales (5% probabilidad)
                if np.random.random() < 0.05:
                    event_impact = np.random.choice([-1, 1]) * volatility * 2
                    random_component += event_impact
                
                # Precio siguiente
                total_return = trend + mean_reversion + random_component
                new_price = current_price * (1 + total_return)
                new_price = max(new_price, params['base_price'] * 0.5)  # Floor
                prices.append(new_price)
            
            # Crear timestamps
            start_date = datetime.now() - timedelta(days=days)
            timestamps = pd.date_range(start=start_date, periods=hours, freq='1H')
            
            # Crear OHLCV data realista
            data = []
            for i in range(hours):
                if i == 0:
                    open_price = prices[i]
                else:
                    open_price = prices[i-1]
                
                close_price = prices[i]
                
                # High/Low realistas
                intraday_vol = abs(np.random.normal(0, volatility * 0.3))
                high_price = max(open_price, close_price) * (1 + intraday_vol)
                low_price = min(open_price, close_price) * (1 - intraday_vol)
                
                # Volumen realista
                price_change = abs(close_price - open_price) / open_price
                base_volume = np.random.lognormal(params['volume_base'], 0.5)
                volume = base_volume * (1 + price_change * 5)
                
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
            logger.error(f"Error generando datos realistas para {symbol}: {e}")
            return pd.DataFrame()

    def calculate_balanced_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos balanceados"""
        try:
            df = data.copy()
            
            # EMAs para tendencia
            df['ema_8'] = df['close'].ewm(span=8).mean()
            df['ema_21'] = df['close'].ewm(span=21).mean()
            df['ema_55'] = df['close'].ewm(span=55).mean()
            
            # RSI para momentum
            df['rsi'] = self.calculate_rsi(df['close'], 14)
            
            # MACD para señales
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
            
            # Volumen
            df['volume_sma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # ATR para volatilidad
            df['atr'] = self.calculate_atr(df)
            
            # Indicadores de calidad
            df['price_change'] = df['close'].pct_change()
            df['volatility'] = df['price_change'].rolling(20).std()
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculando indicadores balanceados: {e}")
            return data

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula Average True Range"""
        high_low = data['high'] - data['low']
        high_close = np.abs(data['high'] - data['close'].shift())
        low_close = np.abs(data['low'] - data['close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        atr = true_range.rolling(window=period).mean()
        return atr

    def generate_balanced_signals(self, data: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Genera señales balanceadas con alta confianza"""
        try:
            df = data.copy()
            
            # Condiciones de tendencia alcista
            trend_up = (
                (df['ema_8'] > df['ema_21']) &
                (df['ema_21'] > df['ema_55']) &
                (df['close'] > df['ema_8'])
            )
            
            # Condiciones de momentum
            momentum_good = (
                (df['rsi'] > 45) &
                (df['rsi'] < 75) &
                (df['macd'] > df['macd_signal']) &
                (df['macd_histogram'] > 0)
            )
            
            # Condiciones de volumen
            volume_confirm = (
                (df['volume_ratio'] >= self.quality_filters['min_volume_spike']) &
                (df['volume_ratio'] < 5.0)  # No volumen extremo
            )
            
            # Condiciones de precio
            price_movement = (
                (abs(df['price_change']) >= self.quality_filters['min_price_movement']/100) &
                (abs(df['price_change']) < 0.1)  # No movimientos extremos
            )
            
            # Posición en Bollinger Bands
            bb_position_good = (
                (df['bb_position'] > 0.2) &
                (df['bb_position'] < 0.8)
            )
            
            # Señal de entrada (todas las condiciones)
            df['entry_signal'] = (
                trend_up &
                momentum_good &
                volume_confirm &
                price_movement &
                bb_position_good
            ).astype(int)
            
            # Calcular confianza de la señal
            df['signal_confidence'] = (
                trend_up.astype(int) * 0.3 +
                momentum_good.astype(int) * 0.25 +
                volume_confirm.astype(int) * 0.2 +
                price_movement.astype(int) * 0.15 +
                bb_position_good.astype(int) * 0.1
            )
            
            # Filtrar por confianza mínima
            df['high_confidence_entry'] = (
                (df['entry_signal'] == 1) &
                (df['signal_confidence'] >= self.quality_filters['min_confidence'])
            ).astype(int)
            
            # Señales de salida
            df['exit_signal'] = (
                (df['rsi'] > 80) |  # Sobrecomprado
                (df['bb_position'] > 0.9) |  # Muy alto en BB
                (df['macd'] < df['macd_signal']) |  # MACD bajista
                (df['ema_8'] < df['ema_21'])  # Tendencia cambiando
            ).astype(int)
            
            return df
            
        except Exception as e:
            logger.error(f"Error generando señales balanceadas para {symbol}: {e}")
            return data

    def simulate_realistic_trading(self, symbol: str, data: pd.DataFrame, current_capital: float) -> List[Dict]:
        """Simula trading realista con gestión de riesgo prudente"""
        try:
            trades = []
            position = None
            entry_price = 0
            entry_time = None
            stop_loss_price = 0
            take_profit_price = 0
            position_size = 0
            
            daily_trades_count = 0
            current_date = None
            max_capital_seen = current_capital
            
            for i, (timestamp, row) in enumerate(data.iterrows()):
                current_price = row['close']
                current_date_check = timestamp.date()
                
                # Reset contador diario
                if current_date != current_date_check:
                    daily_trades_count = 0
                    current_date = current_date_check
                
                # Control de drawdown
                current_drawdown = (current_capital - max_capital_seen) / max_capital_seen
                if current_drawdown < -self.drawdown_limit:
                    continue  # Parar trading si drawdown excede límite
                
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
                        pnl_amount = position_size * pnl_pct
                        
                        trade = {
                            'symbol': symbol,
                            'entry_time': entry_time,
                            'exit_time': timestamp,
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'position_size': position_size,
                            'pnl_pct': pnl_pct,
                            'pnl_amount': pnl_amount,
                            'exit_reason': exit_reason,
                            'duration_hours': (timestamp - entry_time).total_seconds() / 3600
                        }
                        trades.append(trade)
                        
                        # Actualizar capital
                        current_capital += pnl_amount
                        if current_capital > max_capital_seen:
                            max_capital_seen = current_capital
                        
                        position = None
                
                # Buscar nueva entrada
                if (position is None and 
                    row.get('high_confidence_entry', 0) == 1 and 
                    daily_trades_count < self.max_daily_trades and
                    current_capital > 0):
                    
                    # Calcular tamaño de posición realista
                    max_position = current_capital * self.max_position_size
                    risk_amount = current_capital * self.max_risk_per_trade
                    
                    # Stop loss basado en ATR
                    atr = row.get('atr', current_price * 0.02)
                    stop_distance = max(atr * 2, current_price * 0.01)
                    
                    # Tamaño de posición basado en riesgo
                    position_size = min(max_position, risk_amount / (stop_distance / current_price))
                    
                    if position_size > current_capital * 0.05:  # Mínimo 5% para que valga la pena
                        entry_price = current_price
                        stop_loss_price = entry_price - stop_distance
                        take_profit_price = entry_price + (stop_distance * self.min_reward_risk_ratio)
                        
                        position = 'long'
                        entry_time = timestamp
                        daily_trades_count += 1
            
            return trades
            
        except Exception as e:
            logger.error(f"Error simulando trading realista para {symbol}: {e}")
            return []

    def calculate_realistic_performance(self, all_trades: List[Dict]) -> Dict:
        """Calcula rendimiento realista con compounding controlado"""
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
                    'max_drawdown': 0,
                    'avg_trade_duration': 0
                }
            
            # Estadísticas básicas
            total_trades = len(all_trades)
            winning_trades = len([t for t in all_trades if t['pnl_amount'] > 0])
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            # Simular compounding controlado
            capital = self.initial_capital
            daily_returns = []
            max_capital = capital
            capital_history = [capital]
            
            # Procesar trades cronológicamente
            sorted_trades = sorted(all_trades, key=lambda x: x['entry_time'])
            
            for trade in sorted_trades:
                # Aplicar PnL
                old_capital = capital
                capital += trade['pnl_amount']
                
                # Control de compounding (solo reinvertir parte de las ganancias)
                if trade['pnl_amount'] > 0:
                    reinvestment = trade['pnl_amount'] * self.compounding_limit
                    capital = old_capital + reinvestment
                
                # Tracking para métricas
                if capital > max_capital:
                    max_capital = capital
                
                capital_history.append(capital)
                
                # Calcular retorno del trade
                if old_capital > 0:
                    trade_return = (capital - old_capital) / old_capital
                    daily_returns.append(trade_return)
            
            # Calcular métricas finales
            total_return = (capital - self.initial_capital) / self.initial_capital
            
            if len(daily_returns) > 0:
                avg_daily_return = np.mean(daily_returns)
                # Estimar retorno mensual (20 días de trading)
                monthly_return = (1 + avg_daily_return) ** 20 - 1
                
                # Volatilidad y Sharpe
                volatility = np.std(daily_returns) if len(daily_returns) > 1 else 0
                sharpe_ratio = avg_daily_return / volatility if volatility > 0 else 0
                
                # Drawdown máximo
                capital_series = pd.Series(capital_history)
                rolling_max = capital_series.expanding().max()
                drawdown = (capital_series - rolling_max) / rolling_max
                max_drawdown = drawdown.min()
                
                # Duración promedio de trades
                durations = [t['duration_hours'] for t in all_trades if 'duration_hours' in t]
                avg_trade_duration = np.mean(durations) if durations else 0
            else:
                monthly_return = 0
                sharpe_ratio = 0
                max_drawdown = 0
                avg_trade_duration = 0
            
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
                'avg_trade_duration': avg_trade_duration,
                'meets_target': monthly_return >= self.target_monthly_return and win_rate >= self.min_win_rate
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error calculando rendimiento realista: {e}")
            return {}

    def run_realistic_system(self) -> Dict:
        """Ejecuta sistema realista completo"""
        logger.info("⚖️ INICIANDO SISTEMA REALISTA PARA 5% MENSUAL")
        
        try:
            all_trades = []
            symbol_performance = {}
            current_capital = self.initial_capital
            
            # Análisis por símbolo
            for symbol in self.balanced_symbols:
                logger.info(f"📊 Analizando {symbol} con parámetros realistas...")
                
                # Generar datos realistas
                data = self.generate_realistic_data(symbol, 90)  # 3 meses
                
                if data.empty:
                    continue
                
                # Calcular indicadores balanceados
                data = self.calculate_balanced_indicators(data)
                
                # Generar señales balanceadas
                data = self.generate_balanced_signals(data, symbol)
                
                # Simular trading realista
                symbol_trades = self.simulate_realistic_trading(symbol, data, current_capital)
                all_trades.extend(symbol_trades)
                
                # Estadísticas por símbolo
                if symbol_trades:
                    symbol_pnl = [t['pnl_amount'] for t in symbol_trades]
                    symbol_performance[symbol] = {
                        'total_trades': len(symbol_trades),
                        'win_rate': len([p for p in symbol_pnl if p > 0]) / len(symbol_pnl),
                        'total_pnl': sum(symbol_pnl),
                        'avg_pnl': np.mean(symbol_pnl),
                        'best_trade': max(symbol_pnl),
                        'worst_trade': min(symbol_pnl)
                    }
            
            # Calcular rendimiento realista
            performance = self.calculate_realistic_performance(all_trades)
            
            # Compilar resultados
            results = {
                'system_name': self.name,
                'analysis_timestamp': datetime.now().isoformat(),
                'target_monthly_return': self.target_monthly_return,
                'performance': performance,
                'symbol_performance': symbol_performance,
                'risk_management': {
                    'max_risk_per_trade': self.max_risk_per_trade,
                    'max_position_size': self.max_position_size,
                    'min_win_rate': self.min_win_rate,
                    'min_reward_risk_ratio': self.min_reward_risk_ratio,
                    'max_daily_trades': self.max_daily_trades,
                    'compounding_limit': self.compounding_limit,
                    'drawdown_limit': self.drawdown_limit
                }
            }
            
            # Log resultados
            if performance:
                logger.info(f"⚖️ SISTEMA REALISTA COMPLETADO")
                logger.info(f"💰 Capital final: ${performance['final_capital']:,.2f}")
                logger.info(f"📈 Retorno total: {performance['total_return']*100:.2f}%")
                logger.info(f"🎯 Retorno mensual: {performance['monthly_return']*100:.2f}%")
                logger.info(f"🏆 Cumple objetivo: {'SÍ' if performance['meets_target'] else 'NO'}")
                logger.info(f"📊 Total trades: {performance['total_trades']}")
                logger.info(f"🎲 Win rate: {performance['win_rate']*100:.1f}%")
                logger.info(f"📉 Max drawdown: {performance['max_drawdown']*100:.2f}%")
                logger.info(f"⏱️ Duración promedio: {performance['avg_trade_duration']:.1f} horas")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en sistema realista: {e}")
            return {}

def main():
    """Función principal"""
    print("⚖️ SISTEMA REALISTA PARA 5% MENSUAL SIN APALANCAMIENTO")
    print("=" * 60)
    
    # Crear sistema realista
    system = Realistic5PercentSystem()
    
    # Ejecutar análisis
    results = system.run_realistic_system()
    
    if results and results.get('performance'):
        # Guardar resultados
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"realistic_5percent_results_{timestamp}.json"
        
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
        print(f"⏱️ Duración promedio: {perf['avg_trade_duration']:.1f} horas")
        
        if perf['meets_target']:
            print("\n🎉 ¡SISTEMA REALISTA EXITOSO!")
            print("✅ Logra 5% mensual de forma sostenible")
            print("🛡️ Con gestión de riesgo prudente")
        else:
            print("\n⚠️  Sistema requiere ajustes adicionales")
            print("💡 Considerar optimizar parámetros o estrategias")
    
    else:
        print("❌ Error en el sistema realista")

if __name__ == "__main__":
    main()