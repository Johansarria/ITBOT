# /src/analisis_rompimientos_tiempo_real.py

import asyncio
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
from binance_data_provider import BinanceDataProvider
from enhanced_logger import SicarLogger

class AnalizadorRompimientosTiempoReal:
    def __init__(self):
        self.data_provider = BinanceDataProvider()
        self.logger = SicarLogger().get_logger('rompimientos')
        
        # Símbolos principales para análisis
        self.simbolos = [
            'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 
            'DOTUSDT', 'BNBUSDT', 'XRPUSDT', 'LINKUSDT',
            'AVAXUSDT', 'MATICUSDT'
        ]
        
        # Base de datos para análisis histórico
        self.db_path = 'analisis_rompimientos_tiempo_real.db'
        self.inicializar_base_datos()
        
        # Configuración de análisis
        self.periodo_analisis = 50  # Velas para análisis
        self.umbral_volumen = 1.5   # Multiplicador de volumen promedio
        self.umbral_precio = 0.5    # % mínimo de movimiento
        
    def inicializar_base_datos(self):
        """Inicializa la base de datos para almacenar análisis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rompimientos_analisis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                simbolo TEXT,
                precio_actual REAL,
                tipo_rompimiento TEXT,
                fuerza_rompimiento REAL,
                volumen_ratio REAL,
                rsi REAL,
                nivel_soporte REAL,
                nivel_resistencia REAL,
                momentum_score REAL,
                patron_velas TEXT,
                confianza REAL,
                recomendacion TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def calcular_niveles_soporte_resistencia(self, df):
        """Calcula niveles dinámicos de soporte y resistencia"""
        highs = df['high'].rolling(window=20).max()
        lows = df['low'].rolling(window=20).min()
        
        # Niveles de resistencia (máximos locales)
        resistencia = highs.iloc[-1]
        
        # Niveles de soporte (mínimos locales)
        soporte = lows.iloc[-1]
        
        return soporte, resistencia
    
    def detectar_patron_velas(self, df):
        """Detecta patrones específicos de velas"""
        if len(df) < 3:
            return "INSUFICIENTES_DATOS"
            
        ultima = df.iloc[-1]
        anterior = df.iloc[-2]
        ante_anterior = df.iloc[-3]
        
        # Patrón Martillo
        if (ultima['close'] > ultima['open'] and 
            (ultima['low'] < min(ultima['open'], ultima['close']) - 
             (abs(ultima['close'] - ultima['open']) * 2))):
            return "MARTILLO_ALCISTA"
            
        # Patrón Estrella Fugaz
        if (ultima['close'] < ultima['open'] and 
            (ultima['high'] > max(ultima['open'], ultima['close']) + 
             (abs(ultima['close'] - ultima['open']) * 2))):
            return "ESTRELLA_FUGAZ_BAJISTA"
            
        # Patrón Envolvente Alcista
        if (ultima['close'] > ultima['open'] and 
            anterior['close'] < anterior['open'] and
            ultima['open'] < anterior['close'] and 
            ultima['close'] > anterior['open']):
            return "ENVOLVENTE_ALCISTA"
            
        # Patrón Envolvente Bajista
        if (ultima['close'] < ultima['open'] and 
            anterior['close'] > anterior['open'] and
            ultima['open'] > anterior['close'] and 
            ultima['close'] < anterior['open']):
            return "ENVOLVENTE_BAJISTA"
            
        # Tres Soldados Blancos
        if (ultima['close'] > ultima['open'] and 
            anterior['close'] > anterior['open'] and
            ante_anterior['close'] > ante_anterior['open'] and
            ultima['close'] > anterior['close'] > ante_anterior['close']):
            return "TRES_SOLDADOS_BLANCOS"
            
        # Tres Cuervos Negros
        if (ultima['close'] < ultima['open'] and 
            anterior['close'] < anterior['open'] and
            ante_anterior['close'] < ante_anterior['open'] and
            ultima['close'] < anterior['close'] < ante_anterior['close']):
            return "TRES_CUERVOS_NEGROS"
            
        return "NEUTRAL"
    
    def calcular_rsi(self, df, periodo=14):
        """Calcula el RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periodo).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periodo).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else 50
    
    def calcular_momentum_score(self, df):
        """Calcula un score de momentum basado en múltiples factores"""
        if len(df) < 20:
            return 0
            
        # Cambio de precio en diferentes períodos
        cambio_1 = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100
        cambio_5 = (df['close'].iloc[-1] / df['close'].iloc[-6] - 1) * 100
        cambio_20 = (df['close'].iloc[-1] / df['close'].iloc[-21] - 1) * 100
        
        # Volumen relativo
        volumen_promedio = df['volume'].rolling(window=20).mean().iloc[-1]
        volumen_actual = df['volume'].iloc[-1]
        volumen_ratio = volumen_actual / volumen_promedio if volumen_promedio > 0 else 1
        
        # Score combinado
        momentum_score = (cambio_1 * 0.5 + cambio_5 * 0.3 + cambio_20 * 0.2) * volumen_ratio
        
        return momentum_score
    
    def analizar_rompimiento(self, simbolo, df):
        """Analiza si hay un rompimiento significativo"""
        if len(df) < self.periodo_analisis:
            return None
            
        precio_actual = df['close'].iloc[-1]
        soporte, resistencia = self.calcular_niveles_soporte_resistencia(df)
        rsi = self.calcular_rsi(df)
        patron_velas = self.detectar_patron_velas(df)
        momentum_score = self.calcular_momentum_score(df)
        
        # Calcular volumen ratio
        volumen_promedio = df['volume'].rolling(window=20).mean().iloc[-1]
        volumen_actual = df['volume'].iloc[-1]
        volumen_ratio = volumen_actual / volumen_promedio if volumen_promedio > 0 else 1
        
        # Determinar tipo de rompimiento
        tipo_rompimiento = "NEUTRAL"
        fuerza_rompimiento = 0
        confianza = 0
        recomendacion = "MANTENER"
        
        # Rompimiento alcista
        if precio_actual > resistencia * 1.002:  # 0.2% por encima de resistencia
            distancia_resistencia = ((precio_actual - resistencia) / resistencia) * 100
            if distancia_resistencia >= self.umbral_precio and volumen_ratio >= self.umbral_volumen:
                tipo_rompimiento = "RUPTURA_ALCISTA_CONFIRMADA"
                fuerza_rompimiento = min(distancia_resistencia * volumen_ratio, 100)
                confianza = min(70 + (fuerza_rompimiento * 0.3), 95)
                recomendacion = "COMPRAR"
            elif distancia_resistencia >= self.umbral_precio * 0.5:
                tipo_rompimiento = "POSIBLE_RUPTURA_ALCISTA"
                fuerza_rompimiento = distancia_resistencia * volumen_ratio * 0.7
                confianza = min(50 + (fuerza_rompimiento * 0.2), 70)
                recomendacion = "OBSERVAR_COMPRA"
                
        # Rompimiento bajista
        elif precio_actual < soporte * 0.998:  # 0.2% por debajo de soporte
            distancia_soporte = ((soporte - precio_actual) / soporte) * 100
            if distancia_soporte >= self.umbral_precio and volumen_ratio >= self.umbral_volumen:
                tipo_rompimiento = "RUPTURA_BAJISTA_CONFIRMADA"
                fuerza_rompimiento = min(distancia_soporte * volumen_ratio, 100)
                confianza = min(70 + (fuerza_rompimiento * 0.3), 95)
                recomendacion = "VENDER"
            elif distancia_soporte >= self.umbral_precio * 0.5:
                tipo_rompimiento = "POSIBLE_RUPTURA_BAJISTA"
                fuerza_rompimiento = distancia_soporte * volumen_ratio * 0.7
                confianza = min(50 + (fuerza_rompimiento * 0.2), 70)
                recomendacion = "OBSERVAR_VENTA"
        
        # Ajustar confianza basado en RSI y patrones
        if tipo_rompimiento.startswith("RUPTURA_ALCISTA") and rsi < 70:
            confianza += 5
        elif tipo_rompimiento.startswith("RUPTURA_BAJISTA") and rsi > 30:
            confianza += 5
            
        # Ajustar por patrones de velas
        patrones_alcistas = ["MARTILLO_ALCISTA", "ENVOLVENTE_ALCISTA", "TRES_SOLDADOS_BLANCOS"]
        patrones_bajistas = ["ESTRELLA_FUGAZ_BAJISTA", "ENVOLVENTE_BAJISTA", "TRES_CUERVOS_NEGROS"]
        
        if patron_velas in patrones_alcistas and tipo_rompimiento.startswith("RUPTURA_ALCISTA"):
            confianza += 10
        elif patron_velas in patrones_bajistas and tipo_rompimiento.startswith("RUPTURA_BAJISTA"):
            confianza += 10
        
        return {
            'simbolo': simbolo,
            'precio_actual': precio_actual,
            'tipo_rompimiento': tipo_rompimiento,
            'fuerza_rompimiento': round(fuerza_rompimiento, 2),
            'volumen_ratio': round(volumen_ratio, 2),
            'rsi': round(rsi, 2),
            'nivel_soporte': round(soporte, 6),
            'nivel_resistencia': round(resistencia, 6),
            'momentum_score': round(momentum_score, 2),
            'patron_velas': patron_velas,
            'confianza': round(min(confianza, 95), 1),
            'recomendacion': recomendacion
        }
    
    def guardar_analisis(self, analisis):
        """Guarda el análisis en la base de datos"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO rompimientos_analisis 
            (simbolo, precio_actual, tipo_rompimiento, fuerza_rompimiento, 
             volumen_ratio, rsi, nivel_soporte, nivel_resistencia, 
             momentum_score, patron_velas, confianza, recomendacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            analisis['simbolo'], analisis['precio_actual'], 
            analisis['tipo_rompimiento'], analisis['fuerza_rompimiento'],
            analisis['volumen_ratio'], analisis['rsi'], 
            analisis['nivel_soporte'], analisis['nivel_resistencia'],
            analisis['momentum_score'], analisis['patron_velas'], 
            analisis['confianza'], analisis['recomendacion']
        ))
        
        conn.commit()
        conn.close()
    
    def mostrar_resumen_mercado(self, analisis_list):
        """Muestra un resumen del estado del mercado"""
        print("\n" + "="*80)
        print("🔥 ANÁLISIS DE ROMPIMIENTOS DE VELAS EN TIEMPO REAL")
        print("="*80)
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Símbolos analizados: {len(analisis_list)}")
        
        # Contar tipos de rompimientos
        rupturas_alcistas = len([a for a in analisis_list if "ALCISTA" in a['tipo_rompimiento']])
        rupturas_bajistas = len([a for a in analisis_list if "BAJISTA" in a['tipo_rompimiento']])
        neutrales = len([a for a in analisis_list if a['tipo_rompimiento'] == "NEUTRAL"])
        
        print(f"🟢 Rupturas Alcistas: {rupturas_alcistas}")
        print(f"🔴 Rupturas Bajistas: {rupturas_bajistas}")
        print(f"⚪ Neutrales: {neutrales}")
        print("-"*80)
        
        # Mostrar análisis detallado
        for analisis in sorted(analisis_list, key=lambda x: x['confianza'], reverse=True):
            emoji = "🟢" if "ALCISTA" in analisis['tipo_rompimiento'] else "🔴" if "BAJISTA" in analisis['tipo_rompimiento'] else "⚪"
            
            print(f"{emoji} {analisis['simbolo']:<10} | ${analisis['precio_actual']:<12.6f} | "
                  f"{analisis['tipo_rompimiento']:<25} | "
                  f"Confianza: {analisis['confianza']:<5.1f}% | "
                  f"RSI: {analisis['rsi']:<5.1f} | "
                  f"Vol: {analisis['volumen_ratio']:<4.1f}x")
            
            if analisis['tipo_rompimiento'] != "NEUTRAL":
                print(f"   └─ Fuerza: {analisis['fuerza_rompimiento']:.1f} | "
                      f"Momentum: {analisis['momentum_score']:.1f} | "
                      f"Patrón: {analisis['patron_velas']} | "
                      f"📋 {analisis['recomendacion']}")
        
        print("-"*80)
        
        # Resumen de recomendaciones
        compras = len([a for a in analisis_list if a['recomendacion'] == "COMPRAR"])
        ventas = len([a for a in analisis_list if a['recomendacion'] == "VENDER"])
        observar_compras = len([a for a in analisis_list if a['recomendacion'] == "OBSERVAR_COMPRA"])
        observar_ventas = len([a for a in analisis_list if a['recomendacion'] == "OBSERVAR_VENTA"])
        
        print(f"📈 RECOMENDACIONES:")
        print(f"   🟢 COMPRAR: {compras} símbolos")
        print(f"   🔴 VENDER: {ventas} símbolos")
        print(f"   👀 OBSERVAR COMPRA: {observar_compras} símbolos")
        print(f"   👀 OBSERVAR VENTA: {observar_ventas} símbolos")
        print("="*80)
    
    async def ejecutar_analisis_continuo(self):
        """Ejecuta el análisis continuo de rompimientos"""
        print("🚀 Iniciando Análisis de Rompimientos en Tiempo Real...")
        print(f"📊 Monitoreando {len(self.simbolos)} símbolos")
        print(f"⏱️  Frecuencia de análisis: cada 30 segundos")
        print("="*80)
        
        while True:
            try:
                analisis_list = []
                
                for simbolo in self.simbolos:
                    try:
                        # Obtener datos históricos
                        df = self.data_provider.get_historical_data(
                            simbolo, '1h', self.periodo_analisis
                        )
                        
                        if df is not None and len(df) >= self.periodo_analisis:
                            analisis = self.analizar_rompimiento(simbolo, df)
                            if analisis:
                                analisis_list.append(analisis)
                                self.guardar_analisis(analisis)
                                
                    except Exception as e:
                        self.logger.error(f"Error analizando {simbolo}: {e}")
                        continue
                
                # Mostrar resumen
                if analisis_list:
                    self.mostrar_resumen_mercado(analisis_list)
                
                # Esperar antes del siguiente análisis
                await asyncio.sleep(30)
                
            except Exception as e:
                self.logger.error(f"Error en análisis continuo: {e}")
                await asyncio.sleep(10)

def main():
    """Función principal"""
    analizador = AnalizadorRompimientosTiempoReal()
    
    try:
        asyncio.run(analizador.ejecutar_analisis_continuo())
    except KeyboardInterrupt:
        print("\n🛑 Análisis detenido por el usuario")
    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    main()