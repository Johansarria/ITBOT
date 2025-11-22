# /src/detector_rupturas_velas.py

import asyncio
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass
from enum import Enum

# Importaciones locales
from binance_data_provider import BinanceDataProvider

class TipoRuptura(Enum):
    RUPTURA_ALCISTA = "RUPTURA_ALCISTA"
    RUPTURA_BAJISTA = "RUPTURA_BAJISTA"
    POSIBLE_RUPTURA_ALCISTA = "POSIBLE_RUPTURA_ALCISTA"
    POSIBLE_RUPTURA_BAJISTA = "POSIBLE_RUPTURA_BAJISTA"
    SIN_RUPTURA = "SIN_RUPTURA"

@dataclass
class DeteccionRuptura:
    simbolo: str
    tipo: TipoRuptura
    precio_actual: float
    precio_ruptura: float
    nivel_soporte_resistencia: float
    volumen_confirmacion: bool
    fuerza_ruptura: float  # 0-1
    confianza: float  # 0-1
    timestamp: datetime
    velas_confirmacion: int
    momentum_score: float

class DetectorRupturasVelas:
    def __init__(self):
        self.logger = self._setup_logging()
        self.data_provider = BinanceDataProvider()
        self.db_path = "detector_rupturas_velas.db"
        self.simbolos = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'DOTUSDT', 
                        'BNBUSDT', 'XRPUSDT', 'LINKUSDT', 'LTCUSDT', 'AVAXUSDT']
        
        # Parámetros de detección
        self.periodo_analisis = 20  # Velas para análisis de S/R
        self.min_velas_confirmacion = 2  # Mínimo velas para confirmar ruptura
        self.umbral_volumen = 1.5  # Multiplicador de volumen promedio
        self.umbral_fuerza_ruptura = 0.02  # 2% mínimo para considerar ruptura
        
        self._init_database()
        
    def _setup_logging(self):
        """Configurar sistema de logging"""
        logger = logging.getLogger('DetectorRupturas')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
        
    def _init_database(self):
        """Inicializar base de datos para rupturas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabla para detecciones de rupturas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detecciones_rupturas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simbolo TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    precio_actual REAL NOT NULL,
                    precio_ruptura REAL NOT NULL,
                    nivel_sr REAL NOT NULL,
                    volumen_confirmacion BOOLEAN NOT NULL,
                    fuerza_ruptura REAL NOT NULL,
                    confianza REAL NOT NULL,
                    velas_confirmacion INTEGER NOT NULL,
                    momentum_score REAL NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla para niveles de soporte y resistencia
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS niveles_sr (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simbolo TEXT NOT NULL,
                    nivel REAL NOT NULL,
                    tipo TEXT NOT NULL,  -- 'SOPORTE' o 'RESISTENCIA'
                    fuerza REAL NOT NULL,  -- Número de toques
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            self.logger.info("✅ Base de datos inicializada correctamente")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando base de datos: {e}")
            
    def calcular_niveles_sr(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Calcular niveles de soporte y resistencia"""
        try:
            highs = df['high'].values
            lows = df['low'].values
            closes = df['close'].values
            
            # Encontrar máximos y mínimos locales
            resistencias = []
            soportes = []
            
            # Buscar máximos locales (resistencias)
            for i in range(2, len(highs) - 2):
                if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                    highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                    resistencias.append(highs[i])
                    
            # Buscar mínimos locales (soportes)
            for i in range(2, len(lows) - 2):
                if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                    lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                    soportes.append(lows[i])
            
            # Agrupar niveles cercanos
            resistencias = self._agrupar_niveles(resistencias)
            soportes = self._agrupar_niveles(soportes)
            
            return {
                'resistencias': resistencias,
                'soportes': soportes
            }
            
        except Exception as e:
            self.logger.error(f"Error calculando niveles S/R: {e}")
            return {'resistencias': [], 'soportes': []}
            
    def _agrupar_niveles(self, niveles: List[float], tolerancia: float = 0.005) -> List[float]:
        """Agrupar niveles cercanos"""
        if not niveles:
            return []
            
        niveles_ordenados = sorted(niveles)
        grupos = []
        grupo_actual = [niveles_ordenados[0]]
        
        for nivel in niveles_ordenados[1:]:
            if abs(nivel - grupo_actual[-1]) / grupo_actual[-1] <= tolerancia:
                grupo_actual.append(nivel)
            else:
                grupos.append(np.mean(grupo_actual))
                grupo_actual = [nivel]
                
        grupos.append(np.mean(grupo_actual))
        return grupos
        
    def detectar_ruptura_vela(self, df: pd.DataFrame, niveles_sr: Dict) -> DeteccionRuptura:
        """Detectar rupturas de velas específicas"""
        try:
            if len(df) < self.min_velas_confirmacion + 1:
                return None
                
            precio_actual = df['close'].iloc[-1]
            volumen_actual = df['volume'].iloc[-1]
            volumen_promedio = df['volume'].rolling(20).mean().iloc[-1]
            
            # Calcular momentum
            momentum_score = self._calcular_momentum(df)
            
            # Verificar ruptura de resistencia (alcista)
            for resistencia in niveles_sr['resistencias']:
                if self._verificar_ruptura_alcista(df, resistencia, volumen_actual, volumen_promedio):
                    fuerza = abs(precio_actual - resistencia) / resistencia
                    confianza = self._calcular_confianza_ruptura(df, resistencia, 'alcista')
                    
                    return DeteccionRuptura(
                        simbolo=df.attrs.get('simbolo', 'UNKNOWN'),
                        tipo=TipoRuptura.RUPTURA_ALCISTA,
                        precio_actual=precio_actual,
                        precio_ruptura=precio_actual,
                        nivel_soporte_resistencia=resistencia,
                        volumen_confirmacion=volumen_actual > volumen_promedio * self.umbral_volumen,
                        fuerza_ruptura=fuerza,
                        confianza=confianza,
                        timestamp=datetime.now(),
                        velas_confirmacion=self._contar_velas_confirmacion(df, resistencia, 'alcista'),
                        momentum_score=momentum_score
                    )
            
            # Verificar ruptura de soporte (bajista)
            for soporte in niveles_sr['soportes']:
                if self._verificar_ruptura_bajista(df, soporte, volumen_actual, volumen_promedio):
                    fuerza = abs(soporte - precio_actual) / soporte
                    confianza = self._calcular_confianza_ruptura(df, soporte, 'bajista')
                    
                    return DeteccionRuptura(
                        simbolo=df.attrs.get('simbolo', 'UNKNOWN'),
                        tipo=TipoRuptura.RUPTURA_BAJISTA,
                        precio_actual=precio_actual,
                        precio_ruptura=precio_actual,
                        nivel_soporte_resistencia=soporte,
                        volumen_confirmacion=volumen_actual > volumen_promedio * self.umbral_volumen,
                        fuerza_ruptura=fuerza,
                        confianza=confianza,
                        timestamp=datetime.now(),
                        velas_confirmacion=self._contar_velas_confirmacion(df, soporte, 'bajista'),
                        momentum_score=momentum_score
                    )
            
            # Verificar posibles rupturas
            return self._detectar_posible_ruptura(df, niveles_sr, momentum_score)
            
        except Exception as e:
            self.logger.error(f"Error detectando ruptura: {e}")
            return None
            
    def _verificar_ruptura_alcista(self, df: pd.DataFrame, resistencia: float, 
                                  volumen_actual: float, volumen_promedio: float) -> bool:
        """Verificar si hay ruptura alcista confirmada"""
        precio_actual = df['close'].iloc[-1]
        precio_anterior = df['close'].iloc[-2]
        
        # Condiciones para ruptura alcista
        ruptura_precio = precio_actual > resistencia and precio_anterior <= resistencia
        ruptura_fuerte = (precio_actual - resistencia) / resistencia >= self.umbral_fuerza_ruptura
        volumen_confirmado = volumen_actual > volumen_promedio * self.umbral_volumen
        
        return ruptura_precio and ruptura_fuerte and volumen_confirmado
        
    def _verificar_ruptura_bajista(self, df: pd.DataFrame, soporte: float,
                                  volumen_actual: float, volumen_promedio: float) -> bool:
        """Verificar si hay ruptura bajista confirmada"""
        precio_actual = df['close'].iloc[-1]
        precio_anterior = df['close'].iloc[-2]
        
        # Condiciones para ruptura bajista
        ruptura_precio = precio_actual < soporte and precio_anterior >= soporte
        ruptura_fuerte = (soporte - precio_actual) / soporte >= self.umbral_fuerza_ruptura
        volumen_confirmado = volumen_actual > volumen_promedio * self.umbral_volumen
        
        return ruptura_precio and ruptura_fuerte and volumen_confirmado
        
    def _detectar_posible_ruptura(self, df: pd.DataFrame, niveles_sr: Dict, 
                                 momentum_score: float) -> Optional[DeteccionRuptura]:
        """Detectar posibles rupturas (setup pre-breakout)"""
        precio_actual = df['close'].iloc[-1]
        
        # Buscar proximidad a resistencias (posible ruptura alcista)
        for resistencia in niveles_sr['resistencias']:
            distancia = abs(precio_actual - resistencia) / resistencia
            if distancia <= 0.01 and momentum_score > 0.6:  # Dentro del 1% y momentum positivo
                confianza = self._calcular_confianza_posible_ruptura(df, resistencia, 'alcista')
                
                return DeteccionRuptura(
                    simbolo=df.attrs.get('simbolo', 'UNKNOWN'),
                    tipo=TipoRuptura.POSIBLE_RUPTURA_ALCISTA,
                    precio_actual=precio_actual,
                    precio_ruptura=resistencia,
                    nivel_soporte_resistencia=resistencia,
                    volumen_confirmacion=False,
                    fuerza_ruptura=distancia,
                    confianza=confianza,
                    timestamp=datetime.now(),
                    velas_confirmacion=0,
                    momentum_score=momentum_score
                )
        
        # Buscar proximidad a soportes (posible ruptura bajista)
        for soporte in niveles_sr['soportes']:
            distancia = abs(precio_actual - soporte) / soporte
            if distancia <= 0.01 and momentum_score < -0.6:  # Dentro del 1% y momentum negativo
                confianza = self._calcular_confianza_posible_ruptura(df, soporte, 'bajista')
                
                return DeteccionRuptura(
                    simbolo=df.attrs.get('simbolo', 'UNKNOWN'),
                    tipo=TipoRuptura.POSIBLE_RUPTURA_BAJISTA,
                    precio_actual=precio_actual,
                    precio_ruptura=soporte,
                    nivel_soporte_resistencia=soporte,
                    volumen_confirmacion=False,
                    fuerza_ruptura=distancia,
                    confianza=confianza,
                    timestamp=datetime.now(),
                    velas_confirmacion=0,
                    momentum_score=momentum_score
                )
        
        return None
        
    def _calcular_momentum(self, df: pd.DataFrame) -> float:
        """Calcular score de momentum (-1 a 1)"""
        try:
            # RSI momentum
            rsi = self._calcular_rsi(df['close'], 14)
            rsi_score = (rsi - 50) / 50  # Normalizar a -1, 1
            
            # MACD momentum
            macd_line, macd_signal = self._calcular_macd(df['close'])
            macd_score = 1 if macd_line > macd_signal else -1
            
            # Precio vs MA momentum
            ma20 = df['close'].rolling(20).mean().iloc[-1]
            precio_actual = df['close'].iloc[-1]
            ma_score = (precio_actual - ma20) / ma20
            ma_score = max(-1, min(1, ma_score * 10))  # Normalizar
            
            # Combinar scores
            momentum_final = (rsi_score * 0.4 + macd_score * 0.3 + ma_score * 0.3)
            return max(-1, min(1, momentum_final))
            
        except Exception as e:
            self.logger.error(f"Error calculando momentum: {e}")
            return 0
            
    def _calcular_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calcular RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1]
        except:
            return 50
            
    def _calcular_macd(self, prices: pd.Series) -> Tuple[float, float]:
        """Calcular MACD"""
        try:
            ema12 = prices.ewm(span=12).mean()
            ema26 = prices.ewm(span=26).mean()
            macd_line = ema12 - ema26
            macd_signal = macd_line.ewm(span=9).mean()
            return macd_line.iloc[-1], macd_signal.iloc[-1]
        except:
            return 0, 0
            
    def _calcular_confianza_ruptura(self, df: pd.DataFrame, nivel: float, tipo: str) -> float:
        """Calcular confianza de ruptura confirmada"""
        try:
            # Factores de confianza
            volumen_factor = min(1.0, df['volume'].iloc[-1] / df['volume'].rolling(20).mean().iloc[-1] / 2)
            
            # Fuerza de la ruptura
            precio_actual = df['close'].iloc[-1]
            if tipo == 'alcista':
                fuerza_factor = min(1.0, (precio_actual - nivel) / nivel * 50)
            else:
                fuerza_factor = min(1.0, (nivel - precio_actual) / nivel * 50)
            
            # Consistencia de velas
            velas_confirmacion = self._contar_velas_confirmacion(df, nivel, tipo)
            consistencia_factor = min(1.0, velas_confirmacion / 3)
            
            confianza = (volumen_factor * 0.4 + fuerza_factor * 0.4 + consistencia_factor * 0.2)
            return max(0.1, min(1.0, confianza))
            
        except Exception as e:
            self.logger.error(f"Error calculando confianza: {e}")
            return 0.5
            
    def _calcular_confianza_posible_ruptura(self, df: pd.DataFrame, nivel: float, tipo: str) -> float:
        """Calcular confianza de posible ruptura"""
        try:
            # Para posibles rupturas, la confianza es menor
            confianza_base = self._calcular_confianza_ruptura(df, nivel, tipo)
            return max(0.1, min(0.7, confianza_base * 0.6))  # Máximo 70% para posibles
        except:
            return 0.3
            
    def _contar_velas_confirmacion(self, df: pd.DataFrame, nivel: float, tipo: str) -> int:
        """Contar velas que confirman la ruptura"""
        try:
            count = 0
            for i in range(max(0, len(df) - 5), len(df)):  # Últimas 5 velas
                if tipo == 'alcista' and df['close'].iloc[i] > nivel:
                    count += 1
                elif tipo == 'bajista' and df['close'].iloc[i] < nivel:
                    count += 1
            return count
        except:
            return 0
            
    def guardar_deteccion(self, deteccion: DeteccionRuptura):
        """Guardar detección en base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO detecciones_rupturas 
                (simbolo, tipo, precio_actual, precio_ruptura, nivel_sr, 
                 volumen_confirmacion, fuerza_ruptura, confianza, 
                 velas_confirmacion, momentum_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                deteccion.simbolo,
                deteccion.tipo.value,
                deteccion.precio_actual,
                deteccion.precio_ruptura,
                deteccion.nivel_soporte_resistencia,
                deteccion.volumen_confirmacion,
                deteccion.fuerza_ruptura,
                deteccion.confianza,
                deteccion.velas_confirmacion,
                deteccion.momentum_score
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Error guardando detección: {e}")
            
    def analizar_simbolo(self, simbolo: str) -> Optional[DeteccionRuptura]:
        """Analizar un símbolo específico para rupturas"""
        try:
            # Obtener datos históricos
            df = self.data_provider.get_historical_data(
                simbolo, '1h', limit=100
            )
            
            if df is None or len(df) < self.periodo_analisis:
                return None
                
            # Agregar símbolo como atributo
            df.attrs['simbolo'] = simbolo
            
            # Calcular niveles de soporte y resistencia
            niveles_sr = self.calcular_niveles_sr(df)
            
            # Detectar rupturas
            deteccion = self.detectar_ruptura_vela(df, niveles_sr)
            
            if deteccion:
                self.guardar_deteccion(deteccion)
                
            return deteccion
            
        except Exception as e:
            self.logger.error(f"Error analizando {simbolo}: {e}")
            return None
            
    def mostrar_interfaz(self, detecciones: List[DeteccionRuptura]):
        """Mostrar interfaz de rupturas en tiempo real"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("🔥" * 80)
        print("🚀 DETECTOR DE RUPTURAS DE VELAS - TIEMPO REAL 🚀".center(80))
        print("🔥" * 80)
        print()
        
        # Estadísticas generales
        rupturas_confirmadas = [d for d in detecciones if 'RUPTURA_' in d.tipo.value and 'POSIBLE' not in d.tipo.value]
        posibles_rupturas = [d for d in detecciones if 'POSIBLE' in d.tipo.value]
        
        print(f"📊 ESTADÍSTICAS:")
        print(f"   🔴 Rupturas Confirmadas: {len(rupturas_confirmadas)}")
        print(f"   🟡 Posibles Rupturas: {len(posibles_rupturas)}")
        print(f"   📈 Total Detecciones: {len(detecciones)}")
        print()
        
        if detecciones:
            print("🎯 DETECCIONES ACTIVAS:")
            print("─" * 80)
            print(f"{'SÍMBOLO':<10} {'TIPO':<20} {'PRECIO':<12} {'NIVEL S/R':<12} {'CONFIANZA':<10} {'MOMENTUM':<10}")
            print("─" * 80)
            
            for deteccion in sorted(detecciones, key=lambda x: x.confianza, reverse=True):
                # Iconos según tipo
                if deteccion.tipo == TipoRuptura.RUPTURA_ALCISTA:
                    icono = "🚀"
                elif deteccion.tipo == TipoRuptura.RUPTURA_BAJISTA:
                    icono = "📉"
                elif deteccion.tipo == TipoRuptura.POSIBLE_RUPTURA_ALCISTA:
                    icono = "⬆️"
                elif deteccion.tipo == TipoRuptura.POSIBLE_RUPTURA_BAJISTA:
                    icono = "⬇️"
                else:
                    icono = "⚪"
                
                tipo_display = deteccion.tipo.value.replace('_', ' ')
                momentum_display = f"{deteccion.momentum_score:+.2f}"
                
                print(f"{deteccion.simbolo:<10} {icono} {tipo_display:<18} "
                      f"${deteccion.precio_actual:<11.4f} ${deteccion.nivel_soporte_resistencia:<11.4f} "
                      f"{deteccion.confianza:<9.2f} {momentum_display:<10}")
        else:
            print("⏳ Esperando detecciones de rupturas...")
            
        print("─" * 80)
        print(f"🕒 Última actualización: {datetime.now().strftime('%H:%M:%S')}")
        print("🔄 Próxima actualización en 30 segundos... | Ctrl+C para detener")
        print("─" * 80)
        
    async def ejecutar_analisis_continuo(self):
        """Ejecutar análisis continuo de rupturas"""
        self.logger.info("🚀 Iniciando detector de rupturas de velas...")
        
        while True:
            try:
                detecciones_actuales = []
                
                # Analizar todos los símbolos
                for simbolo in self.simbolos:
                    deteccion = self.analizar_simbolo(simbolo)
                    if deteccion:
                        detecciones_actuales.append(deteccion)
                        
                        # Log para rupturas importantes
                        if deteccion.confianza > 0.7:
                            self.logger.info(f"🔥 {deteccion.tipo.value} detectada en {simbolo} "
                                           f"- Confianza: {deteccion.confianza:.2f}")
                
                # Mostrar interfaz
                self.mostrar_interfaz(detecciones_actuales)
                
                # Esperar antes del siguiente ciclo
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Deteniendo detector de rupturas...")
                break
            except Exception as e:
                self.logger.error(f"❌ Error en análisis continuo: {e}")
                await asyncio.sleep(5)

async def main():
    """Función principal"""
    detector = DetectorRupturasVelas()
    await detector.ejecutar_analisis_continuo()

if __name__ == "__main__":
    asyncio.run(main())