#!/usr/bin/env python3
"""
Análisis Comparativo del Gráfico BTCUSD vs Sistema IA
Analiza el comportamiento actual del precio y lo compara con las detecciones del sistema
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import json
from dotenv import load_dotenv
import talib

# Cargar variables de entorno
load_dotenv()

class AnalisisGraficoComparativo:
    def __init__(self):
        self.binance_base_url = "https://api.binance.com/api/v3"
        
    def obtener_datos_recientes(self, symbol="BTCUSDT", interval="5m", limit=100):
        """Obtener datos recientes de Binance"""
        try:
            url = f"{self.binance_base_url}/klines"
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            # Convertir a DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            print(f"Error obteniendo datos: {e}")
            return None
    
    def calcular_indicadores(self, df):
        """Calcular indicadores técnicos"""
        try:
            # RSI
            df['rsi'] = talib.RSI(df['close'].values, timeperiod=14)
            
            # Medias móviles
            df['ema_20'] = talib.EMA(df['close'].values, timeperiod=20)
            df['ema_50'] = talib.EMA(df['close'].values, timeperiod=50)
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(df['close'].values)
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_hist'] = macd_hist
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'].values)
            df['bb_upper'] = bb_upper
            df['bb_middle'] = bb_middle
            df['bb_lower'] = bb_lower
            
            # Volumen promedio
            df['vol_sma'] = talib.SMA(df['volume'].values, timeperiod=20)
            df['vol_ratio'] = df['volume'] / df['vol_sma']
            
            return df
            
        except Exception as e:
            print(f"Error calculando indicadores: {e}")
            return df
    
    def detectar_patrones_visuales(self, df):
        """Detectar patrones basados en la captura visual"""
        patrones = []
        
        # Obtener últimas 20 velas para análisis
        recent_data = df.tail(20).copy()
        
        # 1. Análisis de la tendencia reciente
        precio_actual = recent_data['close'].iloc[-1]
        precio_hace_10_velas = recent_data['close'].iloc[-10]
        
        if precio_actual > precio_hace_10_velas * 1.002:
            patrones.append("TENDENCIA_ALCISTA_CORTO")
        elif precio_actual < precio_hace_10_velas * 0.998:
            patrones.append("TENDENCIA_BAJISTA_CORTO")
        else:
            patrones.append("LATERAL_CONSOLIDACION")
        
        # 2. Análisis de volatilidad
        volatilidad = recent_data['high'].max() - recent_data['low'].min()
        precio_promedio = recent_data['close'].mean()
        vol_porcentaje = (volatilidad / precio_promedio) * 100
        
        if vol_porcentaje > 1.5:
            patrones.append("ALTA_VOLATILIDAD")
        elif vol_porcentaje < 0.5:
            patrones.append("BAJA_VOLATILIDAD")
        
        # 3. Análisis de soporte/resistencia
        max_reciente = recent_data['high'].max()
        min_reciente = recent_data['low'].min()
        
        # Verificar si está cerca de máximos o mínimos
        if precio_actual > max_reciente * 0.999:
            patrones.append("CERCA_RESISTENCIA")
        elif precio_actual < min_reciente * 1.001:
            patrones.append("CERCA_SOPORTE")
        
        # 4. Análisis de volumen
        vol_actual = recent_data['vol_ratio'].iloc[-1]
        if vol_actual > 1.5:
            patrones.append("VOLUMEN_ALTO")
        elif vol_actual < 0.5:
            patrones.append("VOLUMEN_BAJO")
        
        return patrones
    
    def analizar_captura_vs_sistema(self):
        """Análisis principal comparativo"""
        print("="*80)
        print("🔍 ANÁLISIS COMPARATIVO: GRÁFICO vs SISTEMA IA")
        print("="*80)
        
        # Obtener datos actuales
        df = self.obtener_datos_recientes()
        if df is None:
            print("❌ Error obteniendo datos")
            return
        
        # Calcular indicadores
        df = self.calcular_indicadores(df)
        
        # Datos actuales
        ultimo = df.iloc[-1]
        precio_actual = ultimo['close']
        rsi_actual = ultimo['rsi']
        vol_ratio = ultimo['vol_ratio']
        
        print(f"📊 DATOS ACTUALES (Hora: {datetime.now().strftime('%H:%M:%S')})")
        print(f"Precio BTCUSDT: ${precio_actual:,.2f}")
        print(f"RSI: {rsi_actual:.1f}")
        print(f"Volumen Ratio: {vol_ratio:.2f}x")
        
        # Detectar patrones visuales
        patrones_detectados = self.detectar_patrones_visuales(df)
        
        print(f"\n🎯 PATRONES DETECTADOS EN EL GRÁFICO:")
        for patron in patrones_detectados:
            print(f"  ✓ {patron}")
        
        # Análisis de la captura específica (basado en la imagen)
        print(f"\n📈 ANÁLISIS DE LA CAPTURA VISUAL:")
        print(f"  • Precio mostrado: ~$108,110.47")
        print(f"  • Timeframe: 5 minutos")
        print(f"  • Patrón visible: Movimiento lateral con ligera tendencia bajista")
        print(f"  • Rango de trading: ~$106,800 - $108,400")
        print(f"  • Volumen: Aparenta estar en niveles normales")
        
        # Comparación con sistema
        print(f"\n🤖 COMPARACIÓN CON SISTEMA IA:")
        
        # Análisis de concordancia
        concordancias = []
        discrepancias = []
        
        # Verificar si el sistema detecta correctamente el estado lateral
        if "LATERAL_CONSOLIDACION" in patrones_detectados:
            concordancias.append("✅ Sistema detecta correctamente consolidación lateral")
        else:
            discrepancias.append("⚠️ Sistema podría no detectar consolidación lateral")
        
        # Verificar RSI
        if 30 <= rsi_actual <= 70:
            concordancias.append("✅ RSI en zona neutral (concordante con lateral)")
        else:
            discrepancias.append(f"⚠️ RSI en {rsi_actual:.1f} (zona extrema)")
        
        # Verificar volumen
        if vol_ratio < 1.0:
            concordancias.append("✅ Volumen bajo concordante con consolidación")
        else:
            discrepancias.append("⚠️ Volumen alto no concordante con lateral")
        
        print("\n🎯 CONCORDANCIAS:")
        for concordancia in concordancias:
            print(f"  {concordancia}")
        
        if discrepancias:
            print("\n⚠️ DISCREPANCIAS:")
            for discrepancia in discrepancias:
                print(f"  {discrepancia}")
        
        # Recomendaciones
        print(f"\n💡 RECOMENDACIONES BASADAS EN EL ANÁLISIS:")
        
        if "LATERAL_CONSOLIDACION" in patrones_detectados:
            print("  • Mercado en consolidación - Esperar breakout")
            print("  • Niveles clave: Resistencia ~$108,400, Soporte ~$106,800")
            print("  • Estrategia: Range trading o esperar confirmación de ruptura")
        
        if vol_ratio < 0.8:
            print("  • Volumen bajo - Movimientos pueden ser falsos")
            print("  • Esperar confirmación con volumen para entradas")
        
        # Análisis de próximos movimientos
        print(f"\n🔮 PROYECCIÓN PRÓXIMOS MOVIMIENTOS:")
        
        # Calcular niveles clave
        resistance = df.tail(20)['high'].max()
        support = df.tail(20)['low'].min()
        
        print(f"  • Resistencia inmediata: ${resistance:,.2f}")
        print(f"  • Soporte inmediato: ${support:,.2f}")
        print(f"  • Rango actual: {((resistance - support) / precio_actual * 100):.2f}%")
        
        if precio_actual > (resistance + support) / 2:
            print("  • Posición: Parte alta del rango")
            print("  • Bias: Posible retroceso hacia soporte")
        else:
            print("  • Posición: Parte baja del rango")
            print("  • Bias: Posible rebote hacia resistencia")
        
        print("\n" + "="*80)

if __name__ == "__main__":
    analizador = AnalisisGraficoComparativo()
    analizador.analizar_captura_vs_sistema()