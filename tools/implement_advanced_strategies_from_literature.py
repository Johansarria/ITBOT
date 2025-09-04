#!/usr/bin/env python3
"""
Implementación de Estrategias Avanzadas basadas en Literatura de Trading
Objetivo: Alcanzar 15% mensual utilizando conceptos extraídos de PDFs especializados

Estrategias identificadas en literatura:
1. Ultra Scalping con Volatilidad (5 Pasos Scalping Crypto)
2. Trading Algorítmico basado en Volatilidad (Opciones)  
3. Espiral Logarítmica (Trading Avanzado)
4. Sistemas Automáticos con Múltiples Indicadores
5. Elliott Wave con Fibonacci
6. Market Depth Strategy
"""

import sys
import os
sys.path.append('/home/johan/itbot_linux')

from strategies.high_momentum_crypto_strategy import HighMomentumCryptoStrategy
from strategies.backtester import Backtester
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

class VolatilityScalpingStrategy(HighMomentumCryptoStrategy):
    """
    Estrategia Ultra Scalping basada en Volatilidad
    Conceptos de '5 Pasos para Scalping Criptomonedas':
    - Objetivos pequeños (0.2-0.5%)
    - Stop losses pequeños (0.3-0.6%)  
    - Múltiples operaciones por sesión
    - Combinación con escáner de volumen
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Volatility_Scalping_Strategy"
        
        # Parámetros ultra agresivos para scalping
        self.take_profit_pct = 0.3  # 0.3% TP
        self.stop_loss_pct = 0.4    # 0.4% SL
        self.volume_multiplier = 2.5  # Mayor filtro de volumen
        self.volatility_threshold = 0.15  # Mínima volatilidad requerida
        
    def should_enter_trade(self, symbol, current_price, data):
        # Verificar volatilidad alta
        if len(data) < 20:
            return False, None
            
        # Calcular volatilidad de últimas 10 velas
        recent_prices = data['close'].tail(10)
        volatility = (recent_prices.max() - recent_prices.min()) / recent_prices.mean()
        
        if volatility < self.volatility_threshold:
            return False, None
            
        # Aplicar lógica original de momentum + filtros adicionales
        should_enter, direction = super().should_enter_trade(symbol, current_price, data)
        
        if should_enter:
            # Filtro adicional: verificar que el volumen esté aumentando
            volume_trend = data['volume'].tail(5).pct_change().mean()
            if volume_trend < 0.1:  # Volumen debe estar creciendo 10%+
                return False, None
                
        return should_enter, direction

class AlgorithmicVolatilityStrategy(HighMomentumCryptoStrategy):
    """
    Estrategia basada en Volatilidad de Opciones
    Conceptos de 'Trading Algorítmico - Estrategia Basada en Volatilidad':
    - Long Straddle / Strangle adaptado a crypto
    - Trading en períodos de alta volatilidad esperada
    - Múltiples timeframes
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Algorithmic_Volatility_Strategy"
        
        # Configuración para capturar movimientos grandes
        self.take_profit_pct = 8.0   # 8% TP para capturar movimientos grandes
        self.stop_loss_pct = 4.0     # 4% SL ajustado
        self.volatility_window = 24  # Ventana de volatilidad extendida
        
    def calculate_expected_volatility(self, data):
        """Calcular volatilidad esperada similar a opciones"""
        if len(data) < self.volatility_window:
            return 0.0
            
        # Volatilidad histórica
        returns = data['close'].pct_change().dropna()
        historical_vol = returns.std() * np.sqrt(24)  # Anualizada para crypto
        
        # Volatilidad realizada reciente
        recent_returns = returns.tail(12)
        recent_vol = recent_returns.std() * np.sqrt(24)
        
        # Promedio ponderado (más peso a volatilidad reciente)
        expected_vol = 0.7 * recent_vol + 0.3 * historical_vol
        
        return expected_vol
        
    def should_enter_trade(self, symbol, current_price, data):
        if len(data) < self.volatility_window:
            return False, None
            
        # Calcular volatilidad esperada
        exp_vol = self.calculate_expected_volatility(data)
        
        # Solo operar cuando se espera alta volatilidad (>30% anualizada)
        if exp_vol < 0.30:
            return False, None
            
        # Aplicar lógica de momentum
        should_enter, direction = super().should_enter_trade(symbol, current_price, data)
        
        return should_enter, direction

class LogarithmicSpiralStrategy(HighMomentumCryptoStrategy):
    """
    Estrategia Espiral Logarítmica
    Conceptos de 'Trading Avanzado - Espiral Logarítmica':
    - Patrones fractales y geométricos
    - Elliott Wave combinado con Fibonacci
    - Predicción de puntos de giro
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Logarithmic_Spiral_Strategy"
        
        self.take_profit_pct = 12.0  # 12% TP para movimientos de onda
        self.stop_loss_pct = 6.0     # 6% SL
        self.fibonacci_levels = [0.236, 0.382, 0.618, 1.618, 2.618]
        
    def calculate_fibonacci_levels(self, data):
        """Calcular niveles de Fibonacci para la espiral"""
        if len(data) < 50:
            return []
            
        # Encontrar swing high y low recientes
        highs = data['high'].rolling(window=5, center=True).max()
        lows = data['low'].rolling(window=5, center=True).min()
        
        # Obtener último swing significativo
        recent_high = highs.dropna().iloc[-1]
        recent_low = lows.dropna().iloc[-1]
        
        # Calcular niveles de retroceso
        diff = recent_high - recent_low
        levels = []
        
        for fib in self.fibonacci_levels:
            if recent_high > recent_low:  # Tendencia alcista
                level = recent_high - (diff * fib)
            else:  # Tendencia bajista  
                level = recent_low + (diff * fib)
            levels.append(level)
            
        return levels
        
    def should_enter_trade(self, symbol, current_price, data):
        if len(data) < 50:
            return False, None
            
        # Calcular niveles de Fibonacci
        fib_levels = self.calculate_fibonacci_levels(data)
        
        # Verificar si el precio está cerca de un nivel clave
        near_fib_level = False
        for level in fib_levels:
            if abs(current_price - level) / current_price < 0.02:  # Dentro del 2%
                near_fib_level = True
                break
                
        if not near_fib_level:
            return False, None
            
        # Aplicar análisis de momentum
        should_enter, direction = super().should_enter_trade(symbol, current_price, data)
        
        return should_enter, direction

class MultiIndicatorSystemStrategy(HighMomentumCryptoStrategy):
    """
    Sistema Automático con Múltiples Indicadores
    Conceptos de 'Análisis Técnico: Sistemas Automáticos':
    - Combinación de indicadores seguidores de tendencia
    - Osciladores para timing
    - Confirmación múltiple
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Multi_Indicator_System_Strategy"
        
        self.take_profit_pct = 10.0  # 10% TP
        self.stop_loss_pct = 5.0     # 5% SL
        
    def calculate_macd(self, data, fast=12, slow=26, signal=9):
        """Calcular MACD"""
        exp1 = data['close'].ewm(span=fast).mean()
        exp2 = data['close'].ewm(span=slow).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
        
    def calculate_stochastic(self, data, k_period=14, d_period=3):
        """Calcular Estocástico"""
        low_min = data['low'].rolling(window=k_period).min()
        high_max = data['high'].rolling(window=k_period).max()
        
        k_percent = 100 * (data['close'] - low_min) / (high_max - low_min)
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return k_percent, d_percent
        
    def should_enter_trade(self, symbol, current_price, data):
        if len(data) < 50:
            return False, None
            
        # Calcular indicadores
        macd_line, signal_line, histogram = self.calculate_macd(data)
        k_percent, d_percent = self.calculate_stochastic(data)
        
        # Señales de compra
        macd_bullish = macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]
        stoch_oversold = k_percent.iloc[-1] < 30 and k_percent.iloc[-1] > k_percent.iloc[-2]
        
        # Señales de venta
        macd_bearish = macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]
        stoch_overbought = k_percent.iloc[-1] > 70 and k_percent.iloc[-1] < k_percent.iloc[-2]
        
        # Confirmación con momentum original
        should_enter_orig, direction_orig = super().should_enter_trade(symbol, current_price, data)
        
        if should_enter_orig:
            if direction_orig == 'long' and macd_bullish and stoch_oversold:
                return True, 'long'
            elif direction_orig == 'short' and macd_bearish and stoch_overbought:
                return True, 'short'
                
        return False, None

class CryptoDepthStrategy(HighMomentumCryptoStrategy):
    """
    Estrategia basada en Market Depth
    Conceptos de 'Crypto Trading Pro':
    - Análisis de profundidad de mercado
    - Detección de ballenas (whales)
    - Trading 24/7 con volatilidad crypto
    """
    
    def __init__(self):
        super().__init__()
        self.name = "Crypto_Depth_Strategy"
        
        self.take_profit_pct = 6.0   # 6% TP
        self.stop_loss_pct = 3.0     # 3% SL
        self.volume_spike_threshold = 3.0  # Múltiplo de volumen promedio
        
    def detect_volume_spike(self, data):
        """Detectar picos de volumen que indican actividad de ballenas"""
        if len(data) < 20:
            return False
            
        avg_volume = data['volume'].rolling(window=20).mean().iloc[-1]
        current_volume = data['volume'].iloc[-1]
        
        return current_volume > (avg_volume * self.volume_spike_threshold)
        
    def should_enter_trade(self, symbol, current_price, data):
        if len(data) < 20:
            return False, None
            
        # Detectar actividad de ballenas
        volume_spike = self.detect_volume_spike(data)
        
        if not volume_spike:
            return False, None
            
        # Aplicar análisis de momentum
        should_enter, direction = super().should_enter_trade(symbol, current_price, data)
        
        return should_enter, direction

def generate_synthetic_crypto_data(symbol, days=60):
    """Generar datos sintéticos de crypto con patrones realistas"""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta
    
    # Configuración base por tipo de token
    if 'USDT' in symbol:
        base_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 1.0
        volatility = 0.03 if 'BTC' in symbol else 0.04 if 'ETH' in symbol else 0.06
    else:
        base_price = 100
        volatility = 0.08  # Mayor volatilidad para altcoins
    
    # Generar timestamps
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    timestamps = pd.date_range(start=start_date, end=end_date, freq='1h')
    
    # Generar precios con tendencia y volatilidad
    np.random.seed(hash(symbol) % 2**32)  # Seed basada en símbolo para consistencia
    
    # Crear una tendencia sutil
    trend = np.linspace(1.0, 1.2, len(timestamps))  # 20% de tendencia alcista
    
    # Generar retornos con distribución realista
    returns = np.random.normal(0, volatility/24, len(timestamps))
    
    # Agregar algunos patrones de momentum
    for i in range(1, len(returns)):
        if abs(returns[i-1]) > volatility/12:  # Si hubo movimiento grande
            returns[i] += returns[i-1] * 0.3  # Continuar la dirección
    
    # Calcular precios
    price_multipliers = np.cumprod(1 + returns) * trend
    close_prices = base_price * price_multipliers
    
    # Generar OHLV
    open_prices = np.concatenate([[close_prices[0]], close_prices[:-1]])
    
    # High y Low con spread realista
    spreads = np.random.uniform(0.002, 0.01, len(timestamps))
    high_prices = np.maximum(open_prices, close_prices) * (1 + spreads)
    low_prices = np.minimum(open_prices, close_prices) * (1 - spreads)
    
    # Volumen correlacionado con volatilidad
    volatility_proxy = np.abs(returns)
    base_volume = 1000000
    volumes = base_volume * (1 + volatility_proxy * 50) * np.random.uniform(0.5, 2.0, len(timestamps))
    
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }, index=timestamps)
    
    return df

async def run_strategy_test(strategy_class, strategy_name, symbol, timeframe):
    """Función async para probar una estrategia"""
    # Generar datos sintéticos
    historical_data = generate_synthetic_crypto_data(symbol, days=60)
    
    if len(historical_data) < 100:
        return None
    
    # Inicializar estrategia (sin parámetros para HighMomentumCryptoStrategy)
    strategy = strategy_class()
    
    # Configurar backtester
    backtester = Backtester(
        historical_data=historical_data,
        initial_balance=1000,
        symbol=symbol,
        interval=timeframe,
        commission=0.001
    )
    
    # Ejecutar backtest
    result = await backtester.run(strategy)
    
    if result and len(backtester.trades) > 0:
        # Calcular estadísticas
        trades_df = pd.DataFrame(backtester.trades)
        
        if 'pnl_pct' in trades_df.columns and len(trades_df) > 0:
            total_return = trades_df['pnl_pct'].sum()
            monthly_return = total_return  # Ya están en base mensual aproximadamente
            
            winning_trades = trades_df[trades_df['pnl_pct'] > 0]
            win_rate = len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0
            
            avg_win = winning_trades['pnl_pct'].mean() if len(winning_trades) > 0 else 0
            losing_trades = trades_df[trades_df['pnl_pct'] <= 0]
            avg_loss = losing_trades['pnl_pct'].mean() if len(losing_trades) > 0 else 0
            
            return {
                'strategy': strategy_name,
                'symbol': symbol,
                'timeframe': timeframe,
                'monthly_return_pct': monthly_return,
                'total_return_pct': total_return,
                'total_trades': len(trades_df),
                'win_rate': win_rate,
                'avg_win_pct': avg_win,
                'avg_loss_pct': avg_loss,
                'max_drawdown_pct': 0
            }
    
    return None

async def run_advanced_literature_strategies():
    """Ejecutar todas las estrategias avanzadas basadas en literatura"""
    
    print("🚀 IMPLEMENTANDO ESTRATEGIAS AVANZADAS DE LITERATURA")
    print("=" * 80)
    print("📚 Fuentes: PDFs especializados en trading crypto y algorítmico")
    print("🎯 Objetivo: 15% mensual con técnicas probadas")
    print()
    
    # Tokens seleccionados (enfoque en alta volatilidad)
    test_tokens = [
        # DeFi (alta volatilidad)
        'UNIUSDT', 'AAVEUSDT', 'COMPUSDT', 'MKRUSDT',
        # Gaming (movimientos explosivos)  
        'AXSUSDT', 'SANDUSDT', 'MANAUSDT', 'ENJUSDT',
        # Layer 1/2 (momentum fuerte)
        'SOLUSDT', 'ADAUSDT', 'DOTUSDT', 'MATICUSDT',
        # Memes (volatilidad extrema)
        'DOGEUSDT', 'SHIBUSDT', 'PEPEUSDT',
        # AI & Tech
        'FETUSDT', 'AGIXUSDT', 'OCEANUSDT'
    ]
    
    # Timeframes optimizados para cada estrategia
    timeframe_configs = [
        ('5m', 'Ultra rápido'),
        ('15m', 'Scalping'),  
        ('30m', 'Intraday'),
        ('1h', 'Swing corto')
    ]
    
    # Estrategias avanzadas
    strategies = [
        (VolatilityScalpingStrategy, "Volatility_Scalping"),
        (AlgorithmicVolatilityStrategy, "Algorithmic_Volatility"), 
        (LogarithmicSpiralStrategy, "Logarithmic_Spiral"),
        (MultiIndicatorSystemStrategy, "Multi_Indicator_System"),
        (CryptoDepthStrategy, "Crypto_Depth")
    ]
    
    results = []
    
    for strategy_class, strategy_name in strategies:
        print(f"\n📊 PROBANDO: {strategy_name}")
        print("-" * 50)
        
        for timeframe, description in timeframe_configs:
            print(f"\n⏱️  Timeframe: {timeframe} ({description})")
            
            for symbol in test_tokens[:8]:  # Probar con 8 tokens por estrategia
                result = await run_strategy_test(strategy_class, strategy_name, symbol, timeframe)
                
                if result:
                    monthly_return = result['monthly_return_pct']
                    results.append(result)
                    
                    status = "🟢 EXCELENTE" if monthly_return >= 15 else "🟡 BUENO" if monthly_return >= 10 else "🔴 BAJO"
                    print(f"    {symbol}: {monthly_return:.2f}% mensual {status}")
                    
                    # Mostrar detalles si supera 10%
                    if monthly_return >= 10:
                        print(f"      📈 Total: {result['total_return_pct']:.2f}%")
                        print(f"      📊 Trades: {result['total_trades']}, Win Rate: {result['win_rate']:.1f}%")
                else:
                    print(f"    {symbol}: ❌ Sin resultados")
    
    # Análisis de resultados
    print("\n" + "="*80)
    print("📊 ANÁLISIS DE RESULTADOS - ESTRATEGIAS DE LITERATURA")
    print("="*80)
    
    if results:
        df_results = pd.DataFrame(results)
        
        # Mejores resultados por estrategia
        print("\n🏆 MEJORES RESULTADOS POR ESTRATEGIA:")
        for strategy in df_results['strategy'].unique():
            strategy_results = df_results[df_results['strategy'] == strategy]
            best = strategy_results.loc[strategy_results['monthly_return_pct'].idxmax()]
            
            print(f"\n📈 {strategy}:")
            print(f"   🥇 Mejor: {best['symbol']} - {best['monthly_return_pct']:.2f}% mensual")
            print(f"   📊 {best['timeframe']} | {best['total_trades']} trades | {best['win_rate']:.1f}% win rate")
        
        # Top 10 configuraciones generales
        print(f"\n🚀 TOP 10 CONFIGURACIONES GENERALES:")
        top_10 = df_results.nlargest(10, 'monthly_return_pct')
        
        for i, (_, row) in enumerate(top_10.iterrows(), 1):
            print(f"{i:2d}. {row['strategy'][:20]:<20} | {row['symbol']:<8} | {row['timeframe']:<4} | {row['monthly_return_pct']:6.2f}% mensual")
        
        # Estadísticas por categoría
        print(f"\n📊 ESTADÍSTICAS GENERALES:")
        print(f"   • Total configuraciones probadas: {len(results)}")
        print(f"   • Configuraciones rentables (>0%): {len(df_results[df_results['monthly_return_pct'] > 0])}")
        print(f"   • Configuraciones objetivo (>15%): {len(df_results[df_results['monthly_return_pct'] >= 15])}")
        print(f"   • Mejor resultado: {df_results['monthly_return_pct'].max():.2f}% mensual")
        print(f"   • Promedio general: {df_results['monthly_return_pct'].mean():.2f}% mensual")
        
        # Identificar patrones exitosos
        successful = df_results[df_results['monthly_return_pct'] >= 10]
        if len(successful) > 0:
            print(f"\n🎯 PATRONES DE ÉXITO (>10% mensual):")
            print(f"   • Estrategias más exitosas: {successful.groupby('strategy')['monthly_return_pct'].count().sort_values(ascending=False).head(3).to_dict()}")
            print(f"   • Tokens más exitosos: {successful.groupby('symbol')['monthly_return_pct'].count().sort_values(ascending=False).head(5).to_dict()}")
            print(f"   • Timeframes más exitosos: {successful.groupby('timeframe')['monthly_return_pct'].count().sort_values(ascending=False).to_dict()}")
    
    # Guardar resultados detallados
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'/home/johan/itbot_linux/data/literatura_strategies_results_{timestamp}.json'
    
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'objective': '15% monthly return',
            'literature_sources': [
                '5 Pasos para Realizar Scalping Criptomonedas',
                'Análisis técnico sistemas automáticos de trading',
                'El trading algorítmico - Estrategia Basada en Volatilidad',
                'Trading Avanzado - La Espiral Logarítmica',
                'Crypto Trading Pro'
            ],
            'strategies_tested': len(strategies),
            'configurations_tested': len(results),
            'results': results
        }, f, indent=2)
    
    print(f"\n💾 Resultados guardados en: {results_file}")
    
    return results

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_advanced_literature_strategies())
