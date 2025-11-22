#!/usr/bin/env python3
"""
ULTIMATE SICAR + GRID HYBRID SYSTEM
Combinación de señales SICAR con Grid Trading para maximizar ROI
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GridManager:
    """Gestor de Grid Trading integrado con señales SICAR"""
    
    def __init__(self, symbol: str, initial_capital: float = 1000):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = []
        self.daily_pnl = 0
        self.current_day = None
        self.trading_paused = False
        self.max_positions = 3  # Máximo 3 posiciones por grid
        self.daily_drawdown_limit = 0.05  # 5% del capital
        
    def reset_daily_stats(self):
        """Reset estadísticas diarias"""
        self.daily_pnl = 0
        self.trading_paused = False
        
    def check_drawdown_limit(self) -> bool:
        """Verificar si se ha superado el límite de drawdown diario"""
        max_daily_loss = self.current_capital * self.daily_drawdown_limit
        return self.daily_pnl <= -max_daily_loss
        
    def can_open_position(self) -> bool:
        """Verificar si se puede abrir una nueva posición"""
        return (len(self.positions) < self.max_positions and 
                not self.trading_paused and 
                not self.check_drawdown_limit())

class UltimateSicarGridHybrid:
    """Sistema híbrido SICAR + Grid Trading"""
    
    def __init__(self):
        self.symbols = {
            'NAS100': {
                'leverage': 1.0,
                'stop_loss_pct': 0.015,  # 1.5%
                'take_profit_pct': 0.025,  # 2.5%
                'position_size_pct': 0.30,  # 30% por posición
                'commission': 0.0008,
                'signal_strength_threshold': 45,  # Más permisivo
                'confidence_threshold': 55,
                'grid_atr_multiplier': 1.5,
                'trading_hours': [(9.5, 16.0)],  # 9:30 AM - 4:00 PM EST
            },
            'SP500': {
                'leverage': 1.0,
                'stop_loss_pct': 0.015,
                'take_profit_pct': 0.025,
                'position_size_pct': 0.25,
                'commission': 0.0008,
                'signal_strength_threshold': 45,
                'confidence_threshold': 55,
                'grid_atr_multiplier': 1.5,
                'trading_hours': [(9.5, 16.0)],
            },
            'NASDAQ': {
                'leverage': 1.0,
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.03,
                'position_size_pct': 0.25,
                'commission': 0.001,
                'signal_strength_threshold': 40,
                'confidence_threshold': 50,
                'grid_atr_multiplier': 2.0,
                'trading_hours': [(9.5, 16.0)],
            },
            'GOLD': {
                'leverage': 1.0,
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.035,
                'position_size_pct': 0.20,
                'commission': 0.001,
                'signal_strength_threshold': 40,
                'confidence_threshold': 50,
                'grid_atr_multiplier': 1.8,
                'trading_hours': [(0, 24)],  # 24 horas
            },
            'CRUDE': {
                'leverage': 1.0,
                'stop_loss_pct': 0.025,
                'take_profit_pct': 0.04,
                'position_size_pct': 0.20,
                'commission': 0.0012,
                'signal_strength_threshold': 35,
                'confidence_threshold': 45,
                'grid_atr_multiplier': 2.2,
                'trading_hours': [(9.0, 14.5)],  # 9:00 AM - 2:30 PM EST
            },
            'BITCOIN': {
                'leverage': 1.0,
                'stop_loss_pct': 0.03,
                'take_profit_pct': 0.05,
                'position_size_pct': 0.15,
                'commission': 0.001,
                'signal_strength_threshold': 30,
                'confidence_threshold': 40,
                'grid_atr_multiplier': 2.5,
                'trading_hours': [(0, 24)],  # 24/7
            }
        }
        
        self.grid_managers = {}
        for symbol in self.symbols.keys():
            self.grid_managers[symbol] = GridManager(symbol)
            
    def generate_market_data(self, symbol: str, days: int = 730) -> pd.DataFrame:
        """Generar datos de mercado realistas con volatilidad apropiada"""
        
        # Configuraciones específicas por símbolo
        configs = {
            'NAS100': {'base_price': 15000, 'volatility': 0.015, 'trend': 0.0002},
            'SP500': {'base_price': 4500, 'volatility': 0.012, 'trend': 0.0001},
            'NASDAQ': {'base_price': 14000, 'volatility': 0.018, 'trend': 0.0003},
            'GOLD': {'base_price': 2000, 'volatility': 0.020, 'trend': 0.0001},
            'CRUDE': {'base_price': 80, 'volatility': 0.025, 'trend': 0.0002},
            'BITCOIN': {'base_price': 45000, 'volatility': 0.035, 'trend': 0.0005}
        }
        
        config = configs.get(symbol, configs['NAS100'])
        
        # Generar fechas
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generar precios con tendencia y volatilidad
        np.random.seed(42)
        n_points = len(dates)
        
        # Tendencia base
        trend = np.linspace(0, config['trend'] * n_points, n_points)
        
        # Ruido aleatorio con volatilidad
        noise = np.random.normal(0, config['volatility'], n_points)
        
        # Ciclos de mercado (simulando bull/bear markets)
        cycle = 0.1 * np.sin(np.linspace(0, 4 * np.pi, n_points))
        
        # Precio base
        log_returns = trend + noise + cycle
        prices = config['base_price'] * np.exp(np.cumsum(log_returns))
        
        # Crear OHLC realista
        data = []
        for i, price in enumerate(prices):
            # Volatilidad intradiaria
            daily_vol = config['volatility'] * 0.5
            high = price * (1 + np.random.uniform(0, daily_vol))
            low = price * (1 - np.random.uniform(0, daily_vol))
            open_price = price * (1 + np.random.uniform(-daily_vol/2, daily_vol/2))
            close = price
            
            # Volumen realista
            volume = np.random.uniform(100000, 500000)
            
            data.append({
                'Date': dates[i],
                'Open': open_price,
                'High': high,
                'Low': low,
                'Close': close,
                'Volume': volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('Date', inplace=True)
        return df
        
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular indicadores técnicos mejorados"""
        
        # EMAs para tendencia
        df['EMA_20'] = df['Close'].ewm(span=20).mean()
        df['EMA_50'] = df['Close'].ewm(span=50).mean()
        df['EMA_200'] = df['Close'].ewm(span=200).mean()
        
        # ATR para volatilidad y grid size
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['ATR'] = df['TR'].rolling(window=14).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        df['MACD_Histogram'] = df['MACD'] - df['MACD_Signal']
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        # Volume indicators
        df['Volume_SMA'] = df['Volume'].rolling(window=20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
        
        return df
        
    def generate_sicar_signals(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """Generar señales SICAR mejoradas"""
        
        config = self.symbols[symbol]
        
        # Condiciones de tendencia (EMA)
        df['Trend_Long'] = df['Close'] > df['EMA_50']
        df['Trend_Short'] = df['Close'] < df['EMA_50']
        df['Strong_Trend'] = abs(df['EMA_20'] - df['EMA_50']) / df['Close'] > 0.01
        
        # Condiciones de momentum
        df['RSI_Oversold'] = df['RSI'] < 30
        df['RSI_Overbought'] = df['RSI'] > 70
        df['RSI_Neutral'] = (df['RSI'] >= 40) & (df['RSI'] <= 60)
        
        # Condiciones MACD
        df['MACD_Bullish'] = (df['MACD'] > df['MACD_Signal']) & (df['MACD_Histogram'] > 0)
        df['MACD_Bearish'] = (df['MACD'] < df['MACD_Signal']) & (df['MACD_Histogram'] < 0)
        
        # Condiciones de volatilidad
        df['High_Volatility'] = df['ATR'] > df['ATR'].rolling(50).mean() * 1.2
        df['Normal_Volatility'] = df['ATR'] <= df['ATR'].rolling(50).mean() * 1.2
        
        # Condiciones de volumen
        df['High_Volume'] = df['Volume_Ratio'] > 1.5
        df['Normal_Volume'] = df['Volume_Ratio'] <= 1.5
        
        # Señales LONG mejoradas
        long_conditions = [
            df['Trend_Long'],
            df['MACD_Bullish'],
            df['RSI'] < 65,  # No sobrecomprado
            df['Close'] > df['BB_Lower'],  # Por encima de banda inferior
            df['Volume_Ratio'] > 0.8  # Volumen decente
        ]
        
        # Señales SHORT mejoradas
        short_conditions = [
            df['Trend_Short'],
            df['MACD_Bearish'],
            df['RSI'] > 35,  # No sobrevendido
            df['Close'] < df['BB_Upper'],  # Por debajo de banda superior
            df['Volume_Ratio'] > 0.8
        ]
        
        # Calcular fuerza de señal
        df['Long_Strength'] = sum(long_conditions) * 20  # 0-100%
        df['Short_Strength'] = sum(short_conditions) * 20
        
        # Calcular confianza basada en múltiples factores
        confidence_factors = [
            df['Strong_Trend'] * 20,
            df['High_Volume'] * 15,
            df['Normal_Volatility'] * 10,
            (abs(df['RSI'] - 50) / 50) * 25,  # Distancia del RSI de 50
            (abs(df['MACD_Histogram']) / df['ATR']) * 30
        ]
        
        df['Confidence'] = np.minimum(100, sum(confidence_factors))
        
        # Generar señales finales
        df['Signal_Long'] = (
            (df['Long_Strength'] >= config['signal_strength_threshold']) &
            (df['Confidence'] >= config['confidence_threshold'])
        )
        
        df['Signal_Short'] = (
            (df['Short_Strength'] >= config['signal_strength_threshold']) &
            (df['Confidence'] >= config['confidence_threshold'])
        )
        
        return df
        
    def is_trading_hours(self, timestamp: datetime, symbol: str) -> bool:
        """Verificar si está en horario de trading"""
        config = self.symbols[symbol]
        current_hour = timestamp.hour + timestamp.minute / 60.0
        
        for start_hour, end_hour in config['trading_hours']:
            if start_hour <= current_hour <= end_hour:
                return True
        return False
        
    def calculate_grid_size(self, df: pd.DataFrame, symbol: str, index: int) -> float:
        """Calcular tamaño de grid dinámico basado en ATR"""
        config = self.symbols[symbol]
        atr = df.iloc[index]['ATR']
        return atr * config['grid_atr_multiplier']
        
    def backtest_grid_hybrid(self, symbol: str) -> Dict:
        """Backtesting del sistema híbrido SICAR + Grid"""
        
        logger.info(f"🔄 Iniciando backtest híbrido para {symbol}")
        
        # Generar datos
        df = self.generate_market_data(symbol)
        df = self.calculate_technical_indicators(df)
        df = self.generate_sicar_signals(df, symbol)
        
        # Configuración
        config = self.symbols[symbol]
        grid_manager = self.grid_managers[symbol]
        
        # Variables de trading
        trades = []
        equity_curve = []
        current_capital = 1000
        
        for i in range(100, len(df)):  # Empezar después de indicadores
            current_date = df.index[i]
            current_price = df.iloc[i]['Close']
            
            # Reset diario
            if grid_manager.current_day != current_date.date():
                grid_manager.current_day = current_date.date()
                grid_manager.reset_daily_stats()
            
            # Verificar horario de trading
            if not self.is_trading_hours(current_date, symbol):
                continue
                
            # Verificar límite de drawdown
            if grid_manager.check_drawdown_limit():
                continue
            
            # Procesar señales SICAR
            signal_long = df.iloc[i]['Signal_Long']
            signal_short = df.iloc[i]['Signal_Short']
            
            if (signal_long or signal_short) and grid_manager.can_open_position():
                
                # Calcular grid size dinámico
                grid_size = self.calculate_grid_size(df, symbol, i)
                
                # Determinar dirección
                is_long = signal_long
                
                # Calcular posición
                position_size = current_capital * config['position_size_pct']
                
                # Precios de entrada con grid
                entry_prices = []
                base_price = current_price
                
                # Grid de entradas (máximo 3 niveles)
                for level in range(min(3, grid_manager.max_positions - len(grid_manager.positions))):
                    if is_long:
                        entry_price = base_price - (grid_size * level * 0.5)  # Entradas escalonadas hacia abajo
                    else:
                        entry_price = base_price + (grid_size * level * 0.5)  # Entradas escalonadas hacia arriba
                    entry_prices.append(entry_price)
                
                # Simular entradas de grid
                for entry_price in entry_prices:
                    if grid_manager.can_open_position():
                        
                        # Calcular stop loss y take profit
                        if is_long:
                            stop_loss = entry_price * (1 - config['stop_loss_pct'])
                            take_profit = entry_price * (1 + config['take_profit_pct'])
                        else:
                            stop_loss = entry_price * (1 + config['stop_loss_pct'])
                            take_profit = entry_price * (1 - config['take_profit_pct'])
                        
                        # Crear posición
                        position = {
                            'entry_date': current_date,
                            'entry_price': entry_price,
                            'position_size': position_size / len(entry_prices),  # Dividir entre niveles
                            'is_long': is_long,
                            'stop_loss': stop_loss,
                            'take_profit': take_profit,
                            'status': 'open'
                        }
                        
                        grid_manager.positions.append(position)
            
            # Gestionar posiciones abiertas
            for position in grid_manager.positions[:]:  # Copia para modificar durante iteración
                if position['status'] == 'open':
                    
                    # Verificar stop loss
                    if ((position['is_long'] and current_price <= position['stop_loss']) or
                        (not position['is_long'] and current_price >= position['stop_loss'])):
                        
                        # Cerrar por stop loss
                        if position['is_long']:
                            pnl = (position['stop_loss'] - position['entry_price']) * (position['position_size'] / position['entry_price'])
                        else:
                            pnl = (position['entry_price'] - position['stop_loss']) * (position['position_size'] / position['entry_price'])
                        
                        # Aplicar comisión
                        commission = position['position_size'] * config['commission'] * 2  # Entrada + salida
                        pnl -= commission
                        
                        current_capital += pnl
                        grid_manager.daily_pnl += pnl
                        
                        # Registrar trade
                        trade = {
                            'Symbol': symbol,
                            'Entry_Date': position['entry_date'],
                            'Exit_Date': current_date,
                            'Entry_Price': position['entry_price'],
                            'Exit_Price': position['stop_loss'],
                            'Position_Size': position['position_size'],
                            'Is_Long': position['is_long'],
                            'PnL': pnl,
                            'Exit_Reason': 'Stop Loss'
                        }
                        trades.append(trade)
                        
                        position['status'] = 'closed'
                        grid_manager.positions.remove(position)
                    
                    # Verificar take profit
                    elif ((position['is_long'] and current_price >= position['take_profit']) or
                          (not position['is_long'] and current_price <= position['take_profit'])):
                        
                        # Cerrar por take profit
                        if position['is_long']:
                            pnl = (position['take_profit'] - position['entry_price']) * (position['position_size'] / position['entry_price'])
                        else:
                            pnl = (position['entry_price'] - position['take_profit']) * (position['position_size'] / position['entry_price'])
                        
                        # Aplicar comisión
                        commission = position['position_size'] * config['commission'] * 2
                        pnl -= commission
                        
                        current_capital += pnl
                        grid_manager.daily_pnl += pnl
                        
                        # Registrar trade
                        trade = {
                            'Symbol': symbol,
                            'Entry_Date': position['entry_date'],
                            'Exit_Date': current_date,
                            'Entry_Price': position['entry_price'],
                            'Exit_Price': position['take_profit'],
                            'Position_Size': position['position_size'],
                            'Is_Long': position['is_long'],
                            'PnL': pnl,
                            'Exit_Reason': 'Take Profit'
                        }
                        trades.append(trade)
                        
                        position['status'] = 'closed'
                        grid_manager.positions.remove(position)
            
            # Registrar equity
            equity_curve.append({
                'Date': current_date,
                'Capital': current_capital
            })
        
        # Calcular métricas
        if trades:
            trades_df = pd.DataFrame(trades)
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df['PnL'] > 0])
            losing_trades = len(trades_df[trades_df['PnL'] <= 0])
            
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            total_pnl = trades_df['PnL'].sum()
            avg_win = trades_df[trades_df['PnL'] > 0]['PnL'].mean() if winning_trades > 0 else 0
            avg_loss = trades_df[trades_df['PnL'] <= 0]['PnL'].mean() if losing_trades > 0 else 0
            profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if losing_trades > 0 and avg_loss != 0 else float('inf')
            
            # ROI
            total_roi = ((current_capital - 1000) / 1000) * 100
            days_traded = (df.index[-1] - df.index[100]).days
            monthly_roi = (total_roi / days_traded) * 30 if days_traded > 0 else 0
            
            # Drawdown
            equity_df = pd.DataFrame(equity_curve)
            if not equity_df.empty:
                equity_df['Peak'] = equity_df['Capital'].cummax()
                equity_df['Drawdown'] = (equity_df['Capital'] - equity_df['Peak']) / equity_df['Peak'] * 100
                max_drawdown = equity_df['Drawdown'].min()
            else:
                max_drawdown = 0
                
        else:
            total_trades = winning_trades = losing_trades = 0
            win_rate = total_pnl = monthly_roi = max_drawdown = profit_factor = 0
            avg_win = avg_loss = 0
        
        return {
            'symbol': symbol,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'monthly_roi': monthly_roi,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'final_capital': current_capital,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'trades_per_month': (total_trades / (days_traded / 30)) if 'days_traded' in locals() and days_traded > 0 else 0
        }
        
    def run_complete_analysis(self):
        """Ejecutar análisis completo del sistema híbrido"""
        
        logger.info("🚀 INICIANDO ANÁLISIS ULTIMATE SICAR + GRID HYBRID")
        logger.info("=" * 80)
        
        results = {}
        total_capital = 0
        total_trades = 0
        total_winning = 0
        
        # Analizar cada símbolo
        for symbol in self.symbols.keys():
            result = self.backtest_grid_hybrid(symbol)
            results[symbol] = result
            
            total_capital += result['final_capital']
            total_trades += result['total_trades']
            total_winning += result['winning_trades']
            
            # Mostrar resultados individuales
            logger.info(f"\n📊 {symbol}:")
            logger.info(f"   💰 ROI Mensual: {result['monthly_roi']:.2f}%")
            logger.info(f"   🎯 Trades: {result['total_trades']} (✅{result['winning_trades']} | ❌{result['losing_trades']})")
            logger.info(f"   🏆 Win Rate: {result['win_rate']:.1f}%")
            logger.info(f"   💵 Capital Final: ${result['final_capital']:.2f}")
            logger.info(f"   📊 Profit Factor: {result['profit_factor']:.2f}")
            logger.info(f"   📉 Max Drawdown: {result['max_drawdown']:.2f}%")
            logger.info(f"   🔄 Trades/Mes: {result['trades_per_month']:.1f}")
        
        # Resumen general
        overall_roi = ((total_capital - len(self.symbols) * 1000) / (len(self.symbols) * 1000)) * 100
        monthly_roi = overall_roi / 24  # 2 años de datos
        overall_win_rate = (total_winning / total_trades * 100) if total_trades > 0 else 0
        
        logger.info("\n" + "=" * 80)
        logger.info("🎉 RESUMEN GENERAL HÍBRIDO:")
        logger.info("=" * 80)
        logger.info(f"💰 ROI Mensual Promedio: {monthly_roi:.2f}%")
        logger.info(f"🎯 Total Trades: {total_trades}")
        logger.info(f"🏆 Win Rate General: {overall_win_rate:.1f}%")
        logger.info(f"💵 Capital Total Final: ${total_capital:.2f}")
        logger.info(f"📈 Capital Inicial Total: ${len(self.symbols) * 1000:.2f}")
        
        # Evaluación del objetivo
        target_roi = 10.0
        logger.info(f"\n🎯 EVALUACIÓN DEL OBJETIVO ({target_roi}% ROI mensual):")
        if monthly_roi >= target_roi:
            logger.info(f"✅ OBJETIVO ALCANZADO! ROI: {monthly_roi:.2f}%")
        else:
            logger.info(f"❌ Objetivo no alcanzado. ROI: {monthly_roi:.2f}%")
            logger.info(f"📊 Diferencia: {target_roi - monthly_roi:.2f}% puntos")
        
        # Recomendaciones
        logger.info(f"\n💡 RECOMENDACIONES PARA MEJORAR:")
        logger.info("   • Aumentar frecuencia de señales (reducir thresholds)")
        logger.info("   • Implementar trailing stops más agresivos")
        logger.info("   • Considerar apalancamiento controlado 2:1")
        logger.info("   • Añadir más símbolos volátiles (crypto)")
        logger.info("   • Optimizar horarios de trading por símbolo")
        
        return results

if __name__ == "__main__":
    # Ejecutar sistema híbrido
    hybrid_system = UltimateSicarGridHybrid()
    results = hybrid_system.run_complete_analysis()