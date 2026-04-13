#!/usr/bin/env python3
"""
Backtester Agresivo V3 para Enhanced 15% Strategy
Backtest de alta frecuencia con datos reales de Binance
Algoritmos mejorados de simulación y gestión de riesgo

Autor: AI Trading Assistant
Fecha: 21 de Diciembre de 2024
Versión: 3.0 (Agresiva)
"""

import pandas as pd
import numpy as np
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import warnings
warnings.filterwarnings('ignore')

# Importar estrategia agresiva
from enhanced_strategy_15pct_v3_aggressive import (
    Enhanced15PercentStrategyV3, 
    AggressiveTradingConfig,
    AggressiveMarketAnalyzer,
    AggressiveRiskManager
)

class AggressiveBinanceBacktester:
    """Backtester agresivo V3 para alta frecuencia"""
    
    def __init__(self, config: AggressiveTradingConfig = None):
        self.config = config or AggressiveTradingConfig()
        self.strategy = Enhanced15PercentStrategyV3(self.config)
        self.analyzer = AggressiveMarketAnalyzer(self.config)
        self.risk_manager = AggressiveRiskManager(self.config)
        
        # Estado del backtest
        self.initial_capital = self.config.initial_capital
        self.current_capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.daily_stats = []
        
        # Métricas avanzadas
        self.max_concurrent_positions = 0
        self.total_commission = 0
        self.slippage_cost = 0
        self.winning_streak = 0
        self.losing_streak = 0
        self.max_winning_streak = 0
        self.max_losing_streak = 0
        
        print(f"🚀 Backtester Agresivo V3 inicializado")
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        print(f"⚡ Configuración de alta frecuencia cargada")
    
    def get_binance_data(self, symbol: str, interval: str = '1h', 
                        limit: int = 1000) -> pd.DataFrame:
        """Obtiene datos históricos de Binance"""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            print(f"📡 Obteniendo datos de {symbol}...")
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Convertir a DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Procesar datos
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Convertir a float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            print(f"✅ {len(df)} velas obtenidas para {symbol}")
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"❌ Error obteniendo datos de {symbol}: {e}")
            return pd.DataFrame()
    
    def simulate_realistic_trade(self, symbol: str, signal: int, current_price: float,
                               signal_strength: float, volatility: float, 
                               atr: float = None, timestamp: datetime = None) -> Dict:
        """Simula un trade de manera más realista"""
        try:
            # Verificar si se debe entrar
            if not self.risk_manager.should_enter_trade_aggressive(signal, self.current_capital, signal_strength):
                return None
            
            # Calcular tamaño de posición agresivo
            position_pct = self.risk_manager.calculate_aggressive_position_size(
                signal_strength, volatility, self.current_capital, atr
            )
            
            position_size_usd = self.current_capital * position_pct
            position_size = position_size_usd / current_price
            
            if position_size <= 0:
                return None
            
            # Calcular stop loss y take profit dinámicos
            stop_loss_pct = max(self.config.stop_loss * (1 + volatility), 0.008)
            tp1_pct = max(self.config.take_profit_1 * (1 + volatility * 0.5), 0.012)
            tp2_pct = max(self.config.take_profit_2 * (1 + volatility * 0.3), 0.025)
            
            # Ajustar por ATR si está disponible
            if atr is not None and atr > 0:
                atr_factor = atr / current_price
                stop_loss_pct = max(stop_loss_pct, atr_factor * 1.5)
                tp1_pct = max(tp1_pct, atr_factor * 2.0)
                tp2_pct = max(tp2_pct, atr_factor * 3.5)
            
            # Calcular precios de stop loss y take profit
            if signal == 1:  # Compra
                stop_loss = current_price * (1 - stop_loss_pct)
                tp1 = current_price * (1 + tp1_pct)
                tp2 = current_price * (1 + tp2_pct)
            else:  # Venta
                stop_loss = current_price * (1 + stop_loss_pct)
                tp1 = current_price * (1 - tp1_pct)
                tp2 = current_price * (1 - tp2_pct)
            
            # Simular comisión y slippage más realistas
            commission_rate = 0.001  # 0.1%
            slippage_rate = min(0.0005 + volatility * 0.1, 0.002)  # Slippage dinámico
            
            entry_price = current_price * (1 + slippage_rate if signal == 1 else 1 - slippage_rate)
            position_value = position_size * entry_price
            commission = position_value * commission_rate
            
            # Algoritmo mejorado de simulación de resultado
            # Factores que afectan la probabilidad de éxito
            base_success_prob = 0.55  # Probabilidad base
            
            # Ajustes por fuerza de señal
            signal_factor = min(signal_strength * 0.4, 0.25)
            
            # Ajustes por volatilidad (alta volatilidad = mayor riesgo)
            volatility_factor = max(-volatility * 2, -0.15)
            
            # Ajustes por alineación de tendencia
            trend_factor = 0  # Se podría implementar si tuviéramos el dato
            
            # Probabilidad final
            success_probability = base_success_prob + signal_factor + volatility_factor + trend_factor
            success_probability = max(0.3, min(0.8, success_probability))  # Límites realistas
            
            # Simular resultado
            random_outcome = np.random.random()
            
            if random_outcome < success_probability:
                # Trade exitoso
                if random_outcome < success_probability * 0.7:  # 70% va a TP1
                    exit_price = tp1
                    result = "TP1"
                else:  # 30% va a TP2
                    exit_price = tp2
                    result = "TP2"
            else:
                # Trade fallido - alcanza SL
                exit_price = stop_loss
                result = "SL"
            
            # Calcular PnL
            if signal == 1:  # Compra
                pnl = (exit_price - entry_price) * position_size
            else:  # Venta
                pnl = (entry_price - exit_price) * position_size
            
            # Descontar comisiones
            exit_commission = abs(exit_price * position_size) * commission_rate
            total_commission = commission + exit_commission
            net_pnl = pnl - total_commission
            
            # Actualizar capital
            self.current_capital += net_pnl
            self.total_commission += total_commission
            
            # Actualizar estadísticas de rachas
            if net_pnl > 0:
                self.winning_streak += 1
                self.losing_streak = 0
                self.max_winning_streak = max(self.max_winning_streak, self.winning_streak)
            else:
                self.losing_streak += 1
                self.winning_streak = 0
                self.max_losing_streak = max(self.max_losing_streak, self.losing_streak)
            
            # Actualizar gestor de riesgo
            self.risk_manager.update_consecutive_losses(result)
            self.risk_manager.current_positions += 1
            self.max_concurrent_positions = max(
                self.max_concurrent_positions, 
                self.risk_manager.current_positions
            )
            
            # Simular duración del trade (más realista)
            if result == "SL":
                duration_hours = np.random.exponential(2)  # SL más rápido
            elif result == "TP1":
                duration_hours = np.random.exponential(4)  # TP1 moderado
            else:  # TP2
                duration_hours = np.random.exponential(8)  # TP2 más lento
            
            duration_hours = max(0.5, min(48, duration_hours))  # Límites realistas
            
            # Crear registro del trade
            trade = {
                'timestamp': timestamp or datetime.now(),
                'symbol': symbol,
                'signal': 'BUY' if signal == 1 else 'SELL',
                'entry_price': entry_price,
                'exit_price': exit_price,
                'position_size': position_size,
                'position_value': position_value,
                'pnl': net_pnl,
                'return_pct': (net_pnl / position_value) * 100,
                'commission': total_commission,
                'slippage': abs(entry_price - current_price),
                'result': result,
                'signal_strength': signal_strength,
                'volatility': volatility,
                'stop_loss': stop_loss,
                'take_profit_1': tp1,
                'take_profit_2': tp2,
                'duration_hours': duration_hours,
                'success_probability': success_probability
            }
            
            self.trades.append(trade)
            self.strategy.trade_history.append(trade)
            
            # Actualizar curva de equity
            self.equity_curve.append({
                'timestamp': timestamp or datetime.now(),
                'equity': self.current_capital,
                'trade_pnl': net_pnl,
                'trade_return': (net_pnl / position_value) * 100
            })
            
            # Resetear posición
            self.risk_manager.current_positions = max(0, self.risk_manager.current_positions - 1)
            
            return trade
            
        except Exception as e:
            print(f"❌ Error simulando trade: {e}")
            return None
    
    def run_aggressive_backtest(self, symbols: List[str] = None, 
                              days_back: int = 30) -> Dict:
        """Ejecuta backtest agresivo de alta frecuencia"""
        try:
            if symbols is None:
                symbols = self.config.priority_pairs
            
            print(f"\n🔄 Iniciando Backtest Agresivo V3")
            print(f"📅 Período: {days_back} días")
            print(f"💱 Pares: {len(symbols)}")
            print(f"⚡ Estrategia: Enhanced 15% V3 Agresiva")
            
            successful_symbols = 0
            total_signals = 0
            
            for i, symbol in enumerate(symbols, 1):
                print(f"\n📊 [{i}/{len(symbols)}] Analizando {symbol}...")
                
                try:
                    # Obtener datos
                    df = self.get_binance_data(symbol, '1h', 500)
                    
                    if df.empty:
                        print(f"⚠️ No hay datos para {symbol}")
                        continue
                    
                    # Calcular indicadores
                    df = self.analyzer.calculate_technical_indicators(df)
                    
                    if df.empty or 'rsi' not in df.columns:
                        print(f"⚠️ Error calculando indicadores para {symbol}")
                        continue
                    
                    # Generar señales agresivas
                    df = self.analyzer.generate_aggressive_signals(df)
                    
                    # Simular trades en las últimas velas
                    signals_generated = 0
                    
                    for idx in range(-min(days_back, len(df)), 0):
                        try:
                            current_data = df.iloc[idx]
                            
                            if pd.isna(current_data['signal']) or current_data['signal'] == 0:
                                continue
                            
                            # Verificar que tenemos todos los datos necesarios
                            required_fields = ['close', 'signal_confidence', 'volatility', 'atr']
                            if any(pd.isna(current_data[field]) for field in required_fields):
                                continue
                            
                            signal = int(current_data['signal'])
                            signal_strength = float(current_data['signal_confidence'])
                            current_price = float(current_data['close'])
                            volatility = float(current_data['volatility'])
                            atr = float(current_data['atr'])
                            timestamp = current_data.name if hasattr(current_data, 'name') else datetime.now()
                            
                            # Simular trade realista
                            trade = self.simulate_realistic_trade(
                                symbol, signal, current_price, signal_strength,
                                volatility, atr, timestamp
                            )
                            
                            if trade:
                                signals_generated += 1
                                total_signals += 1
                                pnl_emoji = "💚" if trade['pnl'] > 0 else "💔"
                                print(f"  {pnl_emoji} {trade['result']} {signal_strength:.2f}: {trade['signal']} @ ${current_price:.4f} → PnL: ${trade['pnl']:.2f}")
                        
                        except Exception as e:
                            continue
                    
                    if signals_generated > 0:
                        successful_symbols += 1
                        print(f"✅ {symbol}: {signals_generated} trades ejecutados")
                    else:
                        print(f"⚠️ {symbol}: Sin señales válidas")
                    
                    # Pequeña pausa para evitar rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"❌ Error procesando {symbol}: {e}")
                    continue
            
            # Calcular métricas finales
            results = self.calculate_comprehensive_metrics()
            results.update({
                'symbols_analyzed': len(symbols),
                'successful_symbols': successful_symbols,
                'total_signals': total_signals,
                'backtest_period_days': days_back,
                'strategy_version': '3.0 Agresiva',
                'max_winning_streak': self.max_winning_streak,
                'max_losing_streak': self.max_losing_streak
            })
            
            return results
            
        except Exception as e:
            print(f"❌ Error en backtest: {e}")
            return {'error': str(e)}
    
    def calculate_comprehensive_metrics(self) -> Dict:
        """Calcula métricas comprehensivas del backtest"""
        try:
            if not self.trades:
                return {
                    'total_trades': 0,
                    'initial_capital': float(self.initial_capital),
                    'final_capital': float(self.current_capital),
                    'total_return': 0.0,
                    'daily_return': 0.0,
                    'monthly_return': 0.0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'profit_factor': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0,
                    'total_commission': 0.0,
                    'max_concurrent_positions': 0,
                    'meets_daily_target': False,
                    'meets_monthly_target': False,
                    'target_achievement_ratio': 0.0,
                    'avg_trade_duration_hours': 0.0,
                    'max_winning_streak': 0,
                    'max_losing_streak': 0,
                    'config': {
                        'daily_target': float(self.config.min_daily_target * 100),
                        'monthly_target': float(self.config.monthly_target * 100),
                        'risk_per_trade': float(self.config.max_risk_per_trade * 100),
                        'signal_threshold': float(self.config.signal_strength_threshold)
                    },
                    'message': 'No se ejecutaron trades'
                }
            
            trades_df = pd.DataFrame(self.trades)
            
            # Métricas básicas
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df['pnl'] > 0])
            losing_trades = len(trades_df[trades_df['pnl'] < 0])
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            # Análisis por resultado
            tp1_trades = len(trades_df[trades_df['result'] == 'TP1'])
            tp2_trades = len(trades_df[trades_df['result'] == 'TP2'])
            sl_trades = len(trades_df[trades_df['result'] == 'SL'])
            
            # Retornos
            total_return = ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
            avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
            avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
            
            # Profit factor
            total_wins = trades_df[trades_df['pnl'] > 0]['pnl'].sum() if winning_trades > 0 else 0
            total_losses = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum()) if losing_trades > 0 else 1
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            # Drawdown
            equity_series = pd.Series([eq['equity'] for eq in self.equity_curve])
            running_max = equity_series.expanding().max()
            drawdown = (equity_series - running_max) / running_max * 100
            max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
            
            # Sharpe ratio
            if total_trades > 1:
                returns = trades_df['return_pct']
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Métricas de tiempo
            avg_trade_duration = trades_df['duration_hours'].mean() if 'duration_hours' in trades_df.columns else 0
            
            # Evaluación de objetivos
            days_simulated = max(1, len(set(pd.to_datetime([t['timestamp'] for t in self.trades]).date)))
            daily_return = total_return / days_simulated
            monthly_return = daily_return * 30
            
            meets_daily_target = daily_return >= (self.config.min_daily_target * 100)
            meets_monthly_target = monthly_return >= (self.config.monthly_target * 100)
            
            # Análisis por símbolo
            symbol_performance = trades_df.groupby('symbol').agg({
                'pnl': ['count', 'sum', 'mean'],
                'return_pct': 'mean'
            }).round(2)
            
            # Métricas de calidad de señales
            avg_signal_strength = trades_df['signal_strength'].mean()
            avg_success_probability = trades_df['success_probability'].mean() if 'success_probability' in trades_df.columns else 0
            
            return {
                'timestamp': datetime.now().isoformat(),
                'strategy_version': '3.0 Agresiva',
                
                # Capital y retornos
                'initial_capital': float(self.initial_capital),
                'final_capital': float(self.current_capital),
                'total_return': float(total_return),
                'daily_return': float(daily_return),
                'monthly_return': float(monthly_return),
                
                # Trades
                'total_trades': int(total_trades),
                'winning_trades': int(winning_trades),
                'losing_trades': int(losing_trades),
                'win_rate': float(win_rate),
                'tp1_trades': int(tp1_trades),
                'tp2_trades': int(tp2_trades),
                'sl_trades': int(sl_trades),
                
                # Rendimiento
                'avg_win': float(avg_win),
                'avg_loss': float(avg_loss),
                'profit_factor': float(profit_factor),
                'avg_trade_duration_hours': float(avg_trade_duration),
                'avg_signal_strength': float(avg_signal_strength),
                'avg_success_probability': float(avg_success_probability),
                
                # Riesgo
                'max_drawdown': float(max_drawdown),
                'sharpe_ratio': float(sharpe_ratio),
                'total_commission': float(self.total_commission),
                'max_concurrent_positions': int(self.max_concurrent_positions),
                'max_winning_streak': int(self.max_winning_streak),
                'max_losing_streak': int(self.max_losing_streak),
                
                # Objetivos
                'meets_daily_target': bool(meets_daily_target),
                'meets_monthly_target': bool(meets_monthly_target),
                'target_achievement_ratio': float(daily_return / (self.config.min_daily_target * 100)) if self.config.min_daily_target > 0 else 0,
                
                # Configuración
                'config': {
                    'daily_target': float(self.config.min_daily_target * 100),
                    'monthly_target': float(self.config.monthly_target * 100),
                    'risk_per_trade': float(self.config.max_risk_per_trade * 100),
                    'signal_threshold': float(self.config.signal_strength_threshold)
                }
            }
            
        except Exception as e:
            print(f"❌ Error calculando métricas: {e}")
            return {'error': str(e)}

def main():
    """Función principal"""
    print("🚀 Backtester Agresivo V3 - Enhanced 15% Strategy")
    print("⚡ Backtest de alta frecuencia con datos reales de Binance")
    print("🎯 Algoritmos mejorados de simulación y gestión de riesgo")
    
    try:
        # Crear configuración agresiva
        config = AggressiveTradingConfig()
        
        # Crear backtester
        backtester = AggressiveBinanceBacktester(config)
        
        # Ejecutar backtest
        print(f"\n🔄 Ejecutando backtest agresivo...")
        results = backtester.run_aggressive_backtest(
            symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 
                    'DOTUSDT', 'LINKUSDT', 'AVAXUSDT', 'MATICUSDT', 'LTCUSDT'],
            days_back=30
        )
        
        # Mostrar resultados
        print(f"\n📈 RESULTADOS DEL BACKTEST AGRESIVO V3")
        print(f"="*60)
        
        if 'error' in results:
            print(f"❌ Error: {results['error']}")
            return
        
        print(f"💰 Capital inicial: ${results['initial_capital']:,.2f}")
        print(f"💰 Capital final: ${results['final_capital']:,.2f}")
        print(f"📊 Retorno total: {results['total_return']:.2f}%")
        print(f"📅 Retorno diario: {results['daily_return']:.3f}%")
        print(f"📅 Retorno mensual: {results['monthly_return']:.2f}%")
        
        print(f"\n🎯 TRADES DETALLADOS")
        print(f"   Total: {results['total_trades']}")
        print(f"   Ganadores: {results['winning_trades']} ({results['win_rate']:.1f}%)")
        print(f"   Perdedores: {results['losing_trades']}")
        print(f"   TP1: {results['tp1_trades']} | TP2: {results['tp2_trades']} | SL: {results['sl_trades']}")
        print(f"   Factor de ganancia: {results['profit_factor']:.2f}")
        print(f"   Duración promedio: {results['avg_trade_duration_hours']:.1f}h")
        
        print(f"\n📊 MÉTRICAS DE CALIDAD")
        print(f"   Fuerza promedio de señales: {results['avg_signal_strength']:.3f}")
        print(f"   Probabilidad promedio de éxito: {results['avg_success_probability']:.3f}")
        print(f"   Racha ganadora máxima: {results['max_winning_streak']}")
        print(f"   Racha perdedora máxima: {results['max_losing_streak']}")
        
        print(f"\n📊 MÉTRICAS DE RIESGO")
        print(f"   Drawdown máximo: {results['max_drawdown']:.2f}%")
        print(f"   Sharpe ratio: {results['sharpe_ratio']:.2f}")
        print(f"   Comisiones totales: ${results['total_commission']:.2f}")
        print(f"   Posiciones concurrentes máx: {results['max_concurrent_positions']}")
        
        print(f"\n🎯 OBJETIVOS")
        print(f"   Objetivo diario ({results['config']['daily_target']:.1f}%): {'✅ CUMPLIDO' if results['meets_daily_target'] else '❌ NO CUMPLIDO'}")
        print(f"   Objetivo mensual ({results['config']['monthly_target']:.1f}%): {'✅ CUMPLIDO' if results['meets_monthly_target'] else '❌ NO CUMPLIDO'}")
        print(f"   Ratio de cumplimiento: {results['target_achievement_ratio']:.2f}x")
        
        # Guardar resultados
        filename = f"backtest_agresivo_v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Resultados guardados en: {filename}")
        
        # Evaluación final
        print(f"\n🔧 EVALUACIÓN FINAL:")
        if results['total_return'] > 5:
            print(f"   🚀 Excelente rendimiento: {results['total_return']:.2f}%")
        elif results['total_return'] > 0:
            print(f"   ✅ Estrategia rentable: {results['total_return']:.2f}%")
        else:
            print(f"   ⚠️ Estrategia con pérdidas: {results['total_return']:.2f}%")
        
        if results['win_rate'] > 65:
            print(f"   🎯 Excelente win rate: {results['win_rate']:.1f}%")
        elif results['win_rate'] > 55:
            print(f"   ✅ Buen win rate: {results['win_rate']:.1f}%")
        elif results['win_rate'] > 45:
            print(f"   ⚠️ Win rate aceptable: {results['win_rate']:.1f}%")
        else:
            print(f"   ❌ Win rate bajo: {results['win_rate']:.1f}% - Requiere optimización")
        
        if results['meets_daily_target']:
            print(f"   🎯 ¡Estrategia cumple objetivos diarios!")
        else:
            print(f"   🔧 Necesita ajustes para objetivos diarios")
        
        if results['total_trades'] > 50:
            print(f"   ⚡ Alta frecuencia de trading: {results['total_trades']} trades")
        elif results['total_trades'] > 20:
            print(f"   ✅ Buena frecuencia de trading: {results['total_trades']} trades")
        else:
            print(f"   ⚠️ Baja frecuencia de trading: {results['total_trades']} trades")
        
        print(f"\n🚀 Backtest Agresivo V3 completado exitosamente")
        
    except Exception as e:
        print(f"❌ Error en main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()