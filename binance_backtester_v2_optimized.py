#!/usr/bin/env python3
"""
Backtester Optimizado V2 para Enhanced 15% Strategy
Backtest con datos reales de Binance usando estrategia optimizada
Incluye análisis avanzado y métricas mejoradas

Autor: AI Trading Assistant
Fecha: 21 de Diciembre de 2024
Versión: 2.0 (Optimizada)
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

# Importar estrategia optimizada
from enhanced_strategy_15pct_v2_optimized import (
    Enhanced15PercentStrategyV2, 
    OptimizedTradingConfig,
    OptimizedMarketAnalyzer,
    OptimizedRiskManager
)

class OptimizedBinanceBacktester:
    """Backtester optimizado V2 para datos de Binance"""
    
    def __init__(self, config: OptimizedTradingConfig = None):
        self.config = config or OptimizedTradingConfig()
        self.strategy = Enhanced15PercentStrategyV2(self.config)
        self.analyzer = OptimizedMarketAnalyzer(self.config)
        self.risk_manager = OptimizedRiskManager(self.config)
        
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
        
        print(f"🚀 Backtester Optimizado V2 inicializado")
        print(f"💰 Capital inicial: ${self.initial_capital:,.2f}")
        print(f"📊 Configuración optimizada cargada")
    
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
    
    def calculate_position_size(self, signal_strength: float, current_price: float,
                              volatility: float, atr: float = None) -> float:
        """Calcula tamaño de posición optimizado"""
        try:
            # Usar el gestor de riesgo optimizado
            position_pct = self.risk_manager.calculate_dynamic_position_size(
                signal_strength, volatility, self.current_capital, atr
            )
            
            # Convertir a cantidad en USD
            position_size_usd = self.current_capital * position_pct
            
            # Convertir a cantidad de activo
            position_size = position_size_usd / current_price
            
            return position_size
            
        except Exception as e:
            print(f"❌ Error calculando tamaño de posición: {e}")
            return 0
    
    def simulate_trade_v2(self, symbol: str, signal: int, current_price: float,
                         signal_strength: float, volatility: float, 
                         atr: float = None, timestamp: datetime = None) -> Dict:
        """Simula un trade con gestión optimizada"""
        try:
            # Verificar si se debe entrar
            if not self.risk_manager.should_enter_trade(signal, self.current_capital, signal_strength):
                return None
            
            # Calcular tamaño de posición
            position_size = self.calculate_position_size(
                signal_strength, current_price, volatility, atr
            )
            
            if position_size <= 0:
                return None
            
            # Calcular stop loss y take profit dinámicos
            stop_loss = self.risk_manager.calculate_dynamic_stop_loss(
                current_price, signal, volatility, atr
            )
            
            tp1, tp2 = self.risk_manager.calculate_dynamic_take_profit(
                current_price, signal, volatility, atr
            )
            
            # Simular comisión y slippage
            commission_rate = 0.001  # 0.1%
            slippage_rate = 0.0005   # 0.05%
            
            entry_price = current_price * (1 + slippage_rate if signal == 1 else 1 - slippage_rate)
            position_value = position_size * entry_price
            commission = position_value * commission_rate
            
            # Simular resultado del trade (simplificado)
            # En un backtest real, esto se haría tick por tick
            success_probability = min(signal_strength * 1.5, 0.8)  # Máximo 80%
            
            if np.random.random() < success_probability:
                # Trade exitoso - alcanza TP1
                exit_price = tp1
                result = "TP1"
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
            
            # Actualizar posiciones concurrentes
            self.risk_manager.current_positions += 1
            self.max_concurrent_positions = max(
                self.max_concurrent_positions, 
                self.risk_manager.current_positions
            )
            
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
                'result': result,
                'signal_strength': signal_strength,
                'volatility': volatility,
                'stop_loss': stop_loss,
                'take_profit_1': tp1,
                'take_profit_2': tp2,
                'duration_hours': np.random.randint(1, 24)  # Simulado
            }
            
            self.trades.append(trade)
            self.strategy.trade_history.append(trade)
            
            # Actualizar curva de equity
            self.equity_curve.append({
                'timestamp': timestamp or datetime.now(),
                'equity': self.current_capital,
                'trade_pnl': net_pnl
            })
            
            # Resetear posición
            self.risk_manager.current_positions = max(0, self.risk_manager.current_positions - 1)
            
            return trade
            
        except Exception as e:
            print(f"❌ Error simulando trade: {e}")
            return None
    
    def run_backtest_v2(self, symbols: List[str] = None, 
                       days_back: int = 30) -> Dict:
        """Ejecuta backtest optimizado V2"""
        try:
            if symbols is None:
                symbols = self.config.priority_pairs
            
            print(f"\n🔄 Iniciando Backtest Optimizado V2")
            print(f"📅 Período: {days_back} días")
            print(f"💱 Pares: {len(symbols)}")
            print(f"⚙️ Estrategia: Enhanced 15% V2")
            
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
                    
                    # Generar señales
                    df = self.analyzer.generate_optimized_signals(df)
                    
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
                            
                            # Simular trade
                            trade = self.simulate_trade_v2(
                                symbol, signal, current_price, signal_strength,
                                volatility, atr, timestamp
                            )
                            
                            if trade:
                                signals_generated += 1
                                total_signals += 1
                                print(f"  💹 Trade {signal_strength:.2f}: {trade['signal']} @ ${current_price:.4f} → PnL: ${trade['pnl']:.2f}")
                        
                        except Exception as e:
                            continue
                    
                    if signals_generated > 0:
                        successful_symbols += 1
                        print(f"✅ {symbol}: {signals_generated} señales generadas")
                    else:
                        print(f"⚠️ {symbol}: Sin señales válidas")
                    
                    # Pequeña pausa para evitar rate limiting
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"❌ Error procesando {symbol}: {e}")
                    continue
            
            # Calcular métricas finales
            results = self.calculate_advanced_metrics()
            results.update({
                'symbols_analyzed': len(symbols),
                'successful_symbols': successful_symbols,
                'total_signals': total_signals,
                'backtest_period_days': days_back,
                'strategy_version': '2.0 Optimizada'
            })
            
            return results
            
        except Exception as e:
            print(f"❌ Error en backtest: {e}")
            return {'error': str(e)}
    
    def calculate_advanced_metrics(self) -> Dict:
        """Calcula métricas avanzadas del backtest"""
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
            
            return {
                'timestamp': datetime.now().isoformat(),
                'strategy_version': '2.0 Optimizada',
                
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
                
                # Rendimiento
                'avg_win': float(avg_win),
                'avg_loss': float(avg_loss),
                'profit_factor': float(profit_factor),
                'avg_trade_duration_hours': float(avg_trade_duration),
                
                # Riesgo
                'max_drawdown': float(max_drawdown),
                'sharpe_ratio': float(sharpe_ratio),
                'total_commission': float(self.total_commission),
                'max_concurrent_positions': int(self.max_concurrent_positions),
                
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
    print("🚀 Backtester Optimizado V2 - Enhanced 15% Strategy")
    print("📊 Backtest con datos reales de Binance")
    print("⚡ Versión optimizada con mejores métricas")
    
    try:
        # Crear configuración optimizada
        config = OptimizedTradingConfig()
        
        # Crear backtester
        backtester = OptimizedBinanceBacktester(config)
        
        # Ejecutar backtest
        print(f"\n🔄 Ejecutando backtest optimizado...")
        results = backtester.run_backtest_v2(
            symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT', 
                    'DOTUSDT', 'LINKUSDT', 'AVAXUSDT', 'MATICUSDT', 'LTCUSDT'],
            days_back=30
        )
        
        # Mostrar resultados
        print(f"\n📈 RESULTADOS DEL BACKTEST OPTIMIZADO V2")
        print(f"="*60)
        
        if 'error' in results:
            print(f"❌ Error: {results['error']}")
            return
        
        print(f"💰 Capital inicial: ${results['initial_capital']:,.2f}")
        print(f"💰 Capital final: ${results['final_capital']:,.2f}")
        print(f"📊 Retorno total: {results['total_return']:.2f}%")
        print(f"📅 Retorno diario: {results['daily_return']:.3f}%")
        print(f"📅 Retorno mensual: {results['monthly_return']:.2f}%")
        print(f"\n🎯 TRADES")
        print(f"   Total: {results['total_trades']}")
        print(f"   Ganadores: {results['winning_trades']} ({results['win_rate']:.1f}%)")
        print(f"   Perdedores: {results['losing_trades']}")
        print(f"   Factor de ganancia: {results['profit_factor']:.2f}")
        print(f"\n📊 MÉTRICAS DE RIESGO")
        print(f"   Drawdown máximo: {results['max_drawdown']:.2f}%")
        print(f"   Sharpe ratio: {results['sharpe_ratio']:.2f}")
        print(f"   Comisiones totales: ${results['total_commission']:.2f}")
        print(f"\n🎯 OBJETIVOS")
        print(f"   Objetivo diario ({results['config']['daily_target']:.1f}%): {'✅ CUMPLIDO' if results['meets_daily_target'] else '❌ NO CUMPLIDO'}")
        print(f"   Objetivo mensual ({results['config']['monthly_target']:.1f}%): {'✅ CUMPLIDO' if results['meets_monthly_target'] else '❌ NO CUMPLIDO'}")
        print(f"   Ratio de cumplimiento: {results['target_achievement_ratio']:.2f}x")
        
        # Guardar resultados
        filename = f"backtest_optimizado_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Resultados guardados en: {filename}")
        
        # Recomendaciones
        print(f"\n🔧 RECOMENDACIONES:")
        if results['total_return'] > 0:
            print(f"   ✅ Estrategia rentable con {results['total_return']:.2f}% de retorno")
        else:
            print(f"   ⚠️ Estrategia con pérdidas: {results['total_return']:.2f}%")
        
        if results['win_rate'] > 60:
            print(f"   ✅ Excelente win rate: {results['win_rate']:.1f}%")
        elif results['win_rate'] > 50:
            print(f"   ✅ Buen win rate: {results['win_rate']:.1f}%")
        else:
            print(f"   ⚠️ Win rate bajo: {results['win_rate']:.1f}% - Considerar ajustes")
        
        if results['meets_daily_target']:
            print(f"   🎯 Estrategia cumple objetivos diarios")
        else:
            print(f"   🔧 Necesita optimización para objetivos diarios")
        
        print(f"\n🚀 Backtest V2 completado exitosamente")
        
    except Exception as e:
        print(f"❌ Error en main: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()