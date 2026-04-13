#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtester Comprehensivo Multi-Instrumento
Testa estrategias en Forex, Índices y Metales para encontrar 15%+ mensual
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import os
import warnings
warnings.filterwarnings('ignore')

# Importar nuestras clases
try:
    from multi_instrument_data_downloader import MultiInstrumentDataDownloader
    from multi_instrument_strategy import MultiInstrumentStrategy
except ImportError:
    print("⚠️ Importando módulos localmente...")

class ComprehensiveMultiBacktester:
    """
    Backtester que prueba múltiples instrumentos y estrategias
    """
    
    def __init__(self, initial_balance: float = 100000.0, commission: float = 0.001):
        self.initial_balance = initial_balance
        self.commission = commission
        self.results = {}
        
    def run_multi_instrument_backtest(self, data_dict: Dict[str, pd.DataFrame], 
                                     strategies: Dict[str, MultiInstrumentStrategy]) -> Dict[str, Any]:
        """
        Ejecuta backtest para múltiples instrumentos
        """
        print("🚀 Iniciando Backtest Multi-Instrumento")
        print("=" * 60)
        
        all_results = {}
        
        for instrument_name, data in data_dict.items():
            if instrument_name in strategies:
                print(f"\n📊 Testeando {instrument_name}...")
                
                strategy = strategies[instrument_name]
                backtester = SingleInstrumentBacktester(
                    self.initial_balance, 
                    self.commission,
                    instrument_name
                )
                
                results = backtester.run_backtest(data, strategy)
                all_results[instrument_name] = results
                
                # Mostrar resumen rápido
                print(f"   ✅ Completado: {results['total_trades']} trades, "
                      f"{results['monthly_return_pct']:.2f}% mensual")
            else:
                print(f"⚠️ No hay estrategia para {instrument_name}")
        
        # Crear reporte comprehensivo
        comprehensive_report = self._create_comprehensive_report(all_results)
        
        return {
            'individual_results': all_results,
            'comprehensive_report': comprehensive_report,
            'best_performer': self._find_best_performer(all_results),
            'portfolio_results': self._calculate_portfolio_results(all_results)
        }
    
    def _create_comprehensive_report(self, results: Dict[str, Any]) -> str:
        """
        Crea reporte comprehensivo de todos los instrumentos
        """
        report = []
        report.append("📊 REPORTE COMPREHENSIVO MULTI-INSTRUMENTO")
        report.append("=" * 60)
        report.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Balance inicial por instrumento: ${self.initial_balance:,.2f}")
        report.append("")
        
        # Resumen ejecutivo
        instruments_15_plus = []
        total_instruments = len(results)
        
        report.append("🎯 RESUMEN EJECUTIVO")
        report.append("-" * 30)
        
        for instrument, result in results.items():
            monthly_return = result['monthly_return_pct']
            if monthly_return >= 15.0:
                instruments_15_plus.append((instrument, monthly_return))
        
        report.append(f"Instrumentos testeados: {total_instruments}")
        report.append(f"Instrumentos con 15%+ mensual: {len(instruments_15_plus)}")
        report.append(f"Tasa de éxito: {len(instruments_15_plus)/total_instruments*100:.1f}%")
        report.append("")
        
        if instruments_15_plus:
            report.append("🏆 INSTRUMENTOS QUE ALCANZAN 15%+ MENSUAL:")
            instruments_15_plus.sort(key=lambda x: x[1], reverse=True)
            for i, (instrument, monthly_return) in enumerate(instruments_15_plus, 1):
                report.append(f"{i}. {instrument}: {monthly_return:.2f}% mensual")
            report.append("")
        
        # Detalles por instrumento
        report.append("📈 RESULTADOS DETALLADOS POR INSTRUMENTO")
        report.append("=" * 50)
        
        # Ordenar por retorno mensual
        sorted_results = sorted(results.items(), key=lambda x: x[1]['monthly_return_pct'], reverse=True)
        
        for instrument, result in sorted_results:
            report.append(f"\n🔸 {instrument}")
            report.append("-" * 20)
            report.append(f"Balance final: ${result['final_balance']:,.2f}")
            report.append(f"Retorno total: {result['total_return_pct']:.2f}%")
            report.append(f"Retorno mensual: {result['monthly_return_pct']:.2f}%")
            report.append(f"Objetivo 15%: {'✅ ALCANZADO' if result['target_achieved'] else '❌ NO ALCANZADO'}")
            report.append(f"Total trades: {result['total_trades']}")
            report.append(f"Win rate: {result['win_rate_pct']:.2f}%")
            report.append(f"Profit factor: {result['profit_factor']:.2f}")
            report.append(f"Max drawdown: {result['max_drawdown_pct']:.2f}%")
            
            # Métricas específicas si están disponibles
            if 'avg_signal_score' in result:
                report.append(f"Score promedio señales: {result['avg_signal_score']:.1f}")
            if 'adaptation_count' in result:
                report.append(f"Adaptaciones realizadas: {result['adaptation_count']}")
        
        # Análisis comparativo
        report.append("\n\n📊 ANÁLISIS COMPARATIVO")
        report.append("=" * 30)
        
        # Mejores métricas
        best_return = max(results.items(), key=lambda x: x[1]['monthly_return_pct'])
        best_winrate = max(results.items(), key=lambda x: x[1]['win_rate_pct'])
        best_profit_factor = max(results.items(), key=lambda x: x[1]['profit_factor'])
        lowest_drawdown = min(results.items(), key=lambda x: x[1]['max_drawdown_pct'])
        
        report.append(f"🥇 Mejor retorno mensual: {best_return[0]} ({best_return[1]['monthly_return_pct']:.2f}%)")
        report.append(f"🎯 Mejor win rate: {best_winrate[0]} ({best_winrate[1]['win_rate_pct']:.2f}%)")
        report.append(f"💰 Mejor profit factor: {best_profit_factor[0]} ({best_profit_factor[1]['profit_factor']:.2f})")
        report.append(f"🛡️ Menor drawdown: {lowest_drawdown[0]} ({lowest_drawdown[1]['max_drawdown_pct']:.2f}%)")
        
        # Estadísticas agregadas
        avg_monthly_return = np.mean([r['monthly_return_pct'] for r in results.values()])
        avg_winrate = np.mean([r['win_rate_pct'] for r in results.values()])
        avg_drawdown = np.mean([r['max_drawdown_pct'] for r in results.values()])
        
        report.append(f"\n📊 PROMEDIOS:")
        report.append(f"Retorno mensual promedio: {avg_monthly_return:.2f}%")
        report.append(f"Win rate promedio: {avg_winrate:.2f}%")
        report.append(f"Drawdown promedio: {avg_drawdown:.2f}%")
        
        # Recomendaciones
        report.append("\n\n💡 RECOMENDACIONES")
        report.append("=" * 25)
        
        if instruments_15_plus:
            report.append("✅ INSTRUMENTOS RECOMENDADOS PARA TRADING:")
            for instrument, monthly_return in instruments_15_plus[:3]:  # Top 3
                result = results[instrument]
                report.append(f"\n🔹 {instrument}:")
                report.append(f"   - Retorno mensual: {monthly_return:.2f}%")
                report.append(f"   - Win rate: {result['win_rate_pct']:.2f}%")
                report.append(f"   - Drawdown: {result['max_drawdown_pct']:.2f}%")
                report.append(f"   - Trades por mes: ~{result['total_trades']/4:.0f}")
        else:
            report.append("⚠️ NINGÚN INSTRUMENTO ALCANZÓ 15% MENSUAL")
            report.append("\nSugerencias:")
            report.append("1. Ajustar parámetros de riesgo")
            report.append("2. Optimizar filtros de entrada")
            report.append("3. Considerar trading multi-instrumento")
            report.append("4. Revisar gestión de posiciones")
        
        # Portfolio diversificado
        report.append("\n\n🎯 ESTRATEGIA DE PORTFOLIO DIVERSIFICADO")
        report.append("=" * 45)
        
        top_3 = sorted(results.items(), key=lambda x: x[1]['monthly_return_pct'], reverse=True)[:3]
        
        report.append("Asignación recomendada de capital:")
        for i, (instrument, result) in enumerate(top_3, 1):
            allocation = [40, 35, 25][i-1]  # 40%, 35%, 25%
            expected_monthly = result['monthly_return_pct'] * (allocation/100)
            report.append(f"{i}. {instrument}: {allocation}% del capital ({expected_monthly:.2f}% contribución mensual)")
        
        total_expected = sum(r['monthly_return_pct'] * [0.4, 0.35, 0.25][i] for i, (_, r) in enumerate(top_3))
        report.append(f"\nRetorno mensual esperado del portfolio: {total_expected:.2f}%")
        
        return "\n".join(report)
    
    def _find_best_performer(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Encuentra el mejor instrumento"""
        if not results:
            return {}
        
        best = max(results.items(), key=lambda x: x[1]['monthly_return_pct'])
        return {
            'instrument': best[0],
            'results': best[1]
        }
    
    def _calculate_portfolio_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calcula resultados de portfolio diversificado"""
        if not results:
            return {}
        
        # Tomar top 3 instrumentos
        top_3 = sorted(results.items(), key=lambda x: x[1]['monthly_return_pct'], reverse=True)[:3]
        
        if len(top_3) < 3:
            return {'error': 'Insufficient instruments for portfolio'}
        
        # Asignaciones: 40%, 35%, 25%
        allocations = [0.4, 0.35, 0.25]
        
        portfolio_monthly_return = sum(
            result['monthly_return_pct'] * allocation 
            for (_, result), allocation in zip(top_3, allocations)
        )
        
        portfolio_winrate = sum(
            result['win_rate_pct'] * allocation 
            for (_, result), allocation in zip(top_3, allocations)
        )
        
        portfolio_drawdown = max(
            result['max_drawdown_pct'] 
            for _, result in top_3
        )
        
        return {
            'instruments': [instrument for instrument, _ in top_3],
            'allocations': allocations,
            'monthly_return_pct': portfolio_monthly_return,
            'win_rate_pct': portfolio_winrate,
            'max_drawdown_pct': portfolio_drawdown,
            'target_achieved': portfolio_monthly_return >= 20.0
        }


class SingleInstrumentBacktester:
    """
    Backtester para un solo instrumento
    """
    
    def __init__(self, initial_balance: float, commission: float, instrument_name: str):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.commission = commission
        self.instrument_name = instrument_name
        self.position = None
        self.position_size = 0
        self.entry_price = 0
        self.stop_loss = 0
        self.take_profit = 0
        self.trades = []
        self.balance_history = [initial_balance]
        
    def run_backtest(self, data: pd.DataFrame, strategy: MultiInstrumentStrategy) -> Dict[str, Any]:
        """Ejecuta backtest para un instrumento"""
        df = strategy.calculate_adaptive_indicators(data)
        
        adaptation_count = 0
        
        for i in range(len(df)):
            current_data = df.iloc[i]
            
            # Verificar posición existente
            if self.position is not None:
                self._manage_position(current_data, strategy)
            else:
                # Buscar nueva entrada
                signal_data = strategy.generate_adaptive_signal(df, i)
                if signal_data['action'] in ['COMPRAR', 'VENDER']:
                    self._open_position(current_data, signal_data, strategy)
            
            # Contar adaptaciones
            if i > 0 and i % strategy.adaptation_period == 0:
                adaptation_count += 1
            
            # Actualizar historial
            current_value = self._calculate_portfolio_value(current_data['close'])
            self.balance_history.append(current_value)
        
        # Cerrar posición final
        if self.position is not None:
            self._close_position(df.iloc[-1]['close'], "Final close")
        
        results = self._calculate_results()
        results['adaptation_count'] = adaptation_count
        
        return results
    
    def _open_position(self, data: pd.Series, signal_data: Dict[str, Any], strategy: MultiInstrumentStrategy):
        """Abre nueva posición"""
        price = data['close']
        direction = signal_data['action']
        
        # Calcular tamaño de posición
        position_size = strategy.calculate_position_size(price, self.balance)
        
        if position_size > 0:
            cost = position_size * price * (1 + self.commission)
            
            if cost <= self.balance:
                self.position = direction
                self.position_size = position_size
                self.entry_price = price
                
                # Calcular stop loss y take profit
                atr = data.get('atr', price * 0.01)  # Fallback ATR
                self.stop_loss, self.take_profit = strategy.calculate_stop_loss_take_profit(
                    price, direction, atr
                )
                
                self.balance -= cost
                
                # Registrar trade
                trade = {
                    'entry_time': data.name if hasattr(data, 'name') else len(self.trades),
                    'direction': direction,
                    'entry_price': price,
                    'position_size': position_size,
                    'stop_loss': self.stop_loss,
                    'take_profit': self.take_profit,
                    'signal_score': signal_data.get('score', 0),
                    'confidence': signal_data.get('confidence', 0.5),
                    'signals': signal_data.get('signals', []),
                    'status': 'open'
                }
                self.trades.append(trade)
    
    def _manage_position(self, data: pd.Series, strategy: MultiInstrumentStrategy):
        """Gestiona posición existente"""
        current_price = data['close']
        
        # Verificar salida
        should_exit, reason = self._should_exit_position(current_price)
        if should_exit:
            self._close_position(current_price, reason)
    
    def _should_exit_position(self, current_price: float) -> Tuple[bool, str]:
        """Determina si debe salir de la posición"""
        # Stop loss
        if self.position == "COMPRAR" and current_price <= self.stop_loss:
            return True, "Stop Loss"
        elif self.position == "VENDER" and current_price >= self.stop_loss:
            return True, "Stop Loss"
        
        # Take profit
        if self.position == "COMPRAR" and current_price >= self.take_profit:
            return True, "Take Profit"
        elif self.position == "VENDER" and current_price <= self.take_profit:
            return True, "Take Profit"
        
        return False, ""
    
    def _close_position(self, exit_price: float, reason: str):
        """Cierra posición"""
        if self.position is None:
            return
        
        # Calcular P&L
        if self.position == "COMPRAR":
            pnl = (exit_price - self.entry_price) * self.position_size
        else:
            pnl = (self.entry_price - exit_price) * self.position_size
        
        # Aplicar comisión
        commission_cost = exit_price * self.position_size * self.commission
        pnl -= commission_cost
        
        # Actualizar balance
        proceeds = exit_price * self.position_size * (1 - self.commission)
        self.balance += proceeds
        
        # Actualizar trade
        if self.trades:
            self.trades[-1].update({
                'exit_price': exit_price,
                'exit_reason': reason,
                'pnl': pnl,
                'pnl_pct': (pnl / (self.entry_price * self.position_size)) * 100,
                'status': 'closed'
            })
        
        # Reset position
        self.position = None
        self.position_size = 0
    
    def _calculate_portfolio_value(self, current_price: float) -> float:
        """Calcula valor del portfolio"""
        if self.position is None:
            return self.balance
        return self.balance + (self.position_size * current_price)
    
    def _calculate_results(self) -> Dict[str, Any]:
        """Calcula resultados finales"""
        final_balance = self.balance_history[-1]
        total_return = (final_balance / self.initial_balance - 1) * 100
        
        closed_trades = [t for t in self.trades if t.get('status') == 'closed']
        winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
        
        win_rate = len(winning_trades) / len(closed_trades) * 100 if closed_trades else 0
        
        # Métricas
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Calcular drawdown
        peak = self.initial_balance
        max_drawdown = 0
        for balance in self.balance_history:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Retorno mensual estimado
        days_simulated = len(self.balance_history) / (24 * 4)  # 15min intervals
        monthly_return = (total_return / days_simulated) * 30 if days_simulated > 0 else 0
        
        return {
            'instrument': self.instrument_name,
            'initial_balance': self.initial_balance,
            'final_balance': final_balance,
            'total_return_pct': total_return,
            'monthly_return_pct': monthly_return,
            'total_trades': len(closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': win_rate,
            'profit_factor': profit_factor,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'max_drawdown_pct': max_drawdown,
            'avg_signal_score': np.mean([t.get('signal_score', 0) for t in closed_trades]) if closed_trades else 0,
            'target_achieved': monthly_return >= 20.0,
            'balance_history': self.balance_history,
            'trades': self.trades
        }


def run_comprehensive_multi_backtest():
    """
    Función principal para ejecutar backtest comprehensivo
    """
    print("🌍 Iniciando Backtest Comprehensivo Multi-Instrumento")
    print("=" * 70)
    
    # Paso 1: Descargar datos
    print("\n📊 Paso 1: Descargando datos de instrumentos...")
    try:
        downloader = MultiInstrumentDataDownloader()
        data_results = downloader.download_all_instruments(period='1y', interval='15m')
        
        if not data_results:
            print("❌ No se pudieron descargar datos")
            return None
        
        print(f"✅ Datos descargados para {len(data_results)} instrumentos")
        
    except Exception as e:
        print(f"❌ Error descargando datos: {e}")
        print("🔄 Usando datos sintéticos como fallback...")
        data_results = generate_fallback_data_multi()
    
    # Paso 2: Preparar datos para backtest
    print("\n⚙️ Paso 2: Preparando datos para backtest...")
    data_dict = {}
    
    for instrument_key, info in data_results.items():
        if 'data' in info and not info['data'].empty:
            data_dict[instrument_key] = info['data']
            print(f"   {instrument_key}: {len(info['data'])} registros")
    
    if not data_dict:
        print("❌ No hay datos válidos para backtest")
        return None
    
    # Paso 3: Crear estrategias
    print("\n🎯 Paso 3: Creando estrategias adaptativas...")
    strategies = {}
    
    instrument_mapping = {
        'EURUSD': ('forex', 'EURUSD'),
        'AUDCAD': ('forex', 'AUDCAD'),
        'NAS100': ('index', 'NAS100'),
        'QQQ': ('index', 'NAS100'),
        'XAUUSD': ('metal', 'XAUUSD'),
        'GOLD_ETF': ('metal', 'XAUUSD'),
        'GLD': ('metal', 'XAUUSD')
    }
    
    for instrument_key in data_dict.keys():
        if instrument_key in instrument_mapping:
            instrument_type, instrument_name = instrument_mapping[instrument_key]
            strategies[instrument_key] = MultiInstrumentStrategy(instrument_type, instrument_name)
            print(f"   {instrument_key}: Estrategia {instrument_type} creada")
    
    # Paso 4: Ejecutar backtest
    print("\n🚀 Paso 4: Ejecutando backtest comprehensivo...")
    backtester = ComprehensiveMultiBacktester(initial_balance=100000.0)
    
    comprehensive_results = backtester.run_multi_instrument_backtest(data_dict, strategies)
    
    # Paso 5: Guardar y mostrar resultados
    print("\n💾 Paso 5: Guardando resultados...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"comprehensive_multi_backtest_{timestamp}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(comprehensive_results['comprehensive_report'])
    
    print(f"📄 Reporte guardado en: {report_file}")
    
    # Mostrar resumen
    print("\n" + "=" * 60)
    print(comprehensive_results['comprehensive_report'])
    
    return comprehensive_results


def generate_fallback_data_multi() -> Dict[str, Dict[str, Any]]:
    """
    Genera datos sintéticos como fallback
    """
    print("🔄 Generando datos sintéticos para testing...")
    
    instruments = {
        'EURUSD': {'base_price': 1.1000, 'volatility': 0.008},
        'AUDCAD': {'base_price': 0.9200, 'volatility': 0.010},
        'QQQ': {'base_price': 350.0, 'volatility': 0.015},
        'GLD': {'base_price': 180.0, 'volatility': 0.012}
    }
    
    results = {}
    
    for instrument, params in instruments.items():
        data = generate_synthetic_data(
            days=90,
            initial_price=params['base_price'],
            volatility=params['volatility']
        )
        
        results[instrument] = {
            'data': data,
            'records': len(data),
            'instrument_info': {'type': 'synthetic'}
        }
    
    return results


def generate_synthetic_data(days: int = 90, initial_price: float = 100.0, volatility: float = 0.01) -> pd.DataFrame:
    """
    Genera datos sintéticos OHLC
    """
    np.random.seed(42)
    periods_per_day = 24 * 4
    total_periods = days * periods_per_day
    
    dates = pd.date_range(start='2024-01-01', periods=total_periods, freq='15min')
    
    # Generar retornos
    returns = np.random.normal(0, volatility, total_periods)
    
    # Añadir tendencias
    trend = np.sin(np.arange(total_periods) * 2 * np.pi / (periods_per_day * 20)) * 0.002
    returns += trend
    
    # Generar precios
    prices = initial_price * (1 + returns).cumprod()
    
    # Crear OHLC
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'close': prices,
        'volume': np.random.randint(10000, 100000, total_periods)
    })
    
    # Generar high/low
    for i in range(len(df)):
        vol = abs(returns[i]) * 2
        df.loc[i, 'high'] = df.loc[i, 'open'] * (1 + vol)
        df.loc[i, 'low'] = df.loc[i, 'open'] * (1 - vol)
        df.loc[i, 'close'] = np.clip(df.loc[i, 'close'], df.loc[i, 'low'], df.loc[i, 'high'])
    
    df.set_index('timestamp', inplace=True)
    return df


if __name__ == "__main__":
    try:
        results = run_comprehensive_multi_backtest()
        
        if results:
            print("\n🎉 Backtest comprehensivo completado exitosamente!")
            
            best_performer = results['best_performer']
            if best_performer:
                print(f"\n🏆 Mejor instrumento: {best_performer['instrument']}")
                print(f"   Retorno mensual: {best_performer['results']['monthly_return_pct']:.2f}%")
            
            portfolio = results['portfolio_results']
            if portfolio and 'monthly_return_pct' in portfolio:
                print(f"\n📊 Portfolio diversificado:")
                print(f"   Retorno mensual esperado: {portfolio['monthly_return_pct']:.2f}%")
                print(f"   Objetivo 15%: {'✅ ALCANZADO' if portfolio['target_achieved'] else '❌ NO ALCANZADO'}")
        else:
            print("\n❌ No se pudo completar el backtest")
            
    except Exception as e:
        print(f"❌ Error durante el backtest: {e}")
        import traceback
        traceback.print_exc()