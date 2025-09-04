#!/usr/bin/env python3
"""
BACKTESTING Q1-Q2 2025 - ESTRATEGIAS V3
=====================================
Pruebas de rendimiento para los primeros dos trimestres del año 2025
con las estrategias V3 optimizadas.

Períodos a evaluar:
- Q1 2025: 1 enero - 31 marzo 2025
- Q2 2025: 1 abril - 30 junio 2025
- H1 2025: 1 enero - 30 junio 2025 (semestre completo)
"""

import asyncio
import pandas as pd
import numpy as np
import ccxt
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
import warnings

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategies.backtester import Backtester
from config import settings

warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class V3QuarterlyTester:
    """Tester especializado para evaluación trimestral de estrategias V3"""
    
    def __init__(self):
        """Inicializar tester trimestral"""
        self.exchange = ccxt.binance({
            'apiKey': getattr(settings, 'BINANCE_API_KEY', ''),
            'secret': getattr(settings, 'BINANCE_SECRET_KEY', ''),
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Configuraciones V3 optimizadas
        self.v3_configs = {
            'scalping_sol_30m': {
                'name': 'Scalping_SOL_30m_Ultimate',
                'symbol': 'SOL/USDT',
                'timeframe': '30m',
                'rsi_oversold': 20, 'rsi_overbought': 80,
                'bb_std': 2.0, 'volume_threshold': 1.0,
                'risk_per_trade': 0.02,
                'atr_multiplier_sl': 1.5, 'atr_multiplier_tp': 3.0,
                'expected_monthly': 14.15
            },
            'hybrid_sol_15m': {
                'name': 'Híbrido_SOL_15m_Ultimate', 
                'symbol': 'SOL/USDT',
                'timeframe': '15m',
                'rsi_oversold': 22, 'rsi_overbought': 78,
                'bb_std': 2.2, 'volume_threshold': 1.1,
                'risk_per_trade': 0.03,
                'atr_multiplier_sl': 1.8, 'atr_multiplier_tp': 3.5,
                'expected_monthly': 13.47
            },
            'hybrid_btc_1h': {
                'name': 'Híbrido_BTC_1h_Ultimate',
                'symbol': 'BTC/USDT', 
                'timeframe': '1h',
                'rsi_oversold': 22, 'rsi_overbought': 78,
                'bb_std': 2.2, 'volume_threshold': 1.1,
                'risk_per_trade': 0.025,
                'atr_multiplier_sl': 2.0, 'atr_multiplier_tp': 4.0,
                'expected_monthly': 11.23
            }
        }
        
        # Definir períodos de prueba
        self.test_periods = {
            'Q1_2025': {
                'start': '2025-01-01',
                'end': '2025-03-31',
                'name': 'Primer Trimestre 2025',
                'days': 90
            },
            'Q2_2025': {
                'start': '2025-04-01', 
                'end': '2025-06-30',
                'name': 'Segundo Trimestre 2025',
                'days': 91
            },
            'H1_2025': {
                'start': '2025-01-01',
                'end': '2025-06-30',
                'name': 'Primer Semestre 2025',
                'days': 181
            }
        }

    async def download_historical_data(self, symbol: str, timeframe: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Descargar datos históricos para el período especificado"""
        try:
            logger.info(f"📥 Descargando {symbol} {timeframe} desde {start_date} hasta {end_date}")
            
            start_timestamp = int(pd.Timestamp(start_date).timestamp() * 1000)
            end_timestamp = int(pd.Timestamp(end_date).timestamp() * 1000)
            
            all_ohlcv = []
            current_timestamp = start_timestamp
            
            while current_timestamp < end_timestamp:
                try:
                    ohlcv = await asyncio.to_thread(
                        self.exchange.fetch_ohlcv,
                        symbol, timeframe, current_timestamp, 1000
                    )
                    
                    if not ohlcv:
                        break
                    
                    all_ohlcv.extend(ohlcv)
                    current_timestamp = ohlcv[-1][0] + 1
                    
                    # Evitar rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error descargando batch: {e}")
                    await asyncio.sleep(1)
                    continue
            
            if not all_ohlcv:
                raise ValueError(f"No se pudieron descargar datos para {symbol} {timeframe}")
            
            # Convertir a DataFrame
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Filtrar por período exacto
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            logger.info(f"✅ Descargados {len(df)} registros para {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"❌ Error descargando datos para {symbol}: {e}")
            raise

    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcular indicadores técnicos V3 usando pandas y numpy"""
        try:
            # RSI (Relative Strength Index)
            def calculate_rsi(prices, window=14):
                delta = prices.diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                return rsi
            
            df['rsi'] = calculate_rsi(df['close'])
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2.0)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2.0)
            df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # MACD
            ema12 = df['close'].ewm(span=12).mean()
            ema26 = df['close'].ewm(span=26).mean()
            df['macd'] = ema12 - ema26
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # EMAs
            df['ema_9'] = df['close'].ewm(span=9).mean()
            df['ema_21'] = df['close'].ewm(span=21).mean()
            df['ema_50'] = df['close'].ewm(span=50).mean()
            
            # Stochastic Oscillator
            def calculate_stochastic(high, low, close, k_window=14, d_window=3):
                lowest_low = low.rolling(k_window).min()
                highest_high = high.rolling(k_window).max()
                k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
                d_percent = k_percent.rolling(d_window).mean()
                return k_percent, d_percent
            
            df['stoch_k'], df['stoch_d'] = calculate_stochastic(df['high'], df['low'], df['close'])
            
            # Williams %R
            def calculate_williams_r(high, low, close, window=14):
                highest_high = high.rolling(window).max()
                lowest_low = low.rolling(window).min()
                wr = -100 * (highest_high - close) / (highest_high - lowest_low)
                return wr
            
            df['williams_r'] = calculate_williams_r(df['high'], df['low'], df['close'])
            
            # CCI (Commodity Channel Index)
            def calculate_cci(high, low, close, window=14):
                tp = (high + low + close) / 3
                tp_ma = tp.rolling(window).mean()
                mad = tp.rolling(window).apply(lambda x: np.mean(np.abs(x - x.mean())))
                cci = (tp - tp_ma) / (0.015 * mad)
                return cci
            
            df['cci'] = calculate_cci(df['high'], df['low'], df['close'])
            
            # ATR (Average True Range)
            def calculate_atr(high, low, close, window=14):
                high_low = high - low
                high_close = np.abs(high - close.shift())
                low_close = np.abs(low - close.shift())
                true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                atr = true_range.rolling(window).mean()
                return atr
            
            df['atr'] = calculate_atr(df['high'], df['low'], df['close'])
            
            # Volume Ratio
            df['volume_sma_20'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma_20']
            
            # Limpiar datos NaN
            df_clean = df.dropna()
            logger.info(f"   📊 Indicadores calculados: {len(df_clean)} registros válidos de {len(df)} originales")
            return df_clean
            
        except Exception as e:
            logger.error(f"❌ Error calculando indicadores: {e}")
            import traceback
            traceback.print_exc()
            raise

class V3StrategyForBacktest:
    """Estrategia V3 adaptada para backtesting"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config['name']
        
    def analyze(self, df: pd.DataFrame, idx: int = None) -> Dict[str, Any]:
        """Analizar y generar señal de trading"""
        try:
            if idx is None:
                idx = len(df) - 1
            
            if idx < 1 or idx >= len(df):
                return {'decision': 'MANTENER', 'score': 0.0, 'reason': 'Índice inválido'}
            
            current = df.iloc[idx]
            prev = df.iloc[idx-1]
            
            # Condiciones LONG
            long_conditions = []
            long_reasons = []
            
            # 1. RSI oversold
            if current['rsi'] < self.config['rsi_oversold']:
                long_conditions.append(True)
                long_reasons.append(f"RSI_oversold({current['rsi']:.1f})")
            else:
                long_conditions.append(False)
            
            # 2. BB position low
            if current['bb_position'] < 0.2:
                long_conditions.append(True)
                long_reasons.append(f"BB_lower({current['bb_position']:.2f})")
            else:
                long_conditions.append(False)
            
            # 3. MACD momentum up
            if current['macd_histogram'] > prev['macd_histogram']:
                long_conditions.append(True)
                long_reasons.append("MACD_momentum_up")
            else:
                long_conditions.append(False)
            
            # 4. EMA trend up
            if current['ema_9'] > current['ema_21']:
                long_conditions.append(True)
                long_reasons.append("EMA_trend_up")
            else:
                long_conditions.append(False)
            
            # 5. Stochastic oversold
            if current['stoch_k'] < 20:
                long_conditions.append(True)
                long_reasons.append(f"Stoch_oversold({current['stoch_k']:.1f})")
            else:
                long_conditions.append(False)
            
            # 6. Volume confirmation
            if current['volume_ratio'] > self.config['volume_threshold']:
                long_conditions.append(True)
                long_reasons.append(f"Volume_high({current['volume_ratio']:.1f})")
            else:
                long_conditions.append(False)
            
            # Condiciones SHORT
            short_conditions = []
            short_reasons = []
            
            # 7. RSI overbought
            if current['rsi'] > self.config['rsi_overbought']:
                short_conditions.append(True)
                short_reasons.append(f"RSI_overbought({current['rsi']:.1f})")
            else:
                short_conditions.append(False)
            
            # 8. BB position high
            if current['bb_position'] > 0.8:
                short_conditions.append(True)
                short_reasons.append(f"BB_upper({current['bb_position']:.2f})")
            else:
                short_conditions.append(False)
            
            # 9. MACD momentum down
            if current['macd_histogram'] < prev['macd_histogram']:
                short_conditions.append(True)
                short_reasons.append("MACD_momentum_down")
            else:
                short_conditions.append(False)
            
            # 10. EMA trend down
            if current['ema_9'] < current['ema_21']:
                short_conditions.append(True)
                short_reasons.append("EMA_trend_down")
            else:
                short_conditions.append(False)
            
            # 11. Stochastic overbought
            if current['stoch_k'] > 80:
                short_conditions.append(True)
                short_reasons.append(f"Stoch_overbought({current['stoch_k']:.1f})")
            else:
                short_conditions.append(False)
            
            # 12. Volume confirmation
            if current['volume_ratio'] > self.config['volume_threshold']:
                short_conditions.append(True)
                short_reasons.append(f"Volume_high({current['volume_ratio']:.1f})")
            else:
                short_conditions.append(False)
            
            # Calcular scores
            long_score = sum(long_conditions) / len(long_conditions)
            short_score = sum(short_conditions) / len(short_conditions)
            
            # Decisión final
            if long_score >= 0.7 and long_score > short_score + 0.1:
                return {
                    'decision': 'COMPRAR',
                    'score': long_score,
                    'reason': f"Strong_Long({long_score:.2f}): {', '.join(long_reasons[:3])}"
                }
            elif short_score >= 0.7 and short_score > long_score + 0.1:
                return {
                    'decision': 'VENDER', 
                    'score': short_score,
                    'reason': f"Strong_Short({short_score:.2f}): {', '.join(short_reasons[:3])}"
                }
            else:
                return {
                    'decision': 'MANTENER',
                    'score': max(long_score, short_score),
                    'reason': f"Hold_Signal(L:{long_score:.2f}_S:{short_score:.2f})"
                }
                
        except Exception as e:
            logger.error(f"Error en análisis V3: {e}")
            return {'decision': 'MANTENER', 'score': 0.0, 'reason': f'Error: {str(e)}'}

async def run_quarterly_backtest():
    """Ejecutar backtests trimestrales completos"""
    
    tester = V3QuarterlyTester()
    results = {}
    
    logger.info("🚀 INICIANDO BACKTESTS TRIMESTRALES Q1-Q2 2025")
    logger.info("=" * 60)
    
    # Procesar cada estrategia
    for strategy_id, config in tester.v3_configs.items():
        logger.info(f"\n📊 PROCESANDO ESTRATEGIA: {config['name']}")
        logger.info(f"   Symbol: {config['symbol']} | Timeframe: {config['timeframe']}")
        
        strategy_results = {}
        
        # Procesar cada período
        for period_id, period_config in tester.test_periods.items():
            logger.info(f"\n⏰ Período: {period_config['name']} ({period_config['start']} - {period_config['end']})")
            
            try:
                # Descargar datos históricos
                df = await tester.download_historical_data(
                    config['symbol'], 
                    config['timeframe'],
                    period_config['start'], 
                    period_config['end']
                )
                
                if len(df) < 100:
                    logger.warning(f"⚠️ Datos insuficientes para {period_id}: {len(df)} registros")
                    continue
                
                # Calcular indicadores técnicos
                df_with_indicators = tester.calculate_technical_indicators(df)
                logger.info(f"   📈 Indicadores calculados: {len(df_with_indicators)} registros")
                
                # Configurar estrategia para backtest
                v3_strategy = V3StrategyForBacktest(config)
                
                # Ejecutar backtest
                backtester = Backtester(
                    historical_data=df_with_indicators,
                    initial_balance=1000.0,
                    commission=0.001,
                    warmup_period=50,
                    symbol=config['symbol'],
                    interval=config['timeframe']
                )
                
                metrics = await backtester.run(v3_strategy)
                
                if metrics:
                    # Calcular retorno trimestral proyectado
                    total_return = metrics.get('total_return_pct', 0)
                    days_in_period = period_config['days']
                    monthly_return = (total_return / days_in_period) * 30
                    quarterly_return = (total_return / days_in_period) * 90
                    
                    strategy_results[period_id] = {
                        'period_name': period_config['name'],
                        'start_date': period_config['start'],
                        'end_date': period_config['end'],
                        'days': days_in_period,
                        'total_return_pct': total_return,
                        'monthly_return_projected': monthly_return,
                        'quarterly_return_projected': quarterly_return,
                        'expected_monthly': config['expected_monthly'],
                        'performance_vs_expected': (monthly_return / config['expected_monthly']) * 100 if config['expected_monthly'] > 0 else 0,
                        'total_trades': metrics.get('total_trades', 0),
                        'win_rate_pct': metrics.get('win_rate_pct', 0),
                        'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
                        'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                        'final_balance': metrics.get('final_balance', 1000)
                    }
                    
                    logger.info(f"   ✅ Retorno total: {total_return:.2f}%")
                    logger.info(f"   📊 Retorno mensual proyectado: {monthly_return:.2f}%") 
                    logger.info(f"   🎯 Performance vs esperado: {strategy_results[period_id]['performance_vs_expected']:.1f}%")
                    logger.info(f"   📈 Trades: {metrics.get('total_trades', 0)} | Win Rate: {metrics.get('win_rate_pct', 0):.1f}%")
                
            except Exception as e:
                logger.error(f"❌ Error procesando {strategy_id} en {period_id}: {e}")
                continue
        
        results[strategy_id] = strategy_results
    
    # Guardar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"V3_QUARTERLY_BACKTEST_Q1Q2_2025_{timestamp}.json"
    
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"\n💾 Resultados guardados en: {results_file}")
    
    # Generar reporte final
    await generate_quarterly_report(results, results_file)
    
    return results

async def generate_quarterly_report(results: Dict, results_file: str):
    """Generar reporte ejecutivo de resultados trimestrales"""
    
    logger.info("\n" + "="*80)
    logger.info("📋 REPORTE EJECUTIVO - BACKTESTS Q1-Q2 2025")
    logger.info("="*80)
    
    report_lines = [
        "# 📊 REPORTE BACKTESTS TRIMESTRALES Q1-Q2 2025",
        "## Estrategias V3 - Análisis de Rendimiento",
        f"**Fecha de análisis:** {datetime.now().strftime('%d de %B de %Y')}",
        f"**Archivo de datos:** {results_file}",
        "",
        "## 🎯 RESUMEN EJECUTIVO",
        ""
    ]
    
    total_strategies = len(results)
    successful_tests = 0
    
    for strategy_id, strategy_results in results.items():
        if not strategy_results:
            continue
            
        successful_tests += len([r for r in strategy_results.values() if r.get('total_return_pct', 0) != 0])
        
        report_lines.append(f"### 📈 {strategy_results.get(list(strategy_results.keys())[0], {}).get('period_name', strategy_id) if strategy_results else strategy_id}")
        
        for period_id, period_data in strategy_results.items():
            period_name = period_data.get('period_name', period_id)
            total_return = period_data.get('total_return_pct', 0)
            monthly_projected = period_data.get('monthly_return_projected', 0)
            performance_vs_expected = period_data.get('performance_vs_expected', 0)
            win_rate = period_data.get('win_rate_pct', 0)
            trades = period_data.get('total_trades', 0)
            
            status = "🟢" if performance_vs_expected >= 80 else "🟡" if performance_vs_expected >= 50 else "🔴"
            
            report_lines.extend([
                f"**{period_name}:**",
                f"- Retorno total: **{total_return:.2f}%**",
                f"- Retorno mensual proyectado: **{monthly_projected:.2f}%**", 
                f"- Performance vs esperado: {status} **{performance_vs_expected:.1f}%**",
                f"- Trades ejecutados: {trades} | Win Rate: {win_rate:.1f}%",
                ""
            ])
    
    report_lines.extend([
        "## 📊 ESTADÍSTICAS GENERALES",
        f"- **Estrategias evaluadas:** {total_strategies}",
        f"- **Tests exitosos:** {successful_tests}",
        f"- **Períodos analizados:** Q1 2025, Q2 2025, H1 2025",
        "",
        "## 🏆 CONCLUSIONES",
        "- Análisis completado exitosamente",
        "- Datos guardados para análisis posterior", 
        f"- Archivo de resultados: `{results_file}`",
        "",
        f"*Reporte generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}*"
    ])
    
    # Guardar reporte
    report_file = f"REPORTE_QUARTERLY_V3_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    # Mostrar reporte en consola
    for line in report_lines:
        if line.startswith('#'):
            logger.info(line)
        elif line.startswith('**') or line.startswith('- **'):
            logger.info(line)
        elif line and not line.startswith('*'):
            logger.info(line)
    
    logger.info(f"\n📄 Reporte detallado guardado en: {report_file}")

if __name__ == "__main__":
    asyncio.run(run_quarterly_backtest())
