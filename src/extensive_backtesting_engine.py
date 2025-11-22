#!/usr/bin/env python3
"""
Motor de Backtesting Extenso para Sistema SICAR
Backtesting con 6-12 meses de datos históricos
Validación robusta y análisis detallado de performance
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Visualización
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.dates import DateFormatter
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Estadísticas
from scipy import stats
import yfinance as yf

logger = logging.getLogger(__name__)

class ExtensiveBacktestingEngine:
    def __init__(self, initial_capital=10000):
        """Inicializar motor de backtesting extenso"""
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        self.monthly_returns = []
        
        # Métricas de performance
        self.metrics = {}
        self.drawdown_periods = []
        self.winning_streaks = []
        self.losing_streaks = []
        
        # Configuración de backtesting
        self.commission = 0.001  # 0.1% comisión
        self.slippage = 0.0005   # 0.05% slippage
        self.min_trade_amount = 100  # Mínimo $100 por trade
        
        logger.info("Motor de backtesting extenso inicializado")

    def fetch_extended_data(self, symbols, period='12mo', interval='1h'):
        """Obtener datos históricos extensos"""
        try:
            logger.info(f"Obteniendo datos históricos para {len(symbols)} símbolos - Período: {period}")
            
            all_data = {}
            
            for symbol in symbols:
                try:
                    # Obtener datos de yfinance
                    ticker = yf.Ticker(symbol)
                    data = ticker.history(period=period, interval=interval)
                    
                    if data.empty:
                        logger.warning(f"No se obtuvieron datos para {symbol}")
                        continue
                    
                    # Limpiar datos
                    data = data.dropna()
                    data.columns = [col.lower() for col in data.columns]
                    
                    # Agregar timestamp
                    data['timestamp'] = data.index
                    data = data.reset_index(drop=True)
                    
                    all_data[symbol] = data
                    logger.info(f"Datos obtenidos para {symbol}: {len(data)} registros")
                    
                except Exception as e:
                    logger.error(f"Error obteniendo datos para {symbol}: {e}")
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error en fetch_extended_data: {e}")
            return {}

    def prepare_backtest_data(self, data, features, signals):
        """Preparar datos para backtesting"""
        try:
            # Combinar datos, features y señales
            backtest_data = data.copy()
            
            # Agregar features
            for col in features.columns:
                if col not in backtest_data.columns:
                    backtest_data[col] = features[col]
            
            # Agregar señales
            for col in signals.columns:
                if col not in backtest_data.columns:
                    backtest_data[col] = signals[col]
            
            # Limpiar datos
            backtest_data = backtest_data.fillna(0)
            backtest_data = backtest_data.replace([np.inf, -np.inf], 0)
            
            # Ordenar por timestamp
            if 'timestamp' in backtest_data.columns:
                backtest_data = backtest_data.sort_values('timestamp')
            
            return backtest_data
            
        except Exception as e:
            logger.error(f"Error preparando datos de backtesting: {e}")
            return data

    def calculate_position_size(self, signal_strength, volatility, current_capital):
        """Calcular tamaño de posición dinámico"""
        try:
            # Tamaño base (2-5% del capital)
            base_size = current_capital * 0.03
            
            # Ajustar por fuerza de señal (0.5x a 2x)
            signal_multiplier = 0.5 + (signal_strength * 1.5)
            
            # Ajustar por volatilidad (menos tamaño en alta volatilidad)
            volatility_multiplier = max(0.3, 1 - (volatility * 10))
            
            # Calcular tamaño final
            position_size = base_size * signal_multiplier * volatility_multiplier
            
            # Aplicar límites
            position_size = max(self.min_trade_amount, position_size)
            position_size = min(position_size, current_capital * 0.1)  # Max 10% por trade
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculando tamaño de posición: {e}")
            return self.min_trade_amount

    def execute_trade(self, symbol, signal, price, timestamp, signal_strength=1.0, volatility=0.02):
        """Ejecutar trade con costos realistas"""
        try:
            # Calcular tamaño de posición
            position_size = self.calculate_position_size(signal_strength, volatility, self.current_capital)
            
            # Aplicar slippage
            if signal > 0:  # BUY
                execution_price = price * (1 + self.slippage)
            else:  # SELL
                execution_price = price * (1 - self.slippage)
            
            # Calcular cantidad de acciones/crypto
            quantity = position_size / execution_price
            
            # Calcular comisión
            commission_cost = position_size * self.commission
            
            # Verificar capital suficiente
            total_cost = position_size + commission_cost
            if total_cost > self.current_capital:
                logger.warning(f"Capital insuficiente para trade: {total_cost} > {self.current_capital}")
                return False
            
            # Ejecutar trade
            if signal > 0:  # BUY
                if symbol in self.positions:
                    # Agregar a posición existente
                    old_quantity = self.positions[symbol]['quantity']
                    old_avg_price = self.positions[symbol]['avg_price']
                    
                    new_quantity = old_quantity + quantity
                    new_avg_price = ((old_quantity * old_avg_price) + (quantity * execution_price)) / new_quantity
                    
                    self.positions[symbol] = {
                        'quantity': new_quantity,
                        'avg_price': new_avg_price,
                        'timestamp': timestamp
                    }
                else:
                    # Nueva posición
                    self.positions[symbol] = {
                        'quantity': quantity,
                        'avg_price': execution_price,
                        'timestamp': timestamp
                    }
                
                self.current_capital -= total_cost
                
                # Registrar trade
                self.trades.append({
                    'timestamp': timestamp,
                    'symbol': symbol,
                    'action': 'BUY',
                    'quantity': quantity,
                    'price': execution_price,
                    'value': position_size,
                    'commission': commission_cost,
                    'signal_strength': signal_strength,
                    'capital_after': self.current_capital
                })
                
            else:  # SELL
                if symbol in self.positions and self.positions[symbol]['quantity'] > 0:
                    # Vender posición
                    position = self.positions[symbol]
                    sell_quantity = min(quantity, position['quantity'])
                    
                    # Calcular P&L
                    buy_value = sell_quantity * position['avg_price']
                    sell_value = sell_quantity * execution_price
                    gross_pnl = sell_value - buy_value
                    net_pnl = gross_pnl - commission_cost
                    
                    # Actualizar capital
                    self.current_capital += sell_value - commission_cost
                    
                    # Actualizar posición
                    remaining_quantity = position['quantity'] - sell_quantity
                    if remaining_quantity > 0:
                        self.positions[symbol]['quantity'] = remaining_quantity
                    else:
                        del self.positions[symbol]
                    
                    # Registrar trade
                    self.trades.append({
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'action': 'SELL',
                        'quantity': sell_quantity,
                        'price': execution_price,
                        'value': sell_value,
                        'commission': commission_cost,
                        'pnl': net_pnl,
                        'signal_strength': signal_strength,
                        'capital_after': self.current_capital
                    })
                    
                else:
                    logger.warning(f"No hay posición para vender en {symbol}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error ejecutando trade: {e}")
            return False

    def calculate_portfolio_value(self, current_prices):
        """Calcular valor total del portfolio"""
        try:
            portfolio_value = self.current_capital
            
            # Agregar valor de posiciones abiertas
            for symbol, position in self.positions.items():
                if symbol in current_prices:
                    position_value = position['quantity'] * current_prices[symbol]
                    portfolio_value += position_value
            
            return portfolio_value
            
        except Exception as e:
            logger.error(f"Error calculando valor del portfolio: {e}")
            return self.current_capital

    def run_backtest(self, data_dict, strategy_func, start_date=None, end_date=None):
        """Ejecutar backtesting extenso"""
        try:
            logger.info("Iniciando backtesting extenso...")
            
            # Resetear estado
            self.current_capital = self.initial_capital
            self.positions = {}
            self.trades = []
            self.equity_curve = []
            
            # Obtener fechas comunes
            all_timestamps = []
            for symbol, data in data_dict.items():
                if 'timestamp' in data.columns:
                    all_timestamps.extend(data['timestamp'].tolist())
            
            unique_timestamps = sorted(list(set(all_timestamps)))
            
            # Filtrar por fechas si se especifican
            if start_date:
                unique_timestamps = [ts for ts in unique_timestamps if ts >= start_date]
            if end_date:
                unique_timestamps = [ts for ts in unique_timestamps if ts <= end_date]
            
            logger.info(f"Backtesting período: {unique_timestamps[0]} a {unique_timestamps[-1]}")
            logger.info(f"Total timestamps: {len(unique_timestamps)}")
            
            # Ejecutar backtesting
            for i, timestamp in enumerate(unique_timestamps):
                try:
                    # Obtener datos actuales para todos los símbolos
                    current_data = {}
                    current_prices = {}
                    
                    for symbol, data in data_dict.items():
                        # Encontrar datos hasta este timestamp
                        mask = data['timestamp'] <= timestamp
                        if mask.any():
                            current_row = data[mask].iloc[-1]
                            current_data[symbol] = current_row
                            current_prices[symbol] = current_row['close']
                    
                    if not current_data:
                        continue
                    
                    # Ejecutar estrategia
                    signals = strategy_func(current_data, timestamp)
                    
                    # Ejecutar trades basados en señales
                    for symbol, signal_info in signals.items():
                        if symbol in current_prices:
                            signal = signal_info.get('signal', 0)
                            strength = signal_info.get('strength', 1.0)
                            volatility = signal_info.get('volatility', 0.02)
                            
                            if signal != 0:
                                self.execute_trade(
                                    symbol, signal, current_prices[symbol], 
                                    timestamp, strength, volatility
                                )
                    
                    # Calcular valor del portfolio
                    portfolio_value = self.calculate_portfolio_value(current_prices)
                    
                    # Registrar equity curve
                    self.equity_curve.append({
                        'timestamp': timestamp,
                        'portfolio_value': portfolio_value,
                        'cash': self.current_capital,
                        'positions_value': portfolio_value - self.current_capital
                    })
                    
                    # Log progreso cada 1000 iteraciones
                    if i % 1000 == 0:
                        logger.info(f"Progreso: {i}/{len(unique_timestamps)} - Portfolio: ${portfolio_value:,.2f}")
                
                except Exception as e:
                    logger.error(f"Error en timestamp {timestamp}: {e}")
                    continue
            
            logger.info("Backtesting completado")
            return True
            
        except Exception as e:
            logger.error(f"Error en backtesting: {e}")
            return False

    def calculate_metrics(self):
        """Calcular métricas de performance detalladas"""
        try:
            if not self.equity_curve:
                logger.warning("No hay datos de equity curve para calcular métricas")
                return {}
            
            # Convertir a DataFrame
            equity_df = pd.DataFrame(self.equity_curve)
            equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
            equity_df = equity_df.set_index('timestamp')
            
            # Calcular retornos
            equity_df['returns'] = equity_df['portfolio_value'].pct_change()
            equity_df['cumulative_returns'] = (1 + equity_df['returns']).cumprod() - 1
            
            # Métricas básicas
            total_return = (equity_df['portfolio_value'].iloc[-1] / self.initial_capital) - 1
            
            # Calcular retornos mensuales
            monthly_returns = equity_df['portfolio_value'].resample('M').last().pct_change().dropna()
            avg_monthly_return = monthly_returns.mean()
            
            # Calcular retornos diarios
            daily_returns = equity_df['returns'].dropna()
            
            # Sharpe Ratio (asumiendo 0% risk-free rate)
            sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
            
            # Sortino Ratio
            downside_returns = daily_returns[daily_returns < 0]
            sortino_ratio = daily_returns.mean() / downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 and downside_returns.std() > 0 else 0
            
            # Maximum Drawdown
            rolling_max = equity_df['portfolio_value'].expanding().max()
            drawdown = (equity_df['portfolio_value'] - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # Calmar Ratio
            calmar_ratio = avg_monthly_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Win Rate
            trades_df = pd.DataFrame(self.trades)
            if not trades_df.empty:
                profitable_trades = trades_df[trades_df.get('pnl', 0) > 0]
                win_rate = len(profitable_trades) / len(trades_df[trades_df['action'] == 'SELL']) if len(trades_df[trades_df['action'] == 'SELL']) > 0 else 0
                
                # Profit Factor
                gross_profit = profitable_trades['pnl'].sum() if not profitable_trades.empty else 0
                gross_loss = abs(trades_df[trades_df.get('pnl', 0) < 0]['pnl'].sum())
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
                
                # Average Trade
                avg_trade = trades_df[trades_df['action'] == 'SELL']['pnl'].mean() if len(trades_df[trades_df['action'] == 'SELL']) > 0 else 0
                
                # Total trades
                total_trades = len(trades_df[trades_df['action'] == 'SELL'])
            else:
                win_rate = 0
                profit_factor = 0
                avg_trade = 0
                total_trades = 0
            
            # Volatilidad
            volatility = daily_returns.std() * np.sqrt(252)
            
            # Beta (vs mercado - usando primer símbolo como proxy)
            if len(daily_returns) > 1:
                market_returns = daily_returns  # Simplificado
                beta = np.cov(daily_returns, market_returns)[0, 1] / np.var(market_returns) if np.var(market_returns) > 0 else 1
            else:
                beta = 1
            
            # Métricas de tiempo
            start_date = equity_df.index[0]
            end_date = equity_df.index[-1]
            total_days = (end_date - start_date).days
            
            # Compilar métricas
            metrics = {
                'total_return': total_return,
                'monthly_return': avg_monthly_return,
                'annualized_return': avg_monthly_return * 12,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio,
                'max_drawdown': max_drawdown,
                'volatility': volatility,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'avg_trade': avg_trade,
                'total_trades': total_trades,
                'beta': beta,
                'start_date': start_date,
                'end_date': end_date,
                'total_days': total_days,
                'final_capital': equity_df['portfolio_value'].iloc[-1],
                'max_capital': equity_df['portfolio_value'].max(),
                'min_capital': equity_df['portfolio_value'].min()
            }
            
            self.metrics = metrics
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculando métricas: {e}")
            return {}

    def generate_report(self, save_path=None):
        """Generar reporte detallado de backtesting"""
        try:
            if not self.metrics:
                self.calculate_metrics()
            
            report = []
            report.append("=" * 80)
            report.append("REPORTE DE BACKTESTING EXTENSO - SISTEMA SICAR")
            report.append("=" * 80)
            report.append("")
            
            # Información general
            report.append("INFORMACIÓN GENERAL:")
            report.append(f"Período: {self.metrics.get('start_date', 'N/A')} a {self.metrics.get('end_date', 'N/A')}")
            report.append(f"Duración: {self.metrics.get('total_days', 0)} días")
            report.append(f"Capital inicial: ${self.initial_capital:,.2f}")
            report.append(f"Capital final: ${self.metrics.get('final_capital', 0):,.2f}")
            report.append("")
            
            # Métricas de retorno
            report.append("MÉTRICAS DE RETORNO:")
            report.append(f"Retorno total: {self.metrics.get('total_return', 0)*100:.2f}%")
            report.append(f"Retorno mensual promedio: {self.metrics.get('monthly_return', 0)*100:.2f}%")
            report.append(f"Retorno anualizado: {self.metrics.get('annualized_return', 0)*100:.2f}%")
            report.append("")
            
            # Métricas de riesgo
            report.append("MÉTRICAS DE RIESGO:")
            report.append(f"Máximo drawdown: {self.metrics.get('max_drawdown', 0)*100:.2f}%")
            report.append(f"Volatilidad anualizada: {self.metrics.get('volatility', 0)*100:.2f}%")
            report.append(f"Sharpe ratio: {self.metrics.get('sharpe_ratio', 0):.3f}")
            report.append(f"Sortino ratio: {self.metrics.get('sortino_ratio', 0):.3f}")
            report.append(f"Calmar ratio: {self.metrics.get('calmar_ratio', 0):.3f}")
            report.append(f"Beta: {self.metrics.get('beta', 0):.3f}")
            report.append("")
            
            # Métricas de trading
            report.append("MÉTRICAS DE TRADING:")
            report.append(f"Total de operaciones: {self.metrics.get('total_trades', 0)}")
            report.append(f"Win rate: {self.metrics.get('win_rate', 0)*100:.1f}%")
            report.append(f"Profit factor: {self.metrics.get('profit_factor', 0):.2f}")
            report.append(f"Trade promedio: ${self.metrics.get('avg_trade', 0):.2f}")
            report.append("")
            
            # Análisis de objetivo
            target_monthly = 0.15  # 15% mensual
            actual_monthly = self.metrics.get('monthly_return', 0)
            
            report.append("ANÁLISIS DE OBJETIVO:")
            report.append(f"Objetivo mensual: {target_monthly*100:.1f}%")
            report.append(f"Resultado mensual: {actual_monthly*100:.2f}%")
            report.append(f"Diferencia: {(actual_monthly - target_monthly)*100:.2f}%")
            
            if actual_monthly >= target_monthly:
                report.append("✅ OBJETIVO ALCANZADO")
            else:
                report.append("❌ OBJETIVO NO ALCANZADO")
            
            report.append("")
            report.append("=" * 80)
            
            # Convertir a string
            report_text = "\n".join(report)
            
            # Guardar si se especifica path
            if save_path:
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(report_text)
                logger.info(f"Reporte guardado en: {save_path}")
            
            return report_text
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
            return "Error generando reporte"

    def plot_results(self, save_path=None):
        """Crear gráficos de resultados"""
        try:
            if not self.equity_curve:
                logger.warning("No hay datos para graficar")
                return
            
            # Preparar datos
            equity_df = pd.DataFrame(self.equity_curve)
            equity_df['timestamp'] = pd.to_datetime(equity_df['timestamp'])
            
            # Crear figura con subplots
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Resultados de Backtesting Extenso - Sistema SICAR', fontsize=16)
            
            # 1. Equity Curve
            axes[0, 0].plot(equity_df['timestamp'], equity_df['portfolio_value'], linewidth=2, color='blue')
            axes[0, 0].axhline(y=self.initial_capital, color='red', linestyle='--', alpha=0.7, label='Capital Inicial')
            axes[0, 0].set_title('Curva de Capital')
            axes[0, 0].set_ylabel('Valor del Portfolio ($)')
            axes[0, 0].grid(True, alpha=0.3)
            axes[0, 0].legend()
            
            # 2. Drawdown
            rolling_max = equity_df['portfolio_value'].expanding().max()
            drawdown = (equity_df['portfolio_value'] - rolling_max) / rolling_max * 100
            axes[0, 1].fill_between(equity_df['timestamp'], drawdown, 0, alpha=0.7, color='red')
            axes[0, 1].set_title('Drawdown (%)')
            axes[0, 1].set_ylabel('Drawdown (%)')
            axes[0, 1].grid(True, alpha=0.3)
            
            # 3. Retornos mensuales
            equity_df_indexed = equity_df.set_index('timestamp')
            monthly_returns = equity_df_indexed['portfolio_value'].resample('M').last().pct_change().dropna() * 100
            axes[1, 0].bar(range(len(monthly_returns)), monthly_returns.values, 
                          color=['green' if x > 0 else 'red' for x in monthly_returns.values])
            axes[1, 0].axhline(y=15, color='blue', linestyle='--', alpha=0.7, label='Objetivo 15%')
            axes[1, 0].set_title('Retornos Mensuales (%)')
            axes[1, 0].set_ylabel('Retorno (%)')
            axes[1, 0].grid(True, alpha=0.3)
            axes[1, 0].legend()
            
            # 4. Distribución de trades
            if self.trades:
                trades_df = pd.DataFrame(self.trades)
                sell_trades = trades_df[trades_df['action'] == 'SELL']
                if not sell_trades.empty and 'pnl' in sell_trades.columns:
                    pnl_values = sell_trades['pnl'].values
                    axes[1, 1].hist(pnl_values, bins=20, alpha=0.7, color='purple', edgecolor='black')
                    axes[1, 1].axvline(x=0, color='red', linestyle='--', alpha=0.7)
                    axes[1, 1].set_title('Distribución de P&L por Trade')
                    axes[1, 1].set_xlabel('P&L ($)')
                    axes[1, 1].set_ylabel('Frecuencia')
                    axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Guardar si se especifica
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Gráficos guardados en: {save_path}")
            
            plt.show()
            
        except Exception as e:
            logger.error(f"Error creando gráficos: {e}")

    def export_trades(self, save_path):
        """Exportar trades a CSV"""
        try:
            if not self.trades:
                logger.warning("No hay trades para exportar")
                return
            
            trades_df = pd.DataFrame(self.trades)
            trades_df.to_csv(save_path, index=False)
            logger.info(f"Trades exportados a: {save_path}")
            
        except Exception as e:
            logger.error(f"Error exportando trades: {e}")

def main():
    """Función de prueba"""
    try:
        # Crear motor de backtesting
        backtest_engine = ExtensiveBacktestingEngine(initial_capital=10000)
        
        # Obtener datos de prueba
        symbols = ['BTC-USD', 'ETH-USD']
        data = backtest_engine.fetch_extended_data(symbols, period='3mo', interval='1h')
        
        if data:
            print(f"Datos obtenidos para {len(data)} símbolos")
            for symbol, df in data.items():
                print(f"{symbol}: {len(df)} registros")
        
        print("Prueba de backtesting extenso completada")
        
    except Exception as e:
        print(f"Error en prueba: {e}")

if __name__ == "__main__":
    main()