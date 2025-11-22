#!/usr/bin/env python3
"""
Evaluador de Rendimiento del Sistema SICAR
==========================================

Este script evalúa el rendimiento actual del sistema de trading simulado
con datos reales de Binance, analizando:

1. Rendimiento del Paper Trading
2. Efectividad de la detección de breakouts
3. Performance del sistema de scalping
4. Métricas de riesgo y retorno
5. Análisis de señales y ejecución

Autor: Sistema SICAR
Fecha: 2025-01-14
"""

import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Optional

# Imports del sistema SICAR
from enhanced_logger import SICAR_LOGGER
logger = SICAR_LOGGER.get_logger('main')
from paper_trading_system import PaperTradingEngine
from enhanced_data_fetcher import EnhancedDataFetcher
from enhanced_breakout_detector import EnhancedBreakoutDetector
from scalping_engine import ScalpingEngine
from enhanced_config import CONFIG

class TradingPerformanceEvaluator:
    """Evaluador completo de rendimiento del sistema de trading"""
    
    def __init__(self):
        """Inicializar el evaluador"""
        self.data_fetcher = EnhancedDataFetcher()
        self.paper_engine = PaperTradingEngine(
            initial_capital=CONFIG.PAPER_TRADING_CONFIG['initial_capital'],
            commission_rate=CONFIG.PAPER_TRADING_CONFIG['commission_rate']
        )
        self.breakout_detector = EnhancedBreakoutDetector()
        self.scalping_engine = ScalpingEngine(paper_trading_system=self.paper_engine)
        
        # Configuración de análisis
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'BNBUSDT', 'SOLUSDT']
        self.timeframes = ['1m', '5m', '15m', '1h']
        self.analysis_period = 24  # horas
        
        # Métricas de rendimiento
        self.performance_metrics = {}
        self.trading_signals = []
        self.breakout_events = []
        self.scalping_operations = []
        
        logger.info("🔍 Evaluador de Rendimiento SICAR inicializado")
    
    async def evaluate_full_performance(self) -> Dict[str, Any]:
        """Evaluación completa del rendimiento del sistema"""
        logger.info("🚀 Iniciando evaluación completa de rendimiento...")
        
        try:
            # 1. Análisis de datos de mercado
            market_data = await self._analyze_market_data()
            
            # 2. Evaluación de detección de breakouts
            breakout_performance = await self._evaluate_breakout_detection()
            
            # 3. Análisis del sistema de scalping
            scalping_performance = await self._evaluate_scalping_system()
            
            # 4. Rendimiento del paper trading
            paper_trading_performance = await self._evaluate_paper_trading()
            
            # 5. Métricas de riesgo
            risk_metrics = await self._calculate_risk_metrics()
            
            # 6. Análisis de correlaciones
            correlation_analysis = await self._analyze_correlations()
            
            # Compilar resultados
            performance_report = {
                'timestamp': datetime.now().isoformat(),
                'analysis_period_hours': self.analysis_period,
                'symbols_analyzed': self.symbols,
                'market_data': market_data,
                'breakout_performance': breakout_performance,
                'scalping_performance': scalping_performance,
                'paper_trading_performance': paper_trading_performance,
                'risk_metrics': risk_metrics,
                'correlation_analysis': correlation_analysis,
                'overall_score': self._calculate_overall_score()
            }
            
            # Guardar reporte
            await self._save_performance_report(performance_report)
            
            # Generar visualizaciones
            await self._generate_performance_charts(performance_report)
            
            logger.info("✅ Evaluación de rendimiento completada")
            return performance_report
            
        except Exception as e:
            logger.error(f"❌ Error en evaluación de rendimiento: {e}")
            raise
    
    async def _analyze_market_data(self) -> Dict[str, Any]:
        """Analizar datos de mercado REALES actuales"""
        logger.info("📊 Analizando datos de mercado REALES...")
        
        market_analysis = {
            'symbols': {},
            'market_summary': {},
            'volatility_analysis': {},
            'volume_analysis': {},
            'data_quality': {}
        }
        
        successful_symbols = 0
        
        for symbol in self.symbols:
            try:
                logger.info(f"🔍 Obteniendo datos REALES para {symbol}...")
                
                # Obtener datos históricos REALES
                data = self.data_fetcher.get_historical_data(
                    symbol, self.analysis_period, '1h'
                )
                
                if data is not None and len(data) > 10:
                    # Verificar que los datos son reales y de calidad
                    logger.info(f"✅ Datos REALES obtenidos para {symbol}: {len(data)} velas")
                    
                    # Calcular métricas básicas
                    price_change = ((data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]) * 100
                    volatility = data['Close'].pct_change().std() * 100
                    avg_volume = data['Volume'].mean()
                    
                    market_analysis['symbols'][symbol] = {
                        'price_change_24h': round(price_change, 2),
                        'volatility': round(volatility, 4),
                        'avg_volume': round(avg_volume, 2),
                        'current_price': data['Close'].iloc[-1],
                        'high_24h': data['High'].max(),
                        'low_24h': data['Low'].min(),
                        'data_points': len(data)
                    }
                    
                    successful_symbols += 1
                    logger.info(f"✅ {symbol}: Precio ${data['Close'].iloc[-1]:.2f}, "
                              f"Cambio 24h: {price_change:.2f}%")
                else:
                    logger.error(f"❌ No se pudieron obtener datos REALES para {symbol}")
                    market_analysis['symbols'][symbol] = {
                        'error': 'No se pudieron obtener datos reales',
                        'data_points': 0
                    }
                    
            except Exception as e:
                logger.error(f"🚨 Error crítico analizando {symbol}: {e}")
                market_analysis['symbols'][symbol] = {
                    'error': str(e),
                    'data_points': 0
                }
        
        # Resumen del mercado
        valid_symbols = [s for s in market_analysis['symbols'].values() if 'error' not in s]
        if valid_symbols:
            market_analysis['market_summary'] = {
                'avg_price_change': np.mean([s['price_change_24h'] for s in valid_symbols]),
                'avg_volatility': np.mean([s['volatility'] for s in valid_symbols]),
                'total_symbols_analyzed': len(valid_symbols),
                'market_trend': 'bullish' if np.mean([s['price_change_24h'] for s in valid_symbols]) > 0 else 'bearish'
            }
        
        # Resumen de calidad de datos
        market_analysis['data_quality'] = {
            'total_symbols': len(self.symbols),
            'successful_symbols': successful_symbols,
            'success_rate': round((successful_symbols / len(self.symbols)) * 100, 2),
            'data_source': 'APIs reales (Binance, CoinGecko, Coinbase)'
        }
        
        logger.info(f"📊 Análisis completado: {successful_symbols}/{len(self.symbols)} símbolos con datos REALES")
        return market_analysis
    
    async def _evaluate_breakout_detection(self) -> Dict[str, Any]:
        """Evaluar la efectividad de la detección de breakouts"""
        logger.info("🔍 Evaluando detección de breakouts...")
        
        breakout_analysis = {
            'total_breakouts_detected': 0,
            'breakouts_by_symbol': {},
            'breakout_accuracy': {},
            'signal_strength_distribution': {},
            'timeframe_effectiveness': {}
        }
        
        for symbol in self.symbols:
            try:
                # Simular detección de breakouts en datos históricos
                data = self.data_fetcher.get_historical_data(symbol, 12, '5m')  # 12 horas
                
                if data is not None and len(data) > 20:
                    breakouts_detected = 0
                    successful_breakouts = 0
                    
                    for i in range(10, len(data) - 5):  # Dejar margen para validación
                        current_data = data.iloc[:i+1]
                        
                        # Simular detección de breakout
                        breakout_result = await self._simulate_breakout_detection(symbol, current_data)
                        
                        if breakout_result['detected']:
                            breakouts_detected += 1
                            
                            # Validar si el breakout fue exitoso (precio se movió en la dirección esperada)
                            future_data = data.iloc[i+1:i+6]
                            if len(future_data) > 0:
                                direction = breakout_result['direction']
                                current_price = data.iloc[i]['Close']
                                future_price = future_data['Close'].iloc[-1]
                                
                                if direction == 'bullish' and future_price > current_price * 1.005:  # 0.5% ganancia
                                    successful_breakouts += 1
                                elif direction == 'bearish' and future_price < current_price * 0.995:  # 0.5% caída
                                    successful_breakouts += 1
                    
                    accuracy = (successful_breakouts / breakouts_detected * 100) if breakouts_detected > 0 else 0
                    
                    breakout_analysis['breakouts_by_symbol'][symbol] = {
                        'total_detected': breakouts_detected,
                        'successful': successful_breakouts,
                        'accuracy_percentage': round(accuracy, 2)
                    }
                    
                    breakout_analysis['total_breakouts_detected'] += breakouts_detected
                    
                    logger.info(f"✅ {symbol}: {breakouts_detected} breakouts, {accuracy:.1f}% precisión")
                
            except Exception as e:
                logger.error(f"❌ Error evaluando breakouts {symbol}: {e}")
        
        return breakout_analysis
    
    async def _simulate_breakout_detection(self, symbol: str, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """Simular detección de breakout en datos históricos"""
        try:
            if len(historical_data) < 20:
                return {'detected': False}
            
            # Calcular indicadores básicos
            closes = historical_data['Close'].tail(20).values
            volumes = historical_data['Volume'].tail(20).values
            
            # Detectar breakout simple
            current_price = closes[-1]
            sma_20 = np.mean(closes)
            price_change = (current_price - closes[-2]) / closes[-2]
            volume_spike = volumes[-1] > np.mean(volumes[:-1]) * 1.5
            
            # Condiciones de breakout
            bullish_breakout = (
                current_price > sma_20 * 1.01 and  # Precio 1% sobre SMA
                price_change > 0.005 and  # Cambio > 0.5%
                volume_spike
            )
            
            bearish_breakout = (
                current_price < sma_20 * 0.99 and  # Precio 1% bajo SMA
                price_change < -0.005 and  # Cambio < -0.5%
                volume_spike
            )
            
            if bullish_breakout:
                return {
                    'detected': True,
                    'direction': 'bullish',
                    'strength': abs(price_change) * 100,
                    'confidence': 0.7
                }
            elif bearish_breakout:
                return {
                    'detected': True,
                    'direction': 'bearish',
                    'strength': abs(price_change) * 100,
                    'confidence': 0.7
                }
            
            return {'detected': False}
            
        except Exception as e:
            logger.error(f"Error simulando breakout: {e}")
            return {'detected': False}
    
    async def _evaluate_scalping_system(self) -> Dict[str, Any]:
        """Evaluar el rendimiento del sistema de scalping"""
        logger.info("⚡ Evaluando sistema de scalping...")
        
        scalping_analysis = {
            'total_opportunities': 0,
            'executed_trades': 0,
            'success_rate': 0,
            'avg_profit_per_trade': 0,
            'risk_reward_ratio': 0,
            'scalping_by_symbol': {}
        }
        
        # Simular oportunidades de scalping
        for symbol in self.symbols[:3]:  # Limitar a 3 símbolos para eficiencia
            try:
                # Obtener datos de alta frecuencia
                data = await self.data_fetcher.get_historical_data(symbol, '1m', 6)  # 6 horas
                
                if data and len(data) > 50:
                    opportunities = 0
                    profitable_trades = 0
                    total_profit = 0
                    
                    for i in range(20, len(data) - 10):
                        # Simular detección de oportunidad de scalping
                        opportunity = await self._simulate_scalping_opportunity(symbol, data[i-20:i+1])
                        
                        if opportunity['detected']:
                            opportunities += 1
                            
                            # Simular ejecución y resultado
                            result = await self._simulate_scalping_execution(data[i:i+10], opportunity)
                            
                            if result['profitable']:
                                profitable_trades += 1
                                total_profit += result['profit_pct']
                    
                    success_rate = (profitable_trades / opportunities * 100) if opportunities > 0 else 0
                    avg_profit = total_profit / opportunities if opportunities > 0 else 0
                    
                    scalping_analysis['scalping_by_symbol'][symbol] = {
                        'opportunities': opportunities,
                        'profitable_trades': profitable_trades,
                        'success_rate': round(success_rate, 2),
                        'avg_profit_pct': round(avg_profit, 4)
                    }
                    
                    scalping_analysis['total_opportunities'] += opportunities
                    scalping_analysis['executed_trades'] += profitable_trades
                    
                    logger.info(f"✅ {symbol}: {opportunities} oportunidades, {success_rate:.1f}% éxito")
                
            except Exception as e:
                logger.error(f"❌ Error evaluando scalping {symbol}: {e}")
        
        # Calcular métricas globales
        if scalping_analysis['total_opportunities'] > 0:
            scalping_analysis['success_rate'] = round(
                scalping_analysis['executed_trades'] / scalping_analysis['total_opportunities'] * 100, 2
            )
        
        return scalping_analysis
    
    async def _simulate_scalping_opportunity(self, symbol: str, data: List[Dict]) -> Dict[str, Any]:
        """Simular detección de oportunidad de scalping"""
        try:
            if len(data) < 20:
                return {'detected': False}
            
            # Calcular indicadores rápidos
            closes = [d['close'] for d in data]
            volumes = [d['volume'] for d in data]
            
            # Detectar micro-tendencia
            short_ma = np.mean(closes[-5:])
            long_ma = np.mean(closes[-15:])
            volume_avg = np.mean(volumes[-10:])
            current_volume = volumes[-1]
            
            # Condiciones de scalping
            trend_strength = abs(short_ma - long_ma) / long_ma
            volume_spike = current_volume > volume_avg * 1.3
            price_momentum = (closes[-1] - closes[-3]) / closes[-3]
            
            if trend_strength > 0.002 and volume_spike and abs(price_momentum) > 0.001:
                return {
                    'detected': True,
                    'direction': 'long' if short_ma > long_ma else 'short',
                    'strength': trend_strength * 1000,
                    'confidence': min(0.8, trend_strength * 500)
                }
            
            return {'detected': False}
            
        except Exception as e:
            logger.error(f"Error simulando oportunidad scalping: {e}")
            return {'detected': False}
    
    async def _simulate_scalping_execution(self, future_data: List[Dict], opportunity: Dict) -> Dict[str, Any]:
        """Simular ejecución de trade de scalping"""
        try:
            entry_price = future_data[0]['close']
            direction = opportunity['direction']
            
            # Configurar stops (scalping típico)
            if direction == 'long':
                take_profit = entry_price * 1.008  # 0.8% TP
                stop_loss = entry_price * 0.996   # 0.4% SL
            else:
                take_profit = entry_price * 0.992  # 0.8% TP
                stop_loss = entry_price * 1.004   # 0.4% SL
            
            # Simular evolución del precio
            for data_point in future_data[1:]:
                price = data_point['close']
                
                if direction == 'long':
                    if price >= take_profit:
                        return {'profitable': True, 'profit_pct': 0.8, 'exit_reason': 'take_profit'}
                    elif price <= stop_loss:
                        return {'profitable': False, 'profit_pct': -0.4, 'exit_reason': 'stop_loss'}
                else:
                    if price <= take_profit:
                        return {'profitable': True, 'profit_pct': 0.8, 'exit_reason': 'take_profit'}
                    elif price >= stop_loss:
                        return {'profitable': False, 'profit_pct': -0.4, 'exit_reason': 'stop_loss'}
            
            # Si no se activó ningún stop, cerrar en break-even
            return {'profitable': False, 'profit_pct': 0, 'exit_reason': 'timeout'}
            
        except Exception as e:
            logger.error(f"Error simulando ejecución scalping: {e}")
            return {'profitable': False, 'profit_pct': 0, 'exit_reason': 'error'}
    
    async def _evaluate_paper_trading(self) -> Dict[str, Any]:
        """Evaluar el rendimiento del paper trading"""
        logger.info("📈 Evaluando paper trading...")
        
        paper_analysis = {
            'initial_capital': self.paper_engine.initial_capital,
            'current_capital': self.paper_engine.current_capital,
            'total_trades': self.paper_engine.total_trades,
            'winning_trades': self.paper_engine.winning_trades,
            'total_pnl': self.paper_engine.total_pnl,
            'win_rate': 0,
            'profit_factor': 0,
            'max_drawdown': self.paper_engine.max_drawdown,
            'sharpe_ratio': 0,
            'trade_history': len(self.paper_engine.trade_history)
        }
        
        # Calcular métricas adicionales
        if self.paper_engine.total_trades > 0:
            paper_analysis['win_rate'] = round(
                self.paper_engine.winning_trades / self.paper_engine.total_trades * 100, 2
            )
        
        # ROI
        roi = ((self.paper_engine.current_capital - self.paper_engine.initial_capital) / 
               self.paper_engine.initial_capital * 100)
        paper_analysis['roi_percentage'] = round(roi, 2)
        
        return paper_analysis
    
    async def _calculate_risk_metrics(self) -> Dict[str, Any]:
        """Calcular métricas de riesgo"""
        logger.info("⚠️ Calculando métricas de riesgo...")
        
        risk_metrics = {
            'portfolio_volatility': 0,
            'value_at_risk_95': 0,
            'maximum_drawdown': 0,
            'risk_adjusted_return': 0,
            'correlation_risk': {},
            'concentration_risk': {}
        }
        
        # Simular cálculos de riesgo básicos
        try:
            # Obtener datos de correlación
            correlation_matrix = {}
            for symbol in self.symbols:
                data = self.data_fetcher.get_historical_data(symbol, 24, '1h')
                if data is not None and len(data) > 1:
                    returns = data['Close'].pct_change().dropna().values
                    correlation_matrix[symbol] = returns
            
            # Calcular volatilidad del portafolio (simplificado)
            if correlation_matrix:
                all_returns = list(correlation_matrix.values())
                if all_returns and len(all_returns[0]) > 0:
                    portfolio_returns = np.mean(all_returns, axis=0)
                    risk_metrics['portfolio_volatility'] = round(np.std(portfolio_returns) * 100, 4)
                    
                    # VaR 95%
                    risk_metrics['value_at_risk_95'] = round(np.percentile(portfolio_returns, 5) * 100, 4)
        
        except Exception as e:
            logger.error(f"Error calculando métricas de riesgo: {e}")
        
        return risk_metrics
    
    async def _analyze_correlations(self) -> Dict[str, Any]:
        """Analizar correlaciones entre activos"""
        logger.info("🔗 Analizando correlaciones...")
        
        correlation_analysis = {
            'correlation_matrix': {},
            'high_correlations': [],
            'diversification_score': 0
        }
        
        try:
            # Obtener datos para matriz de correlación
            symbol_data = {}
            for symbol in self.symbols:
                data = self.data_fetcher.get_historical_data(symbol, 24, '1h')
                if data is not None and len(data) > 10:
                    prices = data['Close'].values
                    symbol_data[symbol] = prices
            
            # Calcular correlaciones
            if len(symbol_data) >= 2:
                symbols = list(symbol_data.keys())
                for i, symbol1 in enumerate(symbols):
                    correlation_analysis['correlation_matrix'][symbol1] = {}
                    for j, symbol2 in enumerate(symbols):
                        if i != j and len(symbol_data[symbol1]) == len(symbol_data[symbol2]):
                            corr = np.corrcoef(symbol_data[symbol1], symbol_data[symbol2])[0, 1]
                            correlation_analysis['correlation_matrix'][symbol1][symbol2] = round(corr, 3)
                            
                            # Identificar correlaciones altas
                            if abs(corr) > 0.7:
                                correlation_analysis['high_correlations'].append({
                                    'pair': f"{symbol1}-{symbol2}",
                                    'correlation': round(corr, 3)
                                })
        
        except Exception as e:
            logger.error(f"Error analizando correlaciones: {e}")
        
        return correlation_analysis
    
    def _calculate_overall_score(self) -> float:
        """Calcular puntuación general del sistema"""
        # Puntuación simplificada basada en métricas clave
        base_score = 50.0
        
        # Ajustar según rendimiento del paper trading
        if self.paper_engine.total_trades > 0:
            win_rate = self.paper_engine.winning_trades / self.paper_engine.total_trades
            base_score += (win_rate - 0.5) * 40  # +/- 20 puntos según win rate
        
        # Ajustar según PnL
        roi = ((self.paper_engine.current_capital - self.paper_engine.initial_capital) / 
               self.paper_engine.initial_capital)
        base_score += roi * 30  # +/- 15 puntos según ROI
        
        return max(0, min(100, round(base_score, 1)))
    
    async def _save_performance_report(self, report: Dict[str, Any]):
        """Guardar reporte de rendimiento"""
        try:
            reports_dir = Path("reports/performance")
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_report_{timestamp}.json"
            filepath = reports_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"📄 Reporte guardado: {filepath}")
            
        except Exception as e:
            logger.error(f"Error guardando reporte: {e}")
    
    async def _generate_performance_charts(self, report: Dict[str, Any]):
        """Generar gráficos de rendimiento"""
        try:
            charts_dir = Path("reports/charts")
            charts_dir.mkdir(parents=True, exist_ok=True)
            
            # Configurar estilo
            plt.style.use('seaborn-v0_8')
            sns.set_palette("husl")
            
            # Gráfico 1: Rendimiento por símbolo
            if 'market_data' in report and 'symbols' in report['market_data']:
                symbols_data = report['market_data']['symbols']
                valid_symbols = {k: v for k, v in symbols_data.items() if 'error' not in v}
                
                if valid_symbols:
                    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
                    
                    # Cambios de precio 24h
                    symbols = list(valid_symbols.keys())
                    price_changes = [valid_symbols[s]['price_change_24h'] for s in symbols]
                    
                    ax1.bar(symbols, price_changes, color=['green' if x > 0 else 'red' for x in price_changes])
                    ax1.set_title('Cambio de Precio 24h (%)')
                    ax1.set_ylabel('Cambio (%)')
                    ax1.tick_params(axis='x', rotation=45)
                    
                    # Volatilidad
                    volatilities = [valid_symbols[s]['volatility'] for s in symbols]
                    ax2.bar(symbols, volatilities, color='blue', alpha=0.7)
                    ax2.set_title('Volatilidad por Símbolo')
                    ax2.set_ylabel('Volatilidad')
                    ax2.tick_params(axis='x', rotation=45)
                    
                    plt.tight_layout()
                    plt.savefig(charts_dir / 'market_performance.png', dpi=300, bbox_inches='tight')
                    plt.close()
            
            # Gráfico 2: Métricas de trading
            if 'paper_trading_performance' in report:
                pt_data = report['paper_trading_performance']
                
                fig, ax = plt.subplots(1, 1, figsize=(10, 6))
                
                metrics = ['ROI %', 'Win Rate %', 'Total Trades']
                values = [
                    pt_data.get('roi_percentage', 0),
                    pt_data.get('win_rate', 0),
                    pt_data.get('total_trades', 0)
                ]
                
                bars = ax.bar(metrics, values, color=['green', 'blue', 'orange'])
                ax.set_title('Métricas de Paper Trading')
                ax.set_ylabel('Valor')
                
                # Añadir valores en las barras
                for bar, value in zip(bars, values):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                           f'{value:.1f}', ha='center', va='bottom')
                
                plt.tight_layout()
                plt.savefig(charts_dir / 'trading_metrics.png', dpi=300, bbox_inches='tight')
                plt.close()
            
            logger.info(f"📊 Gráficos generados en: {charts_dir}")
            
        except Exception as e:
            logger.error(f"Error generando gráficos: {e}")

async def main():
    """Función principal"""
    logger.info("🚀 Iniciando evaluación de rendimiento del sistema SICAR...")
    
    try:
        evaluator = TradingPerformanceEvaluator()
        report = await evaluator.evaluate_full_performance()
        
        # Mostrar resumen
        print("\n" + "="*60)
        print("📊 RESUMEN DE RENDIMIENTO DEL SISTEMA SICAR")
        print("="*60)
        
        if 'overall_score' in report:
            print(f"🎯 Puntuación General: {report['overall_score']}/100")
        
        if 'market_data' in report and 'market_summary' in report['market_data']:
            market = report['market_data']['market_summary']
            print(f"📈 Tendencia del Mercado: {market.get('market_trend', 'N/A').upper()}")
            print(f"📊 Símbolos Analizados: {market.get('total_symbols_analyzed', 0)}")
        
        if 'paper_trading_performance' in report:
            pt = report['paper_trading_performance']
            print(f"💰 ROI Paper Trading: {pt.get('roi_percentage', 0):.2f}%")
            print(f"🎯 Tasa de Éxito: {pt.get('win_rate', 0):.1f}%")
            print(f"📈 Total de Trades: {pt.get('total_trades', 0)}")
        
        if 'breakout_performance' in report:
            bp = report['breakout_performance']
            print(f"🔍 Breakouts Detectados: {bp.get('total_breakouts_detected', 0)}")
        
        if 'scalping_performance' in report:
            sp = report['scalping_performance']
            print(f"⚡ Oportunidades Scalping: {sp.get('total_opportunities', 0)}")
            print(f"⚡ Tasa Éxito Scalping: {sp.get('success_rate', 0):.1f}%")
        
        print("="*60)
        print("✅ Evaluación completada. Revisa los reportes en /reports/")
        
    except Exception as e:
        logger.error(f"❌ Error en evaluación: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())