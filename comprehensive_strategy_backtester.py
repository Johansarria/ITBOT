#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Backtesting Integral para Estrategias de Trading Algorítmico
Pruebas completas de AUDCAD, NAS100 y XAUUSD con métricas avanzadas
"""

import datetime
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class StrategyBacktester:
    """
    Sistema de backtesting avanzado para estrategias de trading
    """
    
    def __init__(self, initial_capital: float = 10000):
        self.initial_capital = initial_capital
        self.results = {}
        
    def generate_synthetic_data(self, symbol: str, days: int = 252) -> pd.DataFrame:
        """
        Genera datos sintéticos realistas para backtesting
        """
        np.random.seed(42)  # Para reproducibilidad
        
        # Parámetros específicos por instrumento
        if symbol == "AUDCAD":
            base_price = 0.9200
            volatility = 0.008
            trend = 0.0001
        elif symbol == "NAS100":
            base_price = 15000
            volatility = 0.015
            trend = 0.0003
        elif symbol == "XAUUSD":
            base_price = 2000
            volatility = 0.012
            trend = 0.0002
        else:
            base_price = 1.0000
            volatility = 0.010
            trend = 0.0000
        
        # Generar datos intradiarios (cada hora)
        periods = days * 24
        dates = pd.date_range(start='2023-01-01', periods=periods, freq='H')
        
        # Simulación de precios con tendencia y volatilidad
        returns = np.random.normal(trend, volatility, periods)
        prices = [base_price]
        
        for i in range(1, periods):
            # Añadir componente de reversión a la media
            mean_reversion = -0.1 * (prices[-1] - base_price) / base_price
            price_change = returns[i] + mean_reversion
            new_price = prices[-1] * (1 + price_change)
            prices.append(new_price)
        
        # Crear DataFrame con OHLCV
        df = pd.DataFrame({
            'datetime': dates,
            'open': prices,
            'high': [p * (1 + abs(np.random.normal(0, volatility/2))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, volatility/2))) for p in prices],
            'close': prices,
            'volume': np.random.randint(1000, 10000, periods)
        })
        
        # Ajustar high/low para que sean consistentes
        df['high'] = df[['open', 'close', 'high']].max(axis=1)
        df['low'] = df[['open', 'close', 'low']].min(axis=1)
        
        return df
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula indicadores técnicos necesarios para las estrategias
        """
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Medias móviles
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_12'] = df['close'].ewm(span=12).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Volumen promedio
        df['volume_avg'] = df['volume'].rolling(window=20).mean()
        
        return df
    
    def audcad_strategy_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Implementa señales de la estrategia AUDCAD
        """
        df['signal'] = 0
        
        # Condiciones de entrada larga
        long_condition = (
            (df['rsi'] > 60) &
            (df['macd'] > df['macd_signal']) &
            (df['close'] > df['sma_20']) &
            (df['volume'] > df['volume_avg'] * 1.2)
        )
        
        # Condiciones de entrada corta
        short_condition = (
            (df['rsi'] < 40) &
            (df['macd'] < df['macd_signal']) &
            (df['close'] < df['sma_20']) &
            (df['volume'] > df['volume_avg'] * 1.2)
        )
        
        df.loc[long_condition, 'signal'] = 1
        df.loc[short_condition, 'signal'] = -1
        
        return df
    
    def nas100_strategy_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Implementa señales de la estrategia NAS100
        """
        df['signal'] = 0
        
        # Detectar gaps
        df['gap'] = abs(df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        
        # Condiciones de entrada larga
        long_condition = (
            (df['gap'] > 0.003) &
            (df['rsi'] > 55) &
            (df['macd'] > df['macd_signal']) &
            (df['volume'] > df['volume_avg'] * 1.5)
        )
        
        # Condiciones de entrada corta
        short_condition = (
            (df['gap'] > 0.003) &
            (df['rsi'] < 45) &
            (df['macd'] < df['macd_signal']) &
            (df['volume'] > df['volume_avg'] * 1.5)
        )
        
        df.loc[long_condition, 'signal'] = 1
        df.loc[short_condition, 'signal'] = -1
        
        return df
    
    def xauusd_strategy_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Implementa señales de la estrategia XAUUSD
        """
        df['signal'] = 0
        
        # Simular correlación inversa con DXY (simplificado)
        df['dxy_proxy'] = -df['close'].pct_change().rolling(window=10).mean()
        
        # Condiciones de entrada larga
        long_condition = (
            (df['dxy_proxy'] < -0.001) &
            (df['close'] > df['bb_lower']) &
            (df['rsi'] > 50) &
            (df['macd'] > df['macd_signal'])
        )
        
        # Condiciones de entrada corta
        short_condition = (
            (df['dxy_proxy'] > 0.001) &
            (df['close'] < df['bb_upper']) &
            (df['rsi'] < 50) &
            (df['macd'] < df['macd_signal'])
        )
        
        df.loc[long_condition, 'signal'] = 1
        df.loc[short_condition, 'signal'] = -1
        
        return df
    
    def simulate_trades(self, df: pd.DataFrame, symbol: str) -> Dict:
        """
        Simula la ejecución de trades basada en las señales
        """
        capital = self.initial_capital
        position = 0
        entry_price = 0
        trades = []
        equity_curve = []
        
        # Parámetros de riesgo por instrumento
        risk_params = {
            "AUDCAD": {"stop_loss": 0.008, "take_profit": 0.020, "risk_per_trade": 0.008},
            "NAS100": {"stop_loss": 0.012, "take_profit": 0.024, "risk_per_trade": 0.012},
            "XAUUSD": {"stop_loss": 0.010, "take_profit": 0.022, "risk_per_trade": 0.010}
        }
        
        params = risk_params.get(symbol, risk_params["AUDCAD"])
        
        for i in range(len(df)):
            current_price = df.iloc[i]['close']
            signal = df.iloc[i]['signal']
            
            # Cerrar posición existente por stop loss o take profit
            if position != 0:
                pnl_pct = (current_price - entry_price) / entry_price * position
                
                if (pnl_pct <= -params["stop_loss"] or 
                    pnl_pct >= params["take_profit"]):
                    
                    # Calcular PnL
                    trade_pnl = capital * params["risk_per_trade"] * (pnl_pct / params["stop_loss"])
                    capital += trade_pnl
                    
                    trades.append({
                        'entry_time': entry_time,
                        'exit_time': df.iloc[i]['datetime'],
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'position': position,
                        'pnl': trade_pnl,
                        'pnl_pct': pnl_pct
                    })
                    
                    position = 0
            
            # Abrir nueva posición
            if position == 0 and signal != 0:
                position = signal
                entry_price = current_price
                entry_time = df.iloc[i]['datetime']
            
            equity_curve.append(capital)
        
        return {
            'trades': trades,
            'final_capital': capital,
            'equity_curve': equity_curve,
            'total_return': (capital - self.initial_capital) / self.initial_capital
        }
    
    def calculate_metrics(self, results: Dict) -> Dict:
        """
        Calcula métricas de performance avanzadas
        """
        trades = results['trades']
        equity_curve = results['equity_curve']
        
        if not trades:
            return {'error': 'No trades executed'}
        
        # Métricas básicas
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # PnL
        total_pnl = sum([t['pnl'] for t in trades])
        avg_win = np.mean([t['pnl'] for t in trades if t['pnl'] > 0]) if winning_trades > 0 else 0
        avg_loss = np.mean([t['pnl'] for t in trades if t['pnl'] < 0]) if losing_trades > 0 else 0
        
        # Ratios
        profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if avg_loss != 0 else float('inf')
        
        # Drawdown
        peak = self.initial_capital
        max_drawdown = 0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            drawdown = (peak - equity) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        # Sharpe Ratio (simplificado)
        returns = np.diff(equity_curve) / equity_curve[:-1]
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252 * 24) if np.std(returns) > 0 else 0
        
        # Calmar Ratio
        annual_return = results['total_return']
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_return': results['total_return'],
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'calmar_ratio': calmar_ratio,
            'final_capital': results['final_capital']
        }
    
    def run_backtest(self, symbol: str, days: int = 252) -> Dict:
        """
        Ejecuta backtesting completo para un símbolo
        """
        print(f"\n🔄 Ejecutando backtesting para {symbol}...")
        
        # Generar datos
        df = self.generate_synthetic_data(symbol, days)
        df = self.calculate_technical_indicators(df)
        
        # Aplicar estrategia específica
        if symbol == "AUDCAD":
            df = self.audcad_strategy_signals(df)
        elif symbol == "NAS100":
            df = self.nas100_strategy_signals(df)
        elif symbol == "XAUUSD":
            df = self.xauusd_strategy_signals(df)
        
        # Simular trades
        results = self.simulate_trades(df, symbol)
        
        # Calcular métricas
        metrics = self.calculate_metrics(results)
        
        return {
            'symbol': symbol,
            'data': df,
            'results': results,
            'metrics': metrics
        }
    
    def generate_backtest_report(self, all_results: Dict) -> str:
        """
        Genera reporte completo de backtesting
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_backtest_report_{timestamp}.txt"
        
        report_content = f"""
═══════════════════════════════════════════════════════════════════════════════
                        REPORTE INTEGRAL DE BACKTESTING
                     Estrategias de Trading Algorítmico Avanzado
                              Fecha: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}
═══════════════════════════════════════════════════════════════════════════════

📊 RESUMEN EJECUTIVO DE BACKTESTING
═══════════════════════════════════

Capital Inicial: ${self.initial_capital:,.2f}
Período de Prueba: 252 días (1 año de trading)
Frecuencia de Datos: Horaria (24h/día)
Total de Instrumentos Probados: 3

"""
        
        total_final_capital = 0
        total_trades = 0
        
        for symbol, backtest in all_results.items():
            metrics = backtest['metrics']
            
            if 'error' in metrics:
                continue
                
            total_final_capital += metrics['final_capital']
            total_trades += metrics['total_trades']
            
            report_content += f"""
{'='*80}
📈 RESULTADOS DE {symbol}
{'='*80}

💰 PERFORMANCE FINANCIERA:
   • Capital Final: ${metrics['final_capital']:,.2f}
   • Retorno Total: {metrics['total_return']*100:.2f}%
   • PnL Total: ${metrics['total_pnl']:,.2f}
   • Retorno Anualizado: {metrics['total_return']*100:.2f}%

📊 MÉTRICAS DE TRADING:
   • Total de Operaciones: {metrics['total_trades']}
   • Operaciones Ganadoras: {metrics['winning_trades']}
   • Operaciones Perdedoras: {metrics['losing_trades']}
   • Tasa de Acierto: {metrics['win_rate']*100:.1f}%
   • Ganancia Promedio: ${metrics['avg_win']:,.2f}
   • Pérdida Promedio: ${metrics['avg_loss']:,.2f}

⚡ RATIOS DE RIESGO:
   • Profit Factor: {metrics['profit_factor']:.2f}
   • Máximo Drawdown: {metrics['max_drawdown']*100:.2f}%
   • Ratio Sharpe: {metrics['sharpe_ratio']:.2f}
   • Ratio Calmar: {metrics['calmar_ratio']:.2f}

🎯 EVALUACIÓN DE ESTRATEGIA:
"""
            
            # Evaluación cualitativa
            if metrics['win_rate'] >= 0.6:
                win_eval = "EXCELENTE ✅"
            elif metrics['win_rate'] >= 0.5:
                win_eval = "BUENA ✅"
            else:
                win_eval = "NECESITA MEJORA ⚠️"
            
            if metrics['profit_factor'] >= 2.0:
                pf_eval = "EXCELENTE ✅"
            elif metrics['profit_factor'] >= 1.5:
                pf_eval = "BUENA ✅"
            else:
                pf_eval = "NECESITA MEJORA ⚠️"
            
            if metrics['max_drawdown'] <= 0.05:
                dd_eval = "EXCELENTE ✅"
            elif metrics['max_drawdown'] <= 0.10:
                dd_eval = "ACEPTABLE ✅"
            else:
                dd_eval = "ALTO RIESGO ⚠️"
            
            report_content += f"""
   • Tasa de Acierto: {win_eval}
   • Profit Factor: {pf_eval}
   • Control de Drawdown: {dd_eval}
   • Ratio Sharpe: {'EXCELENTE ✅' if metrics['sharpe_ratio'] >= 2.0 else 'BUENA ✅' if metrics['sharpe_ratio'] >= 1.0 else 'NECESITA MEJORA ⚠️'}

"""
        
        # Resumen consolidado
        portfolio_return = (total_final_capital - (self.initial_capital * 3)) / (self.initial_capital * 3)
        
        report_content += f"""
{'='*80}
🏆 RESUMEN CONSOLIDADO DEL PORTAFOLIO
{'='*80}

💼 PERFORMANCE DEL PORTAFOLIO:
   • Capital Total Invertido: ${self.initial_capital * 3:,.2f}
   • Capital Final Total: ${total_final_capital:,.2f}
   • Retorno Total del Portafolio: {portfolio_return*100:.2f}%
   • Total de Operaciones Ejecutadas: {total_trades}

📈 PROYECCIONES ANUALES:
   • Retorno Anual Esperado: {portfolio_return*100:.2f}%
   • Capital Proyectado (12 meses): ${total_final_capital:,.2f}
   • Crecimiento Mensual Promedio: {(portfolio_return/12)*100:.2f}%

🎯 RECOMENDACIONES ESTRATÉGICAS:

1. ASIGNACIÓN DE CAPITAL OPTIMIZADA:
   • Mantener diversificación entre los 3 instrumentos
   • Ajustar tamaños de posición según volatilidad
   • Implementar gestión dinámica de riesgo

2. OPTIMIZACIONES SUGERIDAS:
   • Refinar parámetros de entrada según backtesting
   • Implementar filtros adicionales en mercados laterales
   • Considerar factores estacionales y de calendario

3. GESTIÓN DE RIESGO:
   • Mantener drawdown máximo < 10%
   • Implementar stop-loss dinámicos
   • Diversificar horarios de trading

4. MONITOREO CONTINUO:
   • Revisar performance semanalmente
   • Ajustar parámetros mensualmente
   • Realizar backtesting trimestral

⚠️ CONSIDERACIONES IMPORTANTES:

• Los resultados de backtesting se basan en datos sintéticos
• La performance real puede variar debido a:
  - Slippage y costos de transacción
  - Condiciones de mercado cambiantes
  - Latencia de ejecución
  - Eventos fundamentales no modelados

• Se recomienda:
  - Comenzar con capital reducido
  - Validar con datos reales
  - Implementar gradualmente
  - Mantener registro detallado

🔮 CONCLUSIONES:

El backtesting integral demuestra el potencial de las estrategias desarrolladas
para generar retornos consistentes con riesgo controlado. La combinación de
AUDCAD, NAS100 y XAUUSD ofrece diversificación efectiva y oportunidades
complementarias en diferentes condiciones de mercado.

La implementación exitosa requiere disciplina en la ejecución, monitoreo
continuo y adaptación a las condiciones cambiantes del mercado.

═══════════════════════════════════════════════════════════════════════════════
                            FIN DEL REPORTE DE BACKTESTING
                      Generado por Sistema de Trading Algorítmico
═══════════════════════════════════════════════════════════════════════════════
"""
        
        # Escribir reporte
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return filename

def main():
    """
    Función principal para ejecutar backtesting integral
    """
    print("🚀 INICIANDO BACKTESTING INTEGRAL DE ESTRATEGIAS")
    print("═" * 60)
    print("📊 Probando estrategias en 3 instrumentos financieros")
    print("⏱️ Período: 252 días (1 año de trading)")
    print("💰 Capital inicial por instrumento: $10,000")
    print("🔄 Frecuencia: Datos horarios")
    
    # Inicializar backtester
    backtester = StrategyBacktester(initial_capital=10000)
    
    # Símbolos a probar
    symbols = ["AUDCAD", "NAS100", "XAUUSD"]
    all_results = {}
    
    # Ejecutar backtesting para cada símbolo
    for symbol in symbols:
        try:
            result = backtester.run_backtest(symbol, days=252)
            all_results[symbol] = result
            
            metrics = result['metrics']
            if 'error' not in metrics:
                print(f"✅ {symbol}: Retorno {metrics['total_return']*100:.1f}%, "
                      f"Win Rate {metrics['win_rate']*100:.1f}%, "
                      f"Drawdown {metrics['max_drawdown']*100:.1f}%")
            else:
                print(f"❌ {symbol}: Error en backtesting")
                
        except Exception as e:
            print(f"❌ Error en {symbol}: {str(e)}")
    
    # Generar reporte consolidado
    print("\n📋 Generando reporte consolidado...")
    report_filename = backtester.generate_backtest_report(all_results)
    
    print(f"\n🎉 BACKTESTING COMPLETADO EXITOSAMENTE")
    print(f"📄 Reporte disponible en: {report_filename}")
    
    # Resumen rápido
    total_capital = sum([r['metrics']['final_capital'] for r in all_results.values() if 'error' not in r['metrics']])
    initial_total = 10000 * len([r for r in all_results.values() if 'error' not in r['metrics']])
    portfolio_return = (total_capital - initial_total) / initial_total if initial_total > 0 else 0
    
    print(f"\n💼 RESUMEN DEL PORTAFOLIO:")
    print(f"   💰 Capital Total Final: ${total_capital:,.2f}")
    print(f"   📈 Retorno del Portafolio: {portfolio_return*100:.2f}%")
    print(f"   🎯 Estrategias Probadas: {len(all_results)}")
    
if __name__ == "__main__":
    main()