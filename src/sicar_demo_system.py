#!/usr/bin/env python3
"""
Sistema SICAR Demo - Versión de demostración
Datos simulados para validar performance del sistema optimizado
Objetivo: 15% ROI mensual sin apalancamiento
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sicar_demo_results.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SicarDemoSystem:
    def __init__(self, initial_capital=10000):
        """Inicializar sistema SICAR demo"""
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}
        self.trades = []
        self.performance_metrics = {}
        
        # Configuración optimizada
        self.symbols = ['BTC', 'ETH', 'ADA', 'SOL', 'XRP']
        
        # Parámetros optimizados basados en análisis previo
        self.params = {
            'min_signal_quality': 0.75,
            'ml_confidence_threshold': 0.65,
            'max_positions': 3,
            'position_size_base': 0.15,
            'stop_loss_pct': 0.03,
            'take_profit_pct': 0.08,
            'trailing_stop_pct': 0.02,
            'market_score_threshold': 40,
        }
        
        logger.info("Sistema SICAR Demo inicializado")

    def generate_simulated_data(self, symbol, days=180):
        """Generar datos simulados realistas"""
        try:
            # Parámetros base por símbolo
            base_params = {
                'BTC': {'price': 45000, 'volatility': 0.04, 'trend': 0.0008},
                'ETH': {'price': 3000, 'volatility': 0.05, 'trend': 0.0010},
                'ADA': {'price': 0.5, 'volatility': 0.06, 'trend': 0.0012},
                'SOL': {'price': 100, 'volatility': 0.07, 'trend': 0.0015},
                'XRP': {'price': 0.6, 'volatility': 0.05, 'trend': 0.0009}
            }
            
            params = base_params.get(symbol, base_params['BTC'])
            
            # Generar fechas
            dates = pd.date_range(
                start=datetime.now() - timedelta(days=days),
                end=datetime.now(),
                freq='H'
            )
            
            # Generar precios con tendencia y volatilidad
            np.random.seed(42)  # Para reproducibilidad
            
            returns = np.random.normal(
                params['trend'], 
                params['volatility'], 
                len(dates)
            )
            
            # Agregar ciclos de mercado
            cycle = np.sin(np.arange(len(dates)) * 2 * np.pi / (24 * 7)) * 0.01
            returns += cycle
            
            # Calcular precios
            prices = [params['price']]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # Crear DataFrame
            data = pd.DataFrame(index=dates)
            data['Close'] = prices
            data['Open'] = data['Close'].shift(1) * (1 + np.random.normal(0, 0.001, len(data)))
            data['High'] = np.maximum(data['Open'], data['Close']) * (1 + np.abs(np.random.normal(0, 0.005, len(data))))
            data['Low'] = np.minimum(data['Open'], data['Close']) * (1 - np.abs(np.random.normal(0, 0.005, len(data))))
            data['Volume'] = np.random.lognormal(15, 0.5, len(data))
            
            # Limpiar datos
            data = data.dropna()
            
            return data
            
        except Exception as e:
            logger.error(f"Error generando datos simulados para {symbol}: {e}")
            return None

    def calculate_technical_indicators(self, data):
        """Calcular indicadores técnicos optimizados"""
        try:
            indicators = {}
            close = data['Close']
            high = data['High']
            low = data['Low']
            volume = data['Volume']
            
            # Medias móviles
            indicators['sma_20'] = close.rolling(20).mean()
            indicators['sma_50'] = close.rolling(50).mean()
            indicators['ema_12'] = close.ewm(span=12).mean()
            indicators['ema_26'] = close.ewm(span=26).mean()
            
            # MACD
            indicators['macd'] = indicators['ema_12'] - indicators['ema_26']
            indicators['macd_signal'] = indicators['macd'].ewm(span=9).mean()
            indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']
            
            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            indicators['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            bb_middle = close.rolling(20).mean()
            bb_std = close.rolling(20).std()
            indicators['bb_upper'] = bb_middle + (bb_std * 2)
            indicators['bb_lower'] = bb_middle - (bb_std * 2)
            indicators['bb_width'] = (indicators['bb_upper'] - indicators['bb_lower']) / bb_middle
            
            # Stochastic
            lowest_low = low.rolling(14).min()
            highest_high = high.rolling(14).max()
            indicators['stoch_k'] = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            indicators['stoch_d'] = indicators['stoch_k'].rolling(3).mean()
            
            # ATR
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            indicators['atr'] = true_range.rolling(14).mean()
            
            # Volumen
            indicators['volume_sma'] = volume.rolling(20).mean()
            indicators['volume_ratio'] = volume / indicators['volume_sma']
            
            # Momentum
            indicators['momentum'] = close / close.shift(10)
            indicators['roc'] = close.pct_change(10)
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculando indicadores: {e}")
            return {}

    def generate_optimized_signals(self, data, indicators):
        """Generar señales optimizadas con múltiples filtros"""
        try:
            signals = []
            
            for i in range(50, len(data)):
                signal_score = 0
                quality_score = 0
                
                # Señales de tendencia (peso: 30%)
                if indicators['ema_12'].iloc[i] > indicators['ema_26'].iloc[i]:
                    signal_score += 1
                    if indicators['ema_12'].iloc[i-1] <= indicators['ema_26'].iloc[i-1]:
                        signal_score += 2  # Cruce alcista
                
                if indicators['sma_20'].iloc[i] > indicators['sma_50'].iloc[i]:
                    signal_score += 1
                
                # MACD (peso: 25%)
                if indicators['macd'].iloc[i] > indicators['macd_signal'].iloc[i]:
                    signal_score += 1
                    if indicators['macd'].iloc[i-1] <= indicators['macd_signal'].iloc[i-1]:
                        signal_score += 2  # Cruce MACD
                
                # RSI (peso: 20%)
                rsi = indicators['rsi'].iloc[i]
                if 30 < rsi < 70:
                    signal_score += 1
                elif rsi < 30:
                    signal_score += 2  # Sobreventa
                elif rsi > 70:
                    signal_score -= 1  # Sobrecompra
                
                # Bollinger Bands (peso: 15%)
                price = data['Close'].iloc[i]
                bb_position = (price - indicators['bb_lower'].iloc[i]) / (indicators['bb_upper'].iloc[i] - indicators['bb_lower'].iloc[i])
                if 0.2 < bb_position < 0.8:
                    signal_score += 1
                elif bb_position < 0.2:
                    signal_score += 1  # Cerca del soporte
                
                # Stochastic (peso: 10%)
                if indicators['stoch_k'].iloc[i] > indicators['stoch_d'].iloc[i]:
                    signal_score += 1
                
                # Filtros de calidad
                # Volumen
                if indicators['volume_ratio'].iloc[i] > 1.2:
                    quality_score += 1
                
                # Volatilidad
                if indicators['bb_width'].iloc[i] > indicators['bb_width'].iloc[i-10:i].mean():
                    quality_score += 1
                
                # Momentum
                if indicators['momentum'].iloc[i] > 1.02:
                    quality_score += 1
                
                # Calcular confianza total
                total_score = signal_score + quality_score
                confidence = min(1.0, total_score / 12)  # Normalizar a 0-1
                
                # Determinar señal
                if total_score >= 8 and confidence >= self.params['min_signal_quality']:
                    signal_type = 'BUY'
                elif total_score <= 3:
                    signal_type = 'SELL'
                else:
                    signal_type = 'HOLD'
                
                signals.append({
                    'timestamp': data.index[i],
                    'signal': signal_type,
                    'confidence': confidence,
                    'score': total_score,
                    'quality': quality_score,
                    'price': price
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generando señales: {e}")
            return []

    def calculate_dynamic_position_size(self, signal, symbol, market_conditions=None):
        """Calcular tamaño de posición dinámico"""
        try:
            # Tamaño base
            base_size = self.params['position_size_base']
            
            # Ajustar por confianza
            confidence_multiplier = signal.get('confidence', 0.5)
            
            # Ajustar por calidad
            quality_multiplier = min(1.5, signal.get('quality', 0) / 3)
            
            # Ajustar por número de posiciones actuales
            position_adjustment = max(0.5, 1 - (len(self.positions) * 0.2))
            
            # Calcular tamaño final
            position_size = (base_size * confidence_multiplier * 
                           quality_multiplier * position_adjustment)
            
            # Límites
            position_size = max(0.05, min(0.25, position_size))
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {e}")
            return 0.1

    def execute_trade(self, signal, symbol, position_size):
        """Ejecutar operación optimizada"""
        try:
            trade_value = self.current_capital * position_size
            price = signal['price']
            
            if signal['signal'] == 'BUY':
                # Verificar límites
                if symbol in self.positions:
                    return False
                
                if len(self.positions) >= self.params['max_positions']:
                    return False
                
                if trade_value > self.current_capital * 0.9:
                    return False
                
                # Ejecutar compra
                shares = trade_value / price
                
                self.positions[symbol] = {
                    'type': 'LONG',
                    'shares': shares,
                    'entry_price': price,
                    'entry_time': signal['timestamp'],
                    'stop_loss': price * (1 - self.params['stop_loss_pct']),
                    'take_profit': price * (1 + self.params['take_profit_pct']),
                    'trailing_stop': price * (1 - self.params['trailing_stop_pct']),
                    'confidence': signal.get('confidence', 0.5)
                }
                
                self.current_capital -= trade_value
                
                trade = {
                    'timestamp': signal['timestamp'],
                    'symbol': symbol,
                    'action': 'BUY',
                    'shares': shares,
                    'price': price,
                    'value': trade_value,
                    'confidence': signal.get('confidence', 0.5)
                }
                
                self.trades.append(trade)
                logger.info(f"Compra: {symbol} - {shares:.4f} @ ${price:.2f} (Conf: {signal.get('confidence', 0):.2f})")
                
                return True
                
            elif signal['signal'] == 'SELL' and symbol in self.positions:
                return self.close_position(symbol, price, "Signal")
            
            return False
            
        except Exception as e:
            logger.error(f"Error ejecutando trade: {e}")
            return False

    def close_position(self, symbol, price, reason):
        """Cerrar posición"""
        try:
            if symbol not in self.positions:
                return False
            
            position = self.positions[symbol]
            shares = position['shares']
            entry_price = position['entry_price']
            
            # Calcular P&L
            profit_loss = (price - entry_price) * shares
            profit_pct = (price - entry_price) / entry_price
            
            # Actualizar capital
            self.current_capital += price * shares
            
            # Registrar trade
            trade = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'action': 'SELL',
                'shares': shares,
                'price': price,
                'value': price * shares,
                'profit_loss': profit_loss,
                'profit_pct': profit_pct,
                'close_reason': reason,
                'hold_time': datetime.now() - position['entry_time']
            }
            
            self.trades.append(trade)
            del self.positions[symbol]
            
            logger.info(f"Venta: {symbol} - {reason} - P&L: ${profit_loss:.2f} ({profit_pct:.2%})")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cerrando posición: {e}")
            return False

    def check_risk_management(self, current_prices):
        """Verificar gestión de riesgo"""
        try:
            positions_to_close = []
            
            for symbol, position in self.positions.items():
                if symbol not in current_prices:
                    continue
                
                current_price = current_prices[symbol]
                entry_price = position['entry_price']
                
                # Actualizar trailing stop
                if current_price > entry_price * 1.02:
                    new_trailing = current_price * (1 - self.params['trailing_stop_pct'])
                    position['trailing_stop'] = max(position['trailing_stop'], new_trailing)
                
                # Verificar condiciones de cierre
                should_close = False
                close_reason = ""
                
                if current_price <= position['stop_loss']:
                    should_close = True
                    close_reason = "Stop Loss"
                elif current_price >= position['take_profit']:
                    should_close = True
                    close_reason = "Take Profit"
                elif current_price <= position['trailing_stop']:
                    should_close = True
                    close_reason = "Trailing Stop"
                
                if should_close:
                    positions_to_close.append((symbol, current_price, close_reason))
            
            # Cerrar posiciones
            for symbol, price, reason in positions_to_close:
                self.close_position(symbol, price, reason)
                
        except Exception as e:
            logger.error(f"Error en gestión de riesgo: {e}")

    def run_demo_backtest(self, days=90):
        """Ejecutar backtest de demostración"""
        try:
            logger.info(f"Iniciando backtest demo por {days} días...")
            
            # Generar datos para todos los símbolos
            all_data = {}
            for symbol in self.symbols:
                data = self.generate_simulated_data(symbol, days)
                if data is not None:
                    all_data[symbol] = data
            
            if not all_data:
                logger.error("No se pudieron generar datos")
                return {}
            
            # Obtener fechas comunes
            common_dates = None
            for data in all_data.values():
                if common_dates is None:
                    common_dates = set(data.index)
                else:
                    common_dates = common_dates.intersection(set(data.index))
            
            common_dates = sorted(list(common_dates))
            
            # Ejecutar backtest
            for date in common_dates[50:]:  # Empezar después de 50 períodos para indicadores
                try:
                    current_prices = {}
                    
                    # Procesar cada símbolo
                    for symbol, data in all_data.items():
                        if date not in data.index:
                            continue
                        
                        current_prices[symbol] = data.loc[date, 'Close']
                        
                        # Calcular indicadores
                        data_subset = data.loc[:date]
                        if len(data_subset) < 50:
                            continue
                        
                        indicators = self.calculate_technical_indicators(data_subset)
                        if not indicators:
                            continue
                        
                        # Generar señales
                        signals = self.generate_optimized_signals(data_subset, indicators)
                        if not signals:
                            continue
                        
                        # Procesar última señal
                        latest_signal = signals[-1]
                        
                        # Calcular tamaño de posición
                        position_size = self.calculate_dynamic_position_size(latest_signal, symbol)
                        
                        # Ejecutar trade
                        if position_size > 0.05:
                            self.execute_trade(latest_signal, symbol, position_size)
                    
                    # Verificar gestión de riesgo
                    self.check_risk_management(current_prices)
                    
                except Exception as e:
                    logger.warning(f"Error procesando fecha {date}: {e}")
                    continue
            
            # Cerrar posiciones restantes
            final_prices = {symbol: data.iloc[-1]['Close'] for symbol, data in all_data.items()}
            for symbol in list(self.positions.keys()):
                if symbol in final_prices:
                    self.close_position(symbol, final_prices[symbol], "End of Backtest")
            
            # Calcular métricas finales
            results = self.calculate_performance_metrics()
            
            return results
            
        except Exception as e:
            logger.error(f"Error en backtest demo: {e}")
            return {}

    def calculate_performance_metrics(self):
        """Calcular métricas de performance"""
        try:
            if not self.trades:
                return {}
            
            # Filtrar trades de venta
            sell_trades = [t for t in self.trades if t['action'] == 'SELL']
            
            if not sell_trades:
                return {}
            
            # Métricas básicas
            total_trades = len(sell_trades)
            profits = [t.get('profit_loss', 0) for t in sell_trades]
            profit_pcts = [t.get('profit_pct', 0) for t in sell_trades]
            
            winning_trades = [p for p in profits if p > 0]
            losing_trades = [p for p in profits if p < 0]
            
            # Calcular métricas
            total_return = sum(profits)
            total_roi = (self.current_capital - self.initial_capital) / self.initial_capital
            
            win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
            avg_profit = np.mean(profits) if profits else 0
            avg_win = np.mean(winning_trades) if winning_trades else 0
            avg_loss = np.mean(losing_trades) if losing_trades else 0
            
            profit_factor = abs(sum(winning_trades) / sum(losing_trades)) if losing_trades else float('inf')
            
            # Sharpe ratio simplificado
            if profit_pcts:
                sharpe_ratio = np.mean(profit_pcts) / np.std(profit_pcts) if np.std(profit_pcts) > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Drawdown máximo
            portfolio_values = [self.initial_capital]
            running_capital = self.initial_capital
            
            for trade in self.trades:
                if trade['action'] == 'BUY':
                    running_capital -= trade['value']
                elif trade['action'] == 'SELL':
                    running_capital += trade['value']
                portfolio_values.append(running_capital)
            
            peak = portfolio_values[0]
            max_drawdown = 0
            
            for value in portfolio_values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
            
            # ROI mensual
            days_traded = (self.trades[-1]['timestamp'] - self.trades[0]['timestamp']).days
            monthly_roi = total_roi * (30 / days_traded) if days_traded > 0 else 0
            
            results = {
                'total_trades': total_trades,
                'win_rate': win_rate,
                'total_return': total_return,
                'total_roi': total_roi,
                'monthly_roi': monthly_roi,
                'avg_profit': avg_profit,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'final_capital': self.current_capital,
                'days_traded': days_traded
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculando métricas: {e}")
            return {}

    def generate_report(self):
        """Generar reporte detallado"""
        try:
            metrics = self.calculate_performance_metrics()
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'system': 'SICAR Demo Optimizado',
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital,
                'performance': metrics,
                'active_positions': len(self.positions),
                'total_trades_executed': len(self.trades),
                'parameters': self.params,
                'recent_trades': self.trades[-10:] if self.trades else []
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
            return {}

def main():
    """Función principal"""
    try:
        print("=== SISTEMA SICAR DEMO OPTIMIZADO ===")
        print("Objetivo: 15% ROI mensual sin apalancamiento")
        print("Integrando todas las mejoras desarrolladas\n")
        
        # Crear sistema
        system = SicarDemoSystem(initial_capital=10000)
        
        # Ejecutar backtest
        print("Ejecutando backtest optimizado...")
        results = system.run_demo_backtest(days=90)
        
        if results:
            print("\n=== RESULTADOS DEL SISTEMA OPTIMIZADO ===")
            print(f"ROI Total: {results.get('total_roi', 0):.2%}")
            print(f"ROI Mensual: {results.get('monthly_roi', 0):.2%}")
            print(f"Win Rate: {results.get('win_rate', 0):.2%}")
            print(f"Total Trades: {results.get('total_trades', 0)}")
            print(f"Profit Factor: {results.get('profit_factor', 0):.2f}")
            print(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
            print(f"Max Drawdown: {results.get('max_drawdown', 0):.2%}")
            print(f"Capital Final: ${results.get('final_capital', 0):.2f}")
            
            # Verificar objetivo
            monthly_roi = results.get('monthly_roi', 0)
            target_roi = 0.15
            
            print(f"\n=== ANÁLISIS DE OBJETIVO ===")
            print(f"Objetivo: {target_roi:.1%} mensual")
            print(f"Alcanzado: {monthly_roi:.1%} mensual")
            
            if monthly_roi >= target_roi:
                print("✅ OBJETIVO ALCANZADO!")
                print(f"Superó el objetivo por: {(monthly_roi - target_roi):.1%}")
            else:
                print("❌ Objetivo no alcanzado")
                print(f"Falta: {(target_roi - monthly_roi):.1%} para alcanzar el objetivo")
            
            # Guardar resultados
            report = system.generate_report()
            
            # Exportar a CSV
            if system.trades:
                trades_df = pd.DataFrame(system.trades)
                trades_df.to_csv('sicar_demo_trades.csv', index=False)
                print(f"\nTrades exportados a: sicar_demo_trades.csv")
            
            print(f"Reporte completo generado con {len(report)} elementos")
            
        else:
            print("No se pudieron generar resultados")
        
        print("\n=== DEMO COMPLETADA ===")
        
    except Exception as e:
        print(f"Error en demo: {e}")

if __name__ == "__main__":
    main()