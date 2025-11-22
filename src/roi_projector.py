#!/usr/bin/env python3
"""
Sistema de Proyección de ROI Mensual para SICAR
Analiza datos históricos y proyecta rendimientos futuros basado en el comportamiento actual del bot.
"""

import sys
import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Agregar el directorio src al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pipelines.data_pipeline import DataPipeline
from module_2_regime import RegimeClassifier
from module_3_metacontroller import MetaController

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ROIProjector:
    """
    Clase para proyectar ROI mensual basado en datos históricos y comportamiento del bot.
    """
    
    def __init__(self, initial_capital: float = 500.0, risk_per_trade: float = 0.02):
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.data_pipeline = DataPipeline()
        self.regime_classifier = RegimeClassifier()
        self.metacontroller = MetaController()
        
        # Configuración de análisis
        self.timeframes = ['15m', '30m', '1h', '2h', '4h']
        self.confidence_threshold = 0.6
        
        # Resultados
        self.historical_analysis = {}
        self.projections = {}
        
    def analyze_historical_performance(self, symbol: str = 'BTCUSDT', 
                                     lookback_months: int = 6) -> Dict:
        """
        Analiza el rendimiento histórico basado en las decisiones que habría tomado SICAR.
        """
        logger.info(f"🔍 Analizando rendimiento histórico para {symbol}")
        
        try:
            # 1. Obtener datos históricos
            historical_data = self._get_historical_data(symbol, lookback_months)
            
            if historical_data.empty:
                logger.error("No se pudieron obtener datos históricos")
                return {}
            
            # 2. Simular decisiones de SICAR en datos históricos
            trades = self._simulate_sicar_decisions(historical_data)
            
            # 3. Calcular métricas de rendimiento
            performance_metrics = self._calculate_performance_metrics(trades)
            
            # 4. Análisis por régimen de mercado
            regime_analysis = self._analyze_performance_by_regime(trades, historical_data)
            
            # 5. Análisis de volatilidad y drawdown
            risk_metrics = self._calculate_risk_metrics(trades)
            
            self.historical_analysis = {
                'symbol': symbol,
                'period': f'{lookback_months} meses',
                'total_trades': len(trades),
                'performance_metrics': performance_metrics,
                'regime_analysis': regime_analysis,
                'risk_metrics': risk_metrics,
                'trades': trades,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Análisis histórico completado: {len(trades)} trades simulados")
            return self.historical_analysis
            
        except Exception as e:
            logger.error(f"Error en análisis histórico: {str(e)}")
            return {}
    
    def project_monthly_roi(self, scenarios: List[str] = None) -> Dict:
        """
        Proyecta ROI mensual basado en análisis histórico.
        """
        if scenarios is None:
            scenarios = ['conservador', 'moderado', 'optimista']
        
        logger.info("📊 Generando proyecciones de ROI mensual")
        
        if not self.historical_analysis:
            logger.error("Debe ejecutar analyze_historical_performance primero")
            return {}
        
        try:
            projections = {}
            
            for scenario in scenarios:
                projection = self._calculate_scenario_projection(scenario)
                projections[scenario] = projection
            
            # Análisis de probabilidades
            probability_analysis = self._calculate_probability_distributions()
            
            # Proyección de 12 meses
            monthly_projections = self._project_12_months(projections)
            
            self.projections = {
                'scenarios': projections,
                'probability_analysis': probability_analysis,
                'monthly_projections': monthly_projections,
                'base_metrics': self._extract_base_metrics(),
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("✅ Proyecciones ROI completadas")
            return self.projections
            
        except Exception as e:
            logger.error(f"Error en proyección ROI: {str(e)}")
            return {}
    
    def _get_historical_data(self, symbol: str, months: int) -> pd.DataFrame:
        """Obtiene datos históricos para análisis."""
        try:
            # Usar datos del cache si están disponibles
            cache_file = f"../data/cache/{symbol}_4h_cache.csv"
            
            if os.path.exists(cache_file):
                data = pd.read_csv(cache_file)
                data['timestamp'] = pd.to_datetime(data['timestamp'])
                data = data.set_index('timestamp')
                logger.info(f"📊 Datos históricos cargados: {len(data)} barras")
                return data
            else:
                # Obtener datos frescos
                data = self.data_pipeline.get_market_data(symbol, period=f"{months*30}d", interval="4h")
                return data
                
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos: {str(e)}")
            return pd.DataFrame()
    
    def _simulate_sicar_decisions(self, data: pd.DataFrame) -> List[Dict]:
        """Simula las decisiones que habría tomado SICAR en datos históricos."""
        trades = []
        current_position = None
        capital = self.initial_capital
        
        logger.info("🤖 Simulando decisiones de SICAR...")
        
        # Procesar datos en ventanas de 4h (como hace SICAR)
        for i in range(50, len(data), 1):  # Empezar después de 50 barras para indicadores
            try:
                # Obtener ventana de datos
                window_data = data.iloc[max(0, i-100):i+1]
                
                if len(window_data) < 50:
                    continue
                
                # Simular análisis multi-timeframe simplificado
                decision = self._simulate_decision_logic(window_data)
                
                current_price = data.iloc[i]['Close']
                timestamp = data.index[i]
                
                # Procesar decisión
                if decision['action'] == 'BUY' and current_position is None:
                    # Abrir posición larga
                    position_size = capital * self.risk_per_trade
                    shares = position_size / current_price
                    
                    current_position = {
                        'type': 'LONG',
                        'entry_price': current_price,
                        'entry_time': timestamp,
                        'shares': shares,
                        'confidence': decision['confidence']
                    }
                    
                elif decision['action'] == 'SELL' and current_position is not None:
                    # Cerrar posición
                    exit_price = current_price
                    pnl = (exit_price - current_position['entry_price']) * current_position['shares']
                    roi = pnl / (current_position['entry_price'] * current_position['shares'])
                    
                    trade = {
                        'entry_time': current_position['entry_time'],
                        'exit_time': timestamp,
                        'entry_price': current_position['entry_price'],
                        'exit_price': exit_price,
                        'shares': current_position['shares'],
                        'pnl': pnl,
                        'roi': roi,
                        'duration_hours': (timestamp - current_position['entry_time']).total_seconds() / 3600,
                        'entry_confidence': current_position['confidence'],
                        'exit_confidence': decision['confidence']
                    }
                    
                    trades.append(trade)
                    capital += pnl
                    current_position = None
                    
            except Exception as e:
                logger.warning(f"Error simulando decisión en {i}: {str(e)}")
                continue
        
        logger.info(f"🎯 Simulación completada: {len(trades)} trades generados")
        return trades
    
    def _simulate_decision_logic(self, data: pd.DataFrame) -> Dict:
        """Simula la lógica de decisión de SICAR de forma simplificada."""
        try:
            # Calcular indicadores básicos
            close_prices = data['Close']
            
            # RSI
            rsi = self._calculate_rsi(close_prices)
            
            # MACD
            macd_line, macd_signal = self._calculate_macd(close_prices)
            
            # Tendencia (SMA)
            sma_20 = close_prices.rolling(20).mean()
            sma_50 = close_prices.rolling(50).mean()
            
            # Lógica de decisión simplificada (similar a SICAR)
            latest_rsi = rsi.iloc[-1] if not rsi.empty else 50
            latest_macd = macd_line.iloc[-1] - macd_signal.iloc[-1] if len(macd_line) > 0 else 0
            trend_signal = 1 if sma_20.iloc[-1] > sma_50.iloc[-1] else -1
            
            # Calcular señal compuesta
            signal_strength = 0
            confidence = 0.5
            
            # Señales de compra
            if latest_rsi < 30 and latest_macd > 0 and trend_signal > 0:
                signal_strength = 1
                confidence = 0.8
            elif latest_rsi < 40 and latest_macd > 0:
                signal_strength = 1
                confidence = 0.65
            
            # Señales de venta
            elif latest_rsi > 70 and latest_macd < 0 and trend_signal < 0:
                signal_strength = -1
                confidence = 0.8
            elif latest_rsi > 60 and latest_macd < 0:
                signal_strength = -1
                confidence = 0.65
            
            # Determinar acción
            if signal_strength > 0 and confidence >= self.confidence_threshold:
                action = 'BUY'
            elif signal_strength < 0 and confidence >= self.confidence_threshold:
                action = 'SELL'
            else:
                action = 'HOLD'
            
            return {
                'action': action,
                'confidence': confidence,
                'signal_strength': signal_strength,
                'rsi': latest_rsi,
                'macd': latest_macd,
                'trend': trend_signal
            }
            
        except Exception as e:
            logger.warning(f"Error en lógica de decisión: {str(e)}")
            return {'action': 'HOLD', 'confidence': 0.5, 'signal_strength': 0}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series]:
        """Calcula MACD."""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        macd_line = ema_12 - ema_26
        macd_signal = macd_line.ewm(span=9).mean()
        return macd_line, macd_signal
    
    def _calculate_performance_metrics(self, trades: List[Dict]) -> Dict:
        """Calcula métricas de rendimiento."""
        if not trades:
            return {'error': 'No hay trades para analizar'}
        
        # Métricas básicas
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        losing_trades = len([t for t in trades if t['pnl'] < 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # PnL total y ROI
        total_pnl = sum(t['pnl'] for t in trades)
        total_roi = total_pnl / self.initial_capital
        
        # ROI promedio por trade
        avg_roi_per_trade = np.mean([t['roi'] for t in trades])
        
        # Mejor y peor trade
        best_trade = max(trades, key=lambda x: x['roi'])
        worst_trade = min(trades, key=lambda x: x['roi'])
        
        # Duración promedio
        avg_duration = np.mean([t['duration_hours'] for t in trades])
        
        # Trades por mes (estimado)
        if trades:
            time_span = (trades[-1]['exit_time'] - trades[0]['entry_time']).days
            trades_per_month = (total_trades / time_span) * 30 if time_span > 0 else 0
        else:
            trades_per_month = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_roi': total_roi,
            'avg_roi_per_trade': avg_roi_per_trade,
            'best_trade_roi': best_trade['roi'],
            'worst_trade_roi': worst_trade['roi'],
            'avg_duration_hours': avg_duration,
            'trades_per_month': trades_per_month
        }
    
    def _analyze_performance_by_regime(self, trades: List[Dict], data: pd.DataFrame) -> Dict:
        """Analiza rendimiento por régimen de mercado."""
        # Simplificado: clasificar por volatilidad
        volatility = data['Close'].pct_change().rolling(20).std()
        
        regime_trades = {'low_vol': [], 'medium_vol': [], 'high_vol': []}
        
        for trade in trades:
            # Encontrar volatilidad en el momento del trade
            trade_time = trade['entry_time']
            try:
                vol_at_trade = volatility.loc[trade_time:trade_time].iloc[0]
                
                if vol_at_trade < volatility.quantile(0.33):
                    regime_trades['low_vol'].append(trade)
                elif vol_at_trade < volatility.quantile(0.66):
                    regime_trades['medium_vol'].append(trade)
                else:
                    regime_trades['high_vol'].append(trade)
            except:
                regime_trades['medium_vol'].append(trade)
        
        # Calcular métricas por régimen
        regime_analysis = {}
        for regime, regime_trade_list in regime_trades.items():
            if regime_trade_list:
                regime_analysis[regime] = {
                    'trades': len(regime_trade_list),
                    'win_rate': len([t for t in regime_trade_list if t['pnl'] > 0]) / len(regime_trade_list),
                    'avg_roi': np.mean([t['roi'] for t in regime_trade_list]),
                    'total_pnl': sum(t['pnl'] for t in regime_trade_list)
                }
            else:
                regime_analysis[regime] = {'trades': 0, 'win_rate': 0, 'avg_roi': 0, 'total_pnl': 0}
        
        return regime_analysis
    
    def _calculate_risk_metrics(self, trades: List[Dict]) -> Dict:
        """Calcula métricas de riesgo."""
        if not trades:
            return {}
        
        # Drawdown máximo
        cumulative_pnl = np.cumsum([t['pnl'] for t in trades])
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = (cumulative_pnl - running_max) / self.initial_capital
        max_drawdown = np.min(drawdown)
        
        # Volatilidad de returns
        returns = [t['roi'] for t in trades]
        volatility = np.std(returns)
        
        # Sharpe ratio (simplificado, asumiendo risk-free rate = 0)
        avg_return = np.mean(returns)
        sharpe_ratio = avg_return / volatility if volatility > 0 else 0
        
        return {
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'avg_return': avg_return
        }
    
    def _calculate_scenario_projection(self, scenario: str) -> Dict:
        """Calcula proyección para un escenario específico."""
        base_metrics = self.historical_analysis['performance_metrics']
        
        # Factores de ajuste por escenario
        scenario_factors = {
            'conservador': {
                'roi_multiplier': 0.7,
                'trade_frequency_multiplier': 0.8,
                'win_rate_adjustment': -0.05,
                'description': 'Proyección conservadora con menor frecuencia de trades'
            },
            'moderado': {
                'roi_multiplier': 1.0,
                'trade_frequency_multiplier': 1.0,
                'win_rate_adjustment': 0.0,
                'description': 'Proyección basada en rendimiento histórico actual'
            },
            'optimista': {
                'roi_multiplier': 1.3,
                'trade_frequency_multiplier': 1.2,
                'win_rate_adjustment': 0.05,
                'description': 'Proyección optimista con mejora en performance'
            }
        }
        
        factors = scenario_factors[scenario]
        
        # Calcular métricas proyectadas
        projected_trades_per_month = base_metrics['trades_per_month'] * factors['trade_frequency_multiplier']
        projected_avg_roi = base_metrics['avg_roi_per_trade'] * factors['roi_multiplier']
        projected_win_rate = min(0.95, base_metrics['win_rate'] + factors['win_rate_adjustment'])
        
        # ROI mensual proyectado
        monthly_roi = projected_trades_per_month * projected_avg_roi * projected_win_rate
        
        return {
            'scenario': scenario,
            'description': factors['description'],
            'projected_trades_per_month': projected_trades_per_month,
            'projected_avg_roi_per_trade': projected_avg_roi,
            'projected_win_rate': projected_win_rate,
            'projected_monthly_roi': monthly_roi,
            'projected_annual_roi': monthly_roi * 12,
            'factors_applied': factors
        }
    
    def _calculate_probability_distributions(self) -> Dict:
        """Calcula distribuciones de probabilidad para ROI."""
        trades = self.historical_analysis['trades']
        
        if not trades:
            return {}
        
        returns = [t['roi'] for t in trades]
        
        # Percentiles
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        percentile_values = np.percentile(returns, percentiles)
        
        # Probabilidad de ROI positivo
        positive_roi_prob = len([r for r in returns if r > 0]) / len(returns)
        
        # Probabilidad de ROI > 5%
        high_roi_prob = len([r for r in returns if r > 0.05]) / len(returns)
        
        return {
            'percentiles': dict(zip(percentiles, percentile_values)),
            'positive_roi_probability': positive_roi_prob,
            'high_roi_probability': high_roi_prob,
            'mean_return': np.mean(returns),
            'std_return': np.std(returns)
        }
    
    def _project_12_months(self, scenarios: Dict) -> Dict:
        """Proyecta ROI para los próximos 12 meses."""
        monthly_projections = {}
        
        for scenario_name, scenario_data in scenarios.items():
            monthly_roi = scenario_data['projected_monthly_roi']
            
            # Proyección mes a mes con compounding
            capital = self.initial_capital
            monthly_data = []
            
            for month in range(1, 13):
                monthly_return = capital * monthly_roi
                capital += monthly_return
                
                monthly_data.append({
                    'month': month,
                    'capital': capital,
                    'monthly_return': monthly_return,
                    'cumulative_roi': (capital - self.initial_capital) / self.initial_capital
                })
            
            monthly_projections[scenario_name] = monthly_data
        
        return monthly_projections
    
    def _extract_base_metrics(self) -> Dict:
        """Extrae métricas base para referencia."""
        return {
            'initial_capital': self.initial_capital,
            'risk_per_trade': self.risk_per_trade,
            'confidence_threshold': self.confidence_threshold,
            'analysis_period': self.historical_analysis.get('period', 'N/A'),
            'total_historical_trades': self.historical_analysis.get('total_trades', 0)
        }
    
    def generate_report(self) -> str:
        """Genera reporte completo de proyección ROI."""
        if not self.projections:
            return "Error: Debe ejecutar project_monthly_roi() primero"
        
        report_lines = [
            "💰 === REPORTE DE PROYECCIÓN ROI MENSUAL SICAR ===",
            "=" * 60,
            f"📅 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"💵 Capital inicial: ${self.initial_capital:,.2f}",
            f"⚠️ Riesgo por trade: {self.risk_per_trade:.1%}",
            "",
            "📊 ANÁLISIS HISTÓRICO:",
            f"   🔍 Período analizado: {self.historical_analysis.get('period', 'N/A')}",
            f"   📈 Total trades simulados: {self.historical_analysis.get('total_trades', 0)}",
            f"   🎯 Win rate: {self.historical_analysis['performance_metrics']['win_rate']:.1%}",
            f"   💰 ROI total histórico: {self.historical_analysis['performance_metrics']['total_roi']:.1%}",
            "",
            "🎯 PROYECCIONES ROI MENSUAL:",
        ]
        
        # Agregar proyecciones por escenario
        for scenario, data in self.projections['scenarios'].items():
            report_lines.extend([
                f"",
                f"📋 ESCENARIO {scenario.upper()}:",
                f"   📝 {data['description']}",
                f"   📊 Trades/mes: {data['projected_trades_per_month']:.1f}",
                f"   🎯 Win rate: {data['projected_win_rate']:.1%}",
                f"   💰 ROI mensual: {data['projected_monthly_roi']:.1%}",
                f"   🚀 ROI anual: {data['projected_annual_roi']:.1%}",
            ])
        
        # Agregar análisis de probabilidades
        prob_data = self.projections['probability_analysis']
        if prob_data:
            report_lines.extend([
                "",
                "📊 ANÁLISIS DE PROBABILIDADES:",
                f"   ✅ Prob. ROI positivo: {prob_data['positive_roi_probability']:.1%}",
                f"   🚀 Prob. ROI > 5%: {prob_data['high_roi_probability']:.1%}",
                f"   📈 Return promedio: {prob_data['mean_return']:.1%}",
                f"   📊 Volatilidad: {prob_data['std_return']:.1%}",
            ])
        
        # Proyección a 12 meses
        report_lines.extend([
            "",
            "📅 PROYECCIÓN 12 MESES (Escenario Moderado):",
        ])
        
        moderate_projection = self.projections['monthly_projections']['moderado']
        for month_data in moderate_projection[::3]:  # Cada 3 meses
            month = month_data['month']
            capital = month_data['capital']
            roi = month_data['cumulative_roi']
            report_lines.append(f"   Mes {month:2d}: ${capital:8,.2f} (ROI: {roi:6.1%})")
        
        report_lines.extend([
            "",
            "⚠️ DISCLAIMER:",
            "   • Proyecciones basadas en análisis histórico",
            "   • Resultados pasados no garantizan rendimientos futuros",
            "   • Considerar siempre el riesgo de pérdidas",
            "   • Diversificar inversiones apropiadamente",
            "",
            "✅ Reporte generado exitosamente"
        ])
        
        return "\n".join(report_lines)
    
    def save_results(self, filename: str = None):
        """Guarda resultados en archivo JSON."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"roi_projection_{timestamp}.json"
        
        results = {
            'historical_analysis': self.historical_analysis,
            'projections': self.projections,
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'initial_capital': self.initial_capital,
                'risk_per_trade': self.risk_per_trade
            }
        }
        
        filepath = f"../reports/{filename}"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Resultados guardados en: {filepath}")
        return filepath


def main():
    """Función principal para ejecutar análisis de ROI."""
    print("💰 === ANÁLISIS DE PROYECCIÓN ROI MENSUAL SICAR ===")
    print(f"⏰ Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Inicializar proyector
        projector = ROIProjector(initial_capital=500.0, risk_per_trade=0.02)
        
        # Análisis histórico
        print("🔍 Ejecutando análisis histórico...")
        historical_results = projector.analyze_historical_performance('BTCUSDT', lookback_months=6)
        
        if not historical_results:
            print("❌ Error en análisis histórico")
            return
        
        # Proyecciones
        print("📊 Generando proyecciones ROI...")
        projections = projector.project_monthly_roi()
        
        if not projections:
            print("❌ Error en proyecciones")
            return
        
        # Generar reporte
        print("📋 Generando reporte...")
        report = projector.generate_report()
        print("\n" + report)
        
        # Guardar resultados
        filepath = projector.save_results()
        print(f"\n💾 Resultados guardados en: {filepath}")
        
        print("\n✅ Análisis completado exitosamente")
        
    except Exception as e:
        logger.error(f"Error en análisis principal: {str(e)}")
        print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    main()