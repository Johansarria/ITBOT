#!/usr/bin/env python3
"""
SICAR Real Data Breakout Backtester
===================================
Sistema de backtesting que usa EXCLUSIVAMENTE datos reales de Binance
para validar la estrategia de "first candle breakout" en las tres sesiones.

Autor: SICAR Team
Fecha: 2025-01-18
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SessionConfig:
    """Configuración de sesión de trading"""
    name: str
    start_hour: int
    start_minute: int
    duration_minutes: int
    timezone_offset: int  # Offset desde UTC
    expected_win_rate: float
    stop_loss_pct: float
    take_profit_pct: float
    position_size_pct: float
    min_volume_ratio: float
    min_price_move_pct: float
    max_spread_pct: float

@dataclass
class RealBreakoutSignal:
    """Señal de breakout con datos reales"""
    timestamp: datetime
    symbol: str
    session: str
    signal_type: str  # 'bullish_breakout' o 'bearish_breakout'
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    volume_ratio: float
    price_move_pct: float
    spread_pct: float
    confidence: float

@dataclass
class RealTradeResult:
    """Resultado de trade con datos reales"""
    signal: RealBreakoutSignal
    exit_price: float
    exit_time: datetime
    exit_reason: str
    pnl_gross: float
    pnl_net: float  # Después de comisiones
    trading_fee: float
    duration_minutes: int
    success: bool

class RealDataBreakoutBacktester:
    """Backtester que usa exclusivamente datos reales de Binance"""
    
    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.total_pnl = 0.0
        self.total_fees = 0.0
        
        # Configuración de sesiones con parámetros validados
        self.sessions = {
            'asian': SessionConfig(
                name='Asian Session',
                start_hour=2,  # 02:00 UTC (Asia abre)
                start_minute=0,
                duration_minutes=5,
                timezone_offset=0,
                expected_win_rate=0.78,
                stop_loss_pct=0.015,
                take_profit_pct=0.025,
                position_size_pct=0.15,
                min_volume_ratio=1.2,
                min_price_move_pct=0.003,
                max_spread_pct=0.001
            ),
            'european': SessionConfig(
                name='European Session',
                start_hour=8,  # 08:00 UTC (Europa abre)
                start_minute=30,
                duration_minutes=5,
                timezone_offset=0,
                expected_win_rate=0.955,
                stop_loss_pct=0.012,
                take_profit_pct=0.020,
                position_size_pct=0.20,
                min_volume_ratio=1.5,
                min_price_move_pct=0.002,
                max_spread_pct=0.0008
            ),
            'american': SessionConfig(
                name='American Session',
                start_hour=14,  # 14:00 UTC (América abre)
                start_minute=30,
                duration_minutes=5,
                timezone_offset=0,
                expected_win_rate=0.87,
                stop_loss_pct=0.018,
                take_profit_pct=0.028,
                position_size_pct=0.18,
                min_volume_ratio=1.3,
                min_price_move_pct=0.0025,
                max_spread_pct=0.0012
            )
        }
        
        # Símbolos optimizados para breakout
        self.symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
            'SOLUSDT', 'DOTUSDT', 'LINKUSDT', 'LTCUSDT', 'BCHUSDT',
            'UNIUSDT', 'XLMUSDT', 'VETUSDT', 'FILUSDT', 'TRXUSDT'
        ]
        
        # Comisiones reales de Binance
        self.trading_fee_rate = 0.001  # 0.1% por lado
        self.total_fee_per_trade = 0.002  # 0.2% total (entrada + salida)
        
        # Almacenamiento de resultados
        self.trades: List[RealTradeResult] = []
        self.session_stats = {}
        
        # Base URL de Binance API
        self.binance_base_url = "https://api.binance.com/api/v3"
        
    async def fetch_real_klines(self, session: aiohttp.ClientSession, symbol: str, 
                               start_time: datetime, end_time: datetime, 
                               interval: str = "1m") -> pd.DataFrame:
        """Obtener datos reales de velas de Binance"""
        try:
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            url = f"{self.binance_base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': start_ms,
                'endTime': end_ms,
                'limit': 1000
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if not data:
                        logger.warning(f"No hay datos para {symbol} en el período solicitado")
                        return pd.DataFrame()
                    
                    # Convertir a DataFrame
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_asset_volume', 'number_of_trades',
                        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
                    ])
                    
                    # Convertir tipos de datos
                    numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume']
                    for col in numeric_columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df['symbol'] = symbol
                    
                    logger.info(f"✅ Obtenidos {len(df)} registros reales para {symbol}")
                    return df[['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
                    
                else:
                    logger.error(f"Error API Binance para {symbol}: {response.status}")
                    return pd.DataFrame()
                    
        except Exception as e:
            logger.error(f"Error obteniendo datos reales para {symbol}: {e}")
            return pd.DataFrame()
    
    def detect_real_breakout(self, df: pd.DataFrame, session_config: SessionConfig, 
                            session_time: datetime) -> Optional[RealBreakoutSignal]:
        """Detectar breakout en datos reales"""
        try:
            if len(df) < 2:
                return None
            
            # Obtener la primera vela de la sesión
            session_start = session_time
            session_end = session_start + timedelta(minutes=session_config.duration_minutes)
            
            # Filtrar datos de la sesión
            session_data = df[
                (df['timestamp'] >= session_start) & 
                (df['timestamp'] < session_end)
            ].copy()
            
            if len(session_data) == 0:
                return None
            
            # Tomar la primera vela completa
            first_candle = session_data.iloc[0]
            
            # Calcular métricas de la vela
            open_price = float(first_candle['open'])
            high_price = float(first_candle['high'])
            low_price = float(first_candle['low'])
            close_price = float(first_candle['close'])
            volume = float(first_candle['volume'])
            
            # Calcular movimiento de precio
            price_move_pct = abs(close_price - open_price) / open_price
            
            # Calcular spread aproximado
            spread_pct = (high_price - low_price) / open_price
            
            # Calcular ratio de volumen (comparar con vela anterior si existe)
            volume_ratio = 1.0
            if len(df) > len(session_data):
                prev_data = df[df['timestamp'] < session_start].tail(5)
                if len(prev_data) > 0:
                    avg_prev_volume = prev_data['volume'].mean()
                    if avg_prev_volume > 0:
                        volume_ratio = volume / avg_prev_volume
            
            # Verificar condiciones mínimas
            if (price_move_pct < session_config.min_price_move_pct or
                volume_ratio < session_config.min_volume_ratio or
                spread_pct > session_config.max_spread_pct):
                return None
            
            # Determinar tipo de breakout
            if close_price > open_price:
                signal_type = 'bullish_breakout'
                entry_price = high_price  # Breakout por encima del máximo
                stop_loss = entry_price * (1 - session_config.stop_loss_pct)
                take_profit = entry_price * (1 + session_config.take_profit_pct)
            else:
                signal_type = 'bearish_breakout'
                entry_price = low_price  # Breakout por debajo del mínimo
                stop_loss = entry_price * (1 + session_config.stop_loss_pct)
                take_profit = entry_price * (1 - session_config.take_profit_pct)
            
            # Calcular tamaño de posición
            position_size = self.current_capital * session_config.position_size_pct
            
            # Calcular confianza basada en métricas reales
            confidence = min(1.0, (
                (price_move_pct / session_config.min_price_move_pct) * 0.3 +
                (volume_ratio / session_config.min_volume_ratio) * 0.4 +
                (1 - spread_pct / session_config.max_spread_pct) * 0.3
            ))
            
            return RealBreakoutSignal(
                timestamp=first_candle['timestamp'],
                symbol=first_candle['symbol'],
                session=session_config.name,
                signal_type=signal_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=position_size,
                volume_ratio=volume_ratio,
                price_move_pct=price_move_pct,
                spread_pct=spread_pct,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error detectando breakout real: {e}")
            return None
    
    def simulate_real_trade(self, signal: RealBreakoutSignal, 
                           market_data: pd.DataFrame) -> RealTradeResult:
        """Simular ejecución de trade con datos reales"""
        try:
            # Buscar datos posteriores a la señal para simular la ejecución
            future_data = market_data[
                market_data['timestamp'] > signal.timestamp
            ].head(60)  # Máximo 1 hora de datos
            
            if len(future_data) == 0:
                # No hay datos suficientes, asumir pérdida
                exit_price = signal.stop_loss
                exit_time = signal.timestamp + timedelta(minutes=5)
                exit_reason = "No data available"
                success = False
            else:
                # Simular ejecución minuto a minuto
                exit_price = None
                exit_time = None
                exit_reason = None
                success = False
                
                for _, candle in future_data.iterrows():
                    high = float(candle['high'])
                    low = float(candle['low'])
                    close = float(candle['close'])
                    timestamp = candle['timestamp']
                    
                    if signal.signal_type == 'bullish_breakout':
                        # Verificar take profit
                        if high >= signal.take_profit:
                            exit_price = signal.take_profit
                            exit_time = timestamp
                            exit_reason = "Take Profit"
                            success = True
                            break
                        # Verificar stop loss
                        elif low <= signal.stop_loss:
                            exit_price = signal.stop_loss
                            exit_time = timestamp
                            exit_reason = "Stop Loss"
                            success = False
                            break
                    else:  # bearish_breakout
                        # Verificar take profit
                        if low <= signal.take_profit:
                            exit_price = signal.take_profit
                            exit_time = timestamp
                            exit_reason = "Take Profit"
                            success = True
                            break
                        # Verificar stop loss
                        elif high >= signal.stop_loss:
                            exit_price = signal.stop_loss
                            exit_time = timestamp
                            exit_reason = "Stop Loss"
                            success = False
                            break
                
                # Si no se activó ningún nivel, cerrar al final del período
                if exit_price is None:
                    last_candle = future_data.iloc[-1]
                    exit_price = float(last_candle['close'])
                    exit_time = last_candle['timestamp']
                    exit_reason = "Time Exit"
                    
                    # Determinar si fue exitoso basado en el precio de cierre
                    if signal.signal_type == 'bullish_breakout':
                        success = exit_price > signal.entry_price
                    else:
                        success = exit_price < signal.entry_price
            
            # Calcular PnL
            if signal.signal_type == 'bullish_breakout':
                pnl_gross = signal.position_size * (exit_price / signal.entry_price - 1)
            else:
                pnl_gross = signal.position_size * (signal.entry_price / exit_price - 1)
            
            # Aplicar comisiones reales
            trading_fee = signal.position_size * self.total_fee_per_trade
            pnl_net = pnl_gross - trading_fee
            
            # Calcular duración
            duration_minutes = int((exit_time - signal.timestamp).total_seconds() / 60)
            
            return RealTradeResult(
                signal=signal,
                exit_price=exit_price,
                exit_time=exit_time,
                exit_reason=exit_reason,
                pnl_gross=pnl_gross,
                pnl_net=pnl_net,
                trading_fee=trading_fee,
                duration_minutes=duration_minutes,
                success=success
            )
            
        except Exception as e:
            logger.error(f"Error simulando trade real: {e}")
            # Retornar trade fallido en caso de error
            return RealTradeResult(
                signal=signal,
                exit_price=signal.stop_loss,
                exit_time=signal.timestamp + timedelta(minutes=5),
                exit_reason="Simulation Error",
                pnl_gross=-signal.position_size * 0.02,
                pnl_net=-signal.position_size * 0.022,
                trading_fee=signal.position_size * self.total_fee_per_trade,
                duration_minutes=5,
                success=False
            )
    
    async def run_real_backtest(self, start_date: datetime, end_date: datetime) -> Dict:
        """Ejecutar backtest completo con datos reales"""
        logger.info(f"🚀 Iniciando backtest con DATOS REALES")
        logger.info(f"📅 Período: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"💰 Capital inicial: ${self.initial_capital:.2f}")
        logger.info(f"📊 Símbolos: {len(self.symbols)} pares")
        logger.info(f"🕐 Sesiones: {len(self.sessions)} (Asian, European, American)")
        
        total_signals = 0
        total_trades = 0
        
        async with aiohttp.ClientSession() as session:
            # Procesar cada día del período
            current_date = start_date
            while current_date <= end_date:
                logger.info(f"📈 Procesando día: {current_date.strftime('%Y-%m-%d')}")
                
                # Para cada sesión del día
                for session_name, session_config in self.sessions.items():
                    # Calcular tiempo de inicio de sesión
                    session_time = datetime(
                        current_date.year, current_date.month, current_date.day,
                        session_config.start_hour, session_config.start_minute
                    )
                    
                    # Obtener datos para el período de la sesión + 2 horas después
                    data_start = session_time - timedelta(hours=1)  # 1 hora antes
                    data_end = session_time + timedelta(hours=3)    # 3 horas después
                    
                    # Para cada símbolo
                    for symbol in self.symbols:
                        try:
                            # Obtener datos reales de Binance
                            df = await self.fetch_real_klines(
                                session, symbol, data_start, data_end
                            )
                            
                            if len(df) == 0:
                                continue
                            
                            # Detectar breakout
                            breakout_signal = self.detect_real_breakout(
                                df, session_config, session_time
                            )
                            
                            if breakout_signal:
                                total_signals += 1
                                logger.info(f"🎯 Señal detectada: {symbol} {session_name} {breakout_signal.signal_type}")
                                
                                # Simular trade
                                trade_result = self.simulate_real_trade(breakout_signal, df)
                                
                                # Actualizar capital
                                self.current_capital += trade_result.pnl_net
                                self.total_pnl += trade_result.pnl_net
                                self.total_fees += trade_result.trading_fee
                                
                                # Guardar trade
                                self.trades.append(trade_result)
                                total_trades += 1
                                
                                # Log del resultado
                                status = "✅ WIN" if trade_result.success else "❌ LOSS"
                                logger.info(f"{status} {symbol}: ${trade_result.pnl_net:.2f} ({trade_result.exit_reason})")
                            
                            # Pequeña pausa para no sobrecargar la API
                            await asyncio.sleep(0.1)
                            
                        except Exception as e:
                            logger.error(f"Error procesando {symbol} en {session_name}: {e}")
                            continue
                
                # Avanzar al siguiente día
                current_date += timedelta(days=1)
                
                # Pausa entre días
                await asyncio.sleep(0.5)
        
        # Calcular estadísticas finales
        return self.calculate_real_performance_stats()
    
    def calculate_real_performance_stats(self) -> Dict:
        """Calcular estadísticas de performance con datos reales"""
        if not self.trades:
            return {"error": "No se ejecutaron trades"}
        
        # Estadísticas generales
        total_trades = len(self.trades)
        winning_trades = sum(1 for t in self.trades if t.success)
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # PnL
        total_pnl_gross = sum(t.pnl_gross for t in self.trades)
        total_pnl_net = sum(t.pnl_net for t in self.trades)
        
        # ROI
        total_roi = (self.current_capital - self.initial_capital) / self.initial_capital
        
        # Estadísticas por sesión
        session_stats = {}
        for session_name in self.sessions.keys():
            session_trades = [t for t in self.trades if session_name.lower() in t.signal.session.lower()]
            if session_trades:
                session_wins = sum(1 for t in session_trades if t.success)
                session_stats[session_name] = {
                    'trades': len(session_trades),
                    'wins': session_wins,
                    'losses': len(session_trades) - session_wins,
                    'win_rate': session_wins / len(session_trades),
                    'pnl_net': sum(t.pnl_net for t in session_trades),
                    'avg_duration': np.mean([t.duration_minutes for t in session_trades])
                }
        
        # Duración promedio
        avg_duration = np.mean([t.duration_minutes for t in self.trades])
        
        # Mejor y peor trade
        best_trade = max(self.trades, key=lambda t: t.pnl_net)
        worst_trade = min(self.trades, key=lambda t: t.pnl_net)
        
        return {
            'backtest_summary': {
                'initial_capital': self.initial_capital,
                'final_capital': self.current_capital,
                'total_pnl_gross': total_pnl_gross,
                'total_pnl_net': total_pnl_net,
                'total_fees': self.total_fees,
                'total_roi': total_roi,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_duration_minutes': avg_duration
            },
            'session_performance': session_stats,
            'best_trade': {
                'symbol': best_trade.signal.symbol,
                'session': best_trade.signal.session,
                'pnl_net': best_trade.pnl_net,
                'duration': best_trade.duration_minutes
            },
            'worst_trade': {
                'symbol': worst_trade.signal.symbol,
                'session': worst_trade.signal.session,
                'pnl_net': worst_trade.pnl_net,
                'duration': worst_trade.duration_minutes
            },
            'data_source': 'BINANCE_REAL_DATA',
            'validation_status': 'REAL_DATA_VALIDATED' if win_rate > 0.75 else 'NEEDS_OPTIMIZATION'
        }
    
    def save_real_results(self, results: Dict, filename: str = None):
        """Guardar resultados del backtest real"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"real_data_backtest_{timestamp}.json"
        
        filepath = f"C:\\Users\\johan\\OneDrive\\Escritorio\\SICAR\\sicar_project\\src\\{filename}"
        
        # Agregar detalles de trades
        results['trade_details'] = []
        for trade in self.trades:
            results['trade_details'].append({
                'timestamp': trade.signal.timestamp.isoformat(),
                'symbol': trade.signal.symbol,
                'session': trade.signal.session,
                'signal_type': trade.signal.signal_type,
                'entry_price': trade.signal.entry_price,
                'exit_price': trade.exit_price,
                'exit_reason': trade.exit_reason,
                'pnl_gross': trade.pnl_gross,
                'pnl_net': trade.pnl_net,
                'trading_fee': trade.trading_fee,
                'duration_minutes': trade.duration_minutes,
                'success': trade.success,
                'confidence': trade.signal.confidence
            })
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Resultados guardados en: {filepath}")
        return filepath

async def main():
    """Función principal para ejecutar backtests con datos reales"""
    
    # Crear backtester
    backtester = RealDataBreakoutBacktester(initial_capital=1000.0)
    
    print("🚀 SICAR Real Data Breakout Backtester")
    print("=" * 50)
    print("📊 USANDO EXCLUSIVAMENTE DATOS REALES DE BINANCE")
    print("=" * 50)
    
    # Definir períodos de backtest
    test_periods = [
        {
            'name': '1 Semana Reciente',
            'start': datetime.now() - timedelta(days=7),
            'end': datetime.now() - timedelta(days=1)
        },
        {
            'name': '2 Semanas Recientes', 
            'start': datetime.now() - timedelta(days=14),
            'end': datetime.now() - timedelta(days=1)
        },
        {
            'name': '1 Mes Reciente',
            'start': datetime.now() - timedelta(days=30),
            'end': datetime.now() - timedelta(days=1)
        }
    ]
    
    all_results = []
    
    for period in test_periods:
        print(f"\n🔍 Ejecutando backtest: {period['name']}")
        print(f"📅 Desde: {period['start'].strftime('%Y-%m-%d')}")
        print(f"📅 Hasta: {period['end'].strftime('%Y-%m-%d')}")
        
        # Resetear backtester para cada período
        backtester.current_capital = backtester.initial_capital
        backtester.total_pnl = 0.0
        backtester.total_fees = 0.0
        backtester.trades = []
        
        try:
            # Ejecutar backtest
            results = await backtester.run_real_backtest(
                period['start'], period['end']
            )
            
            # Agregar información del período
            results['period_info'] = {
                'name': period['name'],
                'start_date': period['start'].isoformat(),
                'end_date': period['end'].isoformat(),
                'duration_days': (period['end'] - period['start']).days
            }
            
            # Guardar resultados
            filename = f"real_backtest_{period['name'].lower().replace(' ', '_')}.json"
            filepath = backtester.save_real_results(results, filename)
            
            # Mostrar resumen
            summary = results['backtest_summary']
            print(f"\n📊 RESULTADOS - {period['name']}:")
            print(f"💰 Capital Final: ${summary['final_capital']:.2f}")
            print(f"📈 ROI Total: {summary['total_roi']*100:.2f}%")
            print(f"🎯 Win Rate: {summary['win_rate']*100:.1f}%")
            print(f"📊 Total Trades: {summary['total_trades']}")
            print(f"💸 Fees Totales: ${summary['total_fees']:.2f}")
            print(f"✅ Estado: {results['validation_status']}")
            
            all_results.append(results)
            
        except Exception as e:
            logger.error(f"Error en backtest {period['name']}: {e}")
            continue
    
    # Resumen final
    print(f"\n🏆 RESUMEN FINAL DE BACKTESTS CON DATOS REALES")
    print("=" * 60)
    
    for i, result in enumerate(all_results):
        period_name = result['period_info']['name']
        summary = result['backtest_summary']
        
        print(f"\n{i+1}. {period_name}:")
        print(f"   ROI: {summary['total_roi']*100:.2f}% | Win Rate: {summary['win_rate']*100:.1f}% | Trades: {summary['total_trades']}")
    
    print(f"\n✅ Todos los backtests completados con DATOS REALES")
    print(f"📁 Resultados guardados en archivos JSON individuales")

if __name__ == "__main__":
    asyncio.run(main())