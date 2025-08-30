#!/usr/bin/env python3
"""
Test de estrategias con datos reales de BTCUSDT
"""
import asyncio
import pandas as pd
import sys
from datetime import datetime

# Cargar datos reales
def load_real_data():
    """Carga los datos reales de BTCUSDT"""
    try:
        df = pd.read_csv('data/analisis/btc_real_data.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        return df
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return None

async def test_strategies_with_real_data():
    """Prueba todas las estrategias con datos reales"""
    
    print('🚀 TEST DE ESTRATEGIAS CON DATOS REALES')
    print('=' * 60)
    
    # Cargar datos reales
    df_real = load_real_data()
    if df_real is None:
        return
    
    print(f'📊 Datos reales cargados: {len(df_real)} registros')
    print(f'📅 Período: {df_real.index[0]} a {df_real.index[-1]}')
    print(f'💰 Precio inicial: ${df_real["close"].iloc[0]:,.2f}')
    print(f'💰 Precio actual: ${df_real["close"].iloc[-1]:,.2f}')
    
    change_pct = ((df_real['close'].iloc[-1] / df_real['close'].iloc[0]) - 1) * 100
    print(f'📈 Cambio periodo: {change_pct:+.2f}%')
    
    # Resetear datos para usar formato correcto (sin índice)
    df_test = df_real.reset_index()
    
    print('\n🔍 ANÁLISIS DE ESTRATEGIAS CON DATOS REALES:')
    print('-' * 60)
    
    results = {}
    
    # 1. ML Strategy
    print('\n🤖 ML STRATEGY:')
    try:
        from strategies.ml_strategy import MLStrategy
        strategy = MLStrategy()
        result = await strategy.analyze(df_test, 'BTCUSDT', '1h')
        
        print(f'   ✅ Decisión: {result.get("decision", "N/A")}')
        print(f'   📊 Score: {result.get("score", 0):.1f}')
        print(f'   🎯 Buy Prob: {result.get("ml_buy_probability", "N/A")}')
        print(f'   🎯 Sell Prob: {result.get("ml_sell_probability", "N/A")}')
        print(f'   📈 RSI: {result.get("rsi", "N/A")}')
        print(f'   📊 MACD: {result.get("macd", "N/A")}')
        
        results['ML'] = result
    except Exception as e:
        print(f'   ❌ Error: {str(e)[:60]}...')
        results['ML'] = {'error': str(e)}
    
    # 2. Simple Technical Strategy
    print('\n📈 SIMPLE TECHNICAL STRATEGY:')
    try:
        from strategies.simple_technical_strategy import SimpleTechnicalStrategy
        strategy = SimpleTechnicalStrategy()
        result = await strategy.analyze(df_test, 'BTCUSDT', '1h')
        
        print(f'   ✅ Decisión: {result.get("decision", "N/A")}')
        print(f'   📊 Score: {result.get("score", 0)}')
        print(f'   📈 RSI: {result.get("rsi", "N/A")}')
        print(f'   📊 MACD: {result.get("macd", "N/A")}')
        print(f'   🔥 Stoch K: {result.get("stoch_k", "N/A")}')
        print(f'   💎 CCI: {result.get("cci", "N/A")}')
        
        results['Technical'] = result
    except Exception as e:
        print(f'   ❌ Error: {str(e)[:60]}...')
        results['Technical'] = {'error': str(e)}
    
    # 3. Bollinger Bands Strategy
    print('\n📊 BOLLINGER BANDS STRATEGY:')
    try:
        from strategies.bollinger_bands_strategy import BollingerBandsStrategy
        strategy = BollingerBandsStrategy()
        result = strategy.analyze(df_test)
        
        print(f'   ✅ Decisión: {result.get("decision", "N/A")}')
        print(f'   📊 Score: {result.get("score", 0)}')
        print(f'   💰 Precio: ${result.get("close_price", 0):,.2f}')
        print(f'   📈 BB Superior: ${result.get("bb_upper", 0):,.2f}')
        print(f'   📉 BB Inferior: ${result.get("bb_lower", 0):,.2f}')
        
        results['Bollinger'] = result
    except Exception as e:
        print(f'   ❌ Error: {str(e)[:60]}...')
        results['Bollinger'] = {'error': str(e)}
    
    # 4. MACD Strategy
    print('\n📉 MACD STRATEGY:')
    try:
        from strategies.macd_strategy import MACDStrategy
        strategy = MACDStrategy()
        result = strategy.analyze(df_test)
        
        print(f'   ✅ Decisión: {result.get("decision", "N/A")}')
        print(f'   📊 Score: {result.get("score", 0)}')
        print(f'   📈 MACD: {result.get("macd", "N/A")}')
        print(f'   📊 MACD Signal: {result.get("macd_signal", "N/A")}')
        
        results['MACD'] = result
    except Exception as e:
        print(f'   ❌ Error: {str(e)[:60]}...')
        results['MACD'] = {'error': str(e)}
    
    # 5. Momentum Strategy
    print('\n🚀 MOMENTUM STRATEGY:')
    try:
        from strategies.momentum_strategy import MomentumStrategy
        strategy = MomentumStrategy()
        result = strategy.analyze(df_test)
        
        print(f'   ✅ Decisión: {result.get("decision", "N/A")}')
        print(f'   📊 Score: {result.get("score", 0)}')
        
        results['Momentum'] = result
    except Exception as e:
        print(f'   ❌ Error: {str(e)[:60]}...')
        results['Momentum'] = {'error': str(e)}
    
    # 6. MA Cross Strategy
    print('\n📊 MA CROSS STRATEGY:')
    try:
        from strategies.ma_cross_strategy import MACrossStrategy
        strategy = MACrossStrategy()
        result = strategy.analyze(df_test)
        
        print(f'   ✅ Decisión: {result.get("decision", "N/A")}')
        print(f'   📊 Score: {result.get("score", 0)}')
        
        results['MA_Cross'] = result
    except Exception as e:
        print(f'   ❌ Error: {str(e)[:60]}...')
        results['MA_Cross'] = {'error': str(e)}
    
    # Análisis comparativo final
    print('\n' + '='*60)
    print('📊 ANÁLISIS COMPARATIVO - DATOS REALES BTC')
    print('='*60)
    
    # Filtrar resultados válidos
    valid_results = {k: v for k, v in results.items() if 'error' not in v}
    error_results = {k: v for k, v in results.items() if 'error' in v}
    
    print(f'✅ Estrategias funcionando: {len(valid_results)}/{len(results)}')
    if error_results:
        print(f'❌ Estrategias con errores: {len(error_results)}')
    
    if valid_results:
        print('\n🏆 DECISIONES POR ESTRATEGIA:')
        print('-' * 40)
        for name, result in valid_results.items():
            decision = result.get('decision', 'N/A')
            score = result.get('score', 0)
            print(f'{name:15} | {decision:15} | Score: {score}')
        
        # Consenso
        decisions = [v.get('decision', 'ERROR') for v in valid_results.values()]
        decision_counts = {}
        for dec in decisions:
            if dec != 'ERROR':
                decision_counts[dec] = decision_counts.get(dec, 0) + 1
        
        if decision_counts:
            consensus = max(decision_counts.items(), key=lambda x: x[1])
            print(f'\n🎯 CONSENSO: {consensus[0]} ({consensus[1]}/{len(valid_results)} estrategias)')
            
            # Mostrar distribución
            print('\n📊 DISTRIBUCIÓN DE DECISIONES:')
            for decision, count in decision_counts.items():
                pct = count / len(valid_results) * 100
                print(f'   • {decision}: {count} estrategias ({pct:.1f}%)')
    
    # Análisis del mercado actual
    print('\n📈 CONTEXTO DE MERCADO ACTUAL:')
    print('-' * 30)
    
    # Últimos 5 días de cambios
    recent_data = df_real.tail(120)  # Últimas 120 horas (5 días)
    recent_change = ((recent_data['close'].iloc[-1] / recent_data['close'].iloc[0]) - 1) * 100
    volatility = recent_data['close'].pct_change().std() * 100
    
    print(f'📊 Cambio últimos 5 días: {recent_change:+.2f}%')
    print(f'⚡ Volatilidad reciente: {volatility:.2f}%')
    
    # Niveles técnicos básicos
    current_price = df_real['close'].iloc[-1]
    high_20d = df_real['high'].tail(480).max()  # 20 días
    low_20d = df_real['low'].tail(480).min()
    
    print(f'💰 Precio actual: ${current_price:,.2f}')
    print(f'🔼 Máximo 20d: ${high_20d:,.2f} ({((current_price/high_20d)-1)*100:+.1f}%)')
    print(f'🔽 Mínimo 20d: ${low_20d:,.2f} ({((current_price/low_20d)-1)*100:+.1f}%)')
    
    print(f'\n🎉 Análisis completado con datos reales de mercado!')
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_strategies_with_real_data())
