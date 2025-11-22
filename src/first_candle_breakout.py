"""
SICAR - First Candle Breakout Strategy
Algoritmo de detección de rupturas en la primera vela de cada sesión
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
import time

from session_detector import SessionDetector
from binance_data_provider import BinanceDataProvider

@dataclass
class BreakoutSignal:
    """Estructura para señales de ruptura"""
    timestamp: datetime
    symbol: str
    session: str
    signal_type: str  # 'bullish_breakout', 'bearish_breakout', 'no_signal'
    entry_price: float
    stop_loss: float
    take_profit: float
    volume_ratio: float
    confidence: float
    candle_data: Dict[str, float]
    
class FirstCandleBreakoutDetector:
    """
    Detector de rupturas en la primera vela de sesiones de trading
    Implementa la estrategia First Candle Breakout validada
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.session_detector = SessionDetector()
        self.binance_provider = BinanceDataProvider()
        
        # Parámetros validados para sesión europea
        self.session_params = {
            'european': {
                'stop_loss_pct': 0.0013,      # 0.13%
                'take_profit_pct': 0.0039,    # 0.39%
                'position_size_pct': 0.95,    # 95%
                'min_volume_ratio': 1.5,      # Volumen mínimo vs promedio
                'min_price_move_pct': 0.0008, # Movimiento mínimo 0.08%
                'max_spread_pct': 0.0005,     # Spread máximo 0.05%
                'confidence_threshold': 0.7   # Confianza mínima
            },
            'american': {
                'stop_loss_pct': 0.0015,      # 0.15%
                'take_profit_pct': 0.0045,    # 0.45%
                'position_size_pct': 0.85,    # 85%
                'min_volume_ratio': 1.8,      # Mayor volumen requerido
                'min_price_move_pct': 0.0010, # 0.10%
                'max_spread_pct': 0.0004,     # 0.04%
                'confidence_threshold': 0.75
            },
            'asian': {
                'stop_loss_pct': 0.0018,      # 0.18%
                'take_profit_pct': 0.0054,    # 0.54%
                'position_size_pct': 0.75,    # 75%
                'min_volume_ratio': 1.3,      # Menor volumen típico
                'min_price_move_pct': 0.0012, # 0.12%
                'max_spread_pct': 0.0006,     # 0.06%
                'confidence_threshold': 0.65
            }
        }
        
        # Símbolos para trading (formato Binance) - Optimizados para rupturas
        self.trading_symbols = [
            # Forex principales
            'EURUSDT',    # EUR/USD - Par principal, alta liquidez
            'USDCUSDT',   # USD Coin - Stablecoin líquida (reemplaza GBPUSDT)
            'APTUSDT',    # Aptos - Layer 1 emergente (reemplaza AUDUSDT)
            
            # Criptomonedas principales - Excelentes para rupturas
            'BTCUSDT',    # Bitcoin - Líder del mercado crypto
            'ETHUSDT',    # Ethereum - Segunda crypto más grande
            'BNBUSDT',    # Binance Coin - Token nativo, alta volatilidad
            'SOLUSDT',    # Solana - Extrema volatilidad, ideal para rupturas
            'AVAXUSDT',   # Avalanche - Alta volatilidad, movimientos fuertes
            
            # Layer 1 blockchains - Alta volatilidad para rupturas
            'ADAUSDT',    # Cardano - Movimientos fuertes en rupturas
            'DOTUSDT',    # Polkadot - Excelente para breakouts
            'ATOMUSDT',   # Cosmos - Alta volatilidad intraday
            'NEARUSDT',   # Near Protocol - Movimientos explosivos
            'SHIBUSDT',   # Shiba Inu - Alta volatilidad (reemplaza MATICUSDT)
            
            # DeFi tokens - Extrema volatilidad
            'UNIUSDT',    # Uniswap - Líder DeFi, rupturas fuertes
            'AAVEUSDT',   # Aave - Movimientos de 10-20% diarios
            'LINKUSDT',   # Chainlink - Oracle líder, alta volatilidad
            'COMPUSDT',   # Compound - Rupturas explosivas
            
            # Altcoins de alta volatilidad
            'DOGEUSDT',   # Dogecoin - Movimientos extremos
            'XRPUSDT',    # Ripple - Rupturas significativas
            'LTCUSDT',    # Litecoin - Volatilidad clásica
            'TRXUSDT'     # Tron - Movimientos rápidos
        ]
        
        # Cache para datos históricos
        self.volume_cache = {}
        self.last_cache_update = {}
        
    def detect_breakout(self, symbol: str, session: str) -> Optional[BreakoutSignal]:
        """
        Detecta ruptura en la primera vela de la sesión
        
        Args:
            symbol: Símbolo a analizar
            session: Sesión actual ('european', 'american', 'asian')
            
        Returns:
            BreakoutSignal: Señal de ruptura o None
        """
        try:
            self.logger.info(f"Analizando ruptura para {symbol} en sesión {session}")
            
            # Obtener parámetros de la sesión
            params = self.session_params.get(session)
            if not params:
                self.logger.error(f"Parámetros no encontrados para sesión {session}")
                return None
            
            # Obtener datos de mercado
            candle_data = self._get_current_candle_data(symbol)
            if not candle_data:
                self.logger.warning(f"No se pudieron obtener datos para {symbol}")
                return None
            
            # Obtener volumen promedio histórico
            avg_volume = self._get_average_volume(symbol)
            if avg_volume is None:
                self.logger.warning(f"No se pudo obtener volumen promedio para {symbol}")
                return None
            
            # Calcular ratio de volumen
            current_volume = candle_data.get('volume', 0)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            # Verificar condiciones básicas
            if not self._validate_basic_conditions(candle_data, params, volume_ratio):
                return self._create_no_signal(symbol, session, candle_data, volume_ratio)
            
            # Detectar tipo de ruptura
            breakout_type = self._detect_breakout_type(candle_data, params)
            if breakout_type == 'no_signal':
                return self._create_no_signal(symbol, session, candle_data, volume_ratio)
            
            # Calcular precios de entrada, stop loss y take profit
            entry_price = candle_data['close']
            stop_loss, take_profit = self._calculate_exit_levels(
                entry_price, breakout_type, params
            )
            
            # Calcular confianza de la señal
            confidence = self._calculate_signal_confidence(
                candle_data, volume_ratio, params
            )
            
            # Crear señal de ruptura
            signal = BreakoutSignal(
                timestamp=datetime.now(),
                symbol=symbol,
                session=session,
                signal_type=breakout_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                volume_ratio=volume_ratio,
                confidence=confidence,
                candle_data=candle_data
            )
            
            self.logger.info(f"Señal detectada: {breakout_type} para {symbol} con confianza {confidence:.2f}")
            return signal
            
        except Exception as e:
            self.logger.error(f"Error detectando ruptura para {symbol}: {e}")
            return None
    
    def _get_current_candle_data(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Obtiene datos de la vela actual (últimos 5 minutos) desde Binance
        
        Args:
            symbol: Símbolo a consultar (formato Binance: EURUSDT, GBPUSDT, etc.)
            
        Returns:
            Dict: Datos OHLCV de la vela actual
        """
        try:
            # Obtener datos históricos de Binance (últimas 50 velas de 5 minutos)
            data = self.binance_provider.get_historical_data(symbol, '5m', 50)
            
            if data is None or data.empty:
                return None
            
            # Obtener la última vela completa
            last_candle = data.iloc[-1]
            
            candle_data = {
                'open': float(last_candle['open']),
                'high': float(last_candle['high']),
                'low': float(last_candle['low']),
                'close': float(last_candle['close']),
                'volume': float(last_candle['volume']),
                'timestamp': last_candle.name
            }
            
            # Calcular métricas adicionales
            candle_data['body_size'] = abs(candle_data['close'] - candle_data['open'])
            candle_data['upper_wick'] = candle_data['high'] - max(candle_data['open'], candle_data['close'])
            candle_data['lower_wick'] = min(candle_data['open'], candle_data['close']) - candle_data['low']
            candle_data['total_range'] = candle_data['high'] - candle_data['low']
            candle_data['body_ratio'] = candle_data['body_size'] / candle_data['total_range'] if candle_data['total_range'] > 0 else 0
            
            return candle_data
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos de vela para {symbol}: {e}")
            return None
    
    def _get_average_volume(self, symbol: str) -> Optional[float]:
        """
        Obtiene el volumen promedio histórico para el símbolo desde Binance
        
        Args:
            symbol: Símbolo a consultar (formato Binance)
            
        Returns:
            float: Volumen promedio o None
        """
        try:
            # Verificar cache
            now = datetime.now()
            if (symbol in self.volume_cache and 
                symbol in self.last_cache_update and
                (now - self.last_cache_update[symbol]).seconds < 3600):  # Cache por 1 hora
                return self.volume_cache[symbol]
            
            # Obtener datos históricos de Binance (últimas 500 velas de 5 minutos ≈ 2 días)
            data = self.binance_provider.get_historical_data(symbol, '5m', 500)
            
            if data is None or data.empty or 'volume' not in data.columns:
                return None
            
            # Calcular volumen promedio
            avg_volume = data['volume'].mean()
            
            # Actualizar cache
            self.volume_cache[symbol] = float(avg_volume)
            self.last_cache_update[symbol] = now
            
            return float(avg_volume)
            
        except Exception as e:
            self.logger.error(f"Error obteniendo volumen promedio para {symbol}: {e}")
            return None
    
    def _validate_basic_conditions(self, candle_data: Dict, params: Dict, volume_ratio: float) -> bool:
        """
        Valida condiciones básicas para una señal válida
        
        Args:
            candle_data: Datos de la vela
            params: Parámetros de la sesión
            volume_ratio: Ratio de volumen actual vs promedio
            
        Returns:
            bool: True si las condiciones básicas se cumplen
        """
        try:
            # Verificar volumen mínimo
            if volume_ratio < params['min_volume_ratio']:
                self.logger.debug(f"Volumen insuficiente: {volume_ratio:.2f} < {params['min_volume_ratio']}")
                return False
            
            # Verificar movimiento mínimo de precio
            price_move_pct = candle_data['body_size'] / candle_data['open']
            if price_move_pct < params['min_price_move_pct']:
                self.logger.debug(f"Movimiento de precio insuficiente: {price_move_pct:.4f} < {params['min_price_move_pct']}")
                return False
            
            # Verificar que la vela tenga cuerpo significativo
            if candle_data['body_ratio'] < 0.3:  # Al menos 30% del rango debe ser cuerpo
                self.logger.debug(f"Cuerpo de vela insuficiente: {candle_data['body_ratio']:.2f}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validando condiciones básicas: {e}")
            return False
    
    def _detect_breakout_type(self, candle_data: Dict, params: Dict) -> str:
        """
        Detecta el tipo de ruptura basado en la vela
        
        Args:
            candle_data: Datos de la vela
            params: Parámetros de la sesión
            
        Returns:
            str: Tipo de ruptura ('bullish_breakout', 'bearish_breakout', 'no_signal')
        """
        try:
            open_price = candle_data['open']
            close_price = candle_data['close']
            high_price = candle_data['high']
            low_price = candle_data['low']
            
            # Calcular fuerza de la ruptura
            body_size = abs(close_price - open_price)
            total_range = high_price - low_price
            
            # Ruptura alcista: vela verde fuerte con cierre cerca del máximo
            if close_price > open_price:
                upper_wick_ratio = (high_price - close_price) / total_range if total_range > 0 else 0
                body_strength = body_size / open_price
                
                # Condiciones para ruptura alcista
                if (body_strength >= params['min_price_move_pct'] and 
                    upper_wick_ratio < 0.3 and  # Mecha superior pequeña
                    candle_data['body_ratio'] > 0.5):  # Cuerpo dominante
                    return 'bullish_breakout'
            
            # Ruptura bajista: vela roja fuerte con cierre cerca del mínimo
            elif close_price < open_price:
                lower_wick_ratio = (close_price - low_price) / total_range if total_range > 0 else 0
                body_strength = body_size / open_price
                
                # Condiciones para ruptura bajista
                if (body_strength >= params['min_price_move_pct'] and 
                    lower_wick_ratio < 0.3 and  # Mecha inferior pequeña
                    candle_data['body_ratio'] > 0.5):  # Cuerpo dominante
                    return 'bearish_breakout'
            
            return 'no_signal'
            
        except Exception as e:
            self.logger.error(f"Error detectando tipo de ruptura: {e}")
            return 'no_signal'
    
    def _calculate_exit_levels(self, entry_price: float, breakout_type: str, params: Dict) -> Tuple[float, float]:
        """
        Calcula niveles de stop loss y take profit
        
        Args:
            entry_price: Precio de entrada
            breakout_type: Tipo de ruptura
            params: Parámetros de la sesión
            
        Returns:
            Tuple[float, float]: (stop_loss, take_profit)
        """
        try:
            if breakout_type == 'bullish_breakout':
                stop_loss = entry_price * (1 - params['stop_loss_pct'])
                take_profit = entry_price * (1 + params['take_profit_pct'])
            elif breakout_type == 'bearish_breakout':
                stop_loss = entry_price * (1 + params['stop_loss_pct'])
                take_profit = entry_price * (1 - params['take_profit_pct'])
            else:
                stop_loss = entry_price
                take_profit = entry_price
            
            return round(stop_loss, 5), round(take_profit, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculando niveles de salida: {e}")
            return entry_price, entry_price
    
    def _calculate_signal_confidence(self, candle_data: Dict, volume_ratio: float, params: Dict) -> float:
        """
        Calcula la confianza de la señal basada en múltiples factores
        
        Args:
            candle_data: Datos de la vela
            volume_ratio: Ratio de volumen
            params: Parámetros de la sesión
            
        Returns:
            float: Confianza entre 0 y 1
        """
        try:
            confidence_factors = []
            
            # Factor de volumen (0-0.3)
            volume_score = min(volume_ratio / (params['min_volume_ratio'] * 2), 1.0) * 0.3
            confidence_factors.append(volume_score)
            
            # Factor de cuerpo de vela (0-0.25)
            body_score = min(candle_data['body_ratio'] / 0.8, 1.0) * 0.25
            confidence_factors.append(body_score)
            
            # Factor de movimiento de precio (0-0.25)
            price_move = candle_data['body_size'] / candle_data['open']
            price_score = min(price_move / (params['min_price_move_pct'] * 3), 1.0) * 0.25
            confidence_factors.append(price_score)
            
            # Factor de mechas (0-0.2)
            total_wick = candle_data['upper_wick'] + candle_data['lower_wick']
            wick_ratio = total_wick / candle_data['total_range'] if candle_data['total_range'] > 0 else 1
            wick_score = (1 - min(wick_ratio, 1.0)) * 0.2  # Menos mechas = mayor confianza
            confidence_factors.append(wick_score)
            
            # Confianza total
            total_confidence = sum(confidence_factors)
            
            return round(min(total_confidence, 1.0), 3)
            
        except Exception as e:
            self.logger.error(f"Error calculando confianza: {e}")
            return 0.0
    
    def _create_no_signal(self, symbol: str, session: str, candle_data: Dict, volume_ratio: float) -> BreakoutSignal:
        """
        Crea una señal de 'no_signal' para tracking
        
        Args:
            symbol: Símbolo
            session: Sesión
            candle_data: Datos de la vela
            volume_ratio: Ratio de volumen
            
        Returns:
            BreakoutSignal: Señal sin acción
        """
        return BreakoutSignal(
            timestamp=datetime.now(),
            symbol=symbol,
            session=session,
            signal_type='no_signal',
            entry_price=candle_data.get('close', 0),
            stop_loss=0,
            take_profit=0,
            volume_ratio=volume_ratio,
            confidence=0.0,
            candle_data=candle_data
        )
    
    def scan_all_symbols(self, session: str) -> List[BreakoutSignal]:
        """
        Escanea todos los símbolos para detectar rupturas
        
        Args:
            session: Sesión actual
            
        Returns:
            List[BreakoutSignal]: Lista de señales detectadas
        """
        signals = []
        
        self.logger.info(f"Escaneando {len(self.trading_symbols)} símbolos para sesión {session}")
        
        for symbol in self.trading_symbols:
            try:
                signal = self.detect_breakout(symbol, session)
                if signal:
                    signals.append(signal)
                    
                # Pequeña pausa para evitar rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error escaneando {symbol}: {e}")
                continue
        
        # Filtrar solo señales válidas
        valid_signals = [s for s in signals if s.signal_type != 'no_signal']
        
        self.logger.info(f"Encontradas {len(valid_signals)} señales válidas de {len(signals)} símbolos escaneados")
        
        return signals
    
    def get_session_parameters(self, session: str) -> Optional[Dict]:
        """
        Obtiene los parámetros de una sesión específica
        
        Args:
            session: Nombre de la sesión
            
        Returns:
            Dict: Parámetros de la sesión o None
        """
        return self.session_params.get(session)


if __name__ == "__main__":
    # Configurar logging para pruebas
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Crear detector
    detector = FirstCandleBreakoutDetector()
    
    print("=== SICAR First Candle Breakout - Prueba ===")
    print()
    
    # Detectar sesión actual
    session_detector = SessionDetector()
    current_session = session_detector.get_current_session()
    
    if current_session:
        print(f"Sesión actual detectada: {current_session}")
        print("Escaneando símbolos para rupturas...")
        
        # Escanear todos los símbolos
        signals = detector.scan_all_symbols(current_session)
        
        print(f"\nResultados del escaneo:")
        print(f"Total de símbolos analizados: {len(signals)}")
        
        valid_signals = [s for s in signals if s.signal_type != 'no_signal']
        print(f"Señales válidas encontradas: {len(valid_signals)}")
        
        # Mostrar señales válidas
        for signal in valid_signals:
            print(f"\n🚨 SEÑAL DETECTADA:")
            print(f"  Símbolo: {signal.symbol}")
            print(f"  Tipo: {signal.signal_type}")
            print(f"  Precio entrada: {signal.entry_price:.5f}")
            print(f"  Stop Loss: {signal.stop_loss:.5f}")
            print(f"  Take Profit: {signal.take_profit:.5f}")
            print(f"  Confianza: {signal.confidence:.1%}")
            print(f"  Ratio volumen: {signal.volume_ratio:.2f}x")
        
        # Mostrar resumen de señales sin acción
        no_signals = [s for s in signals if s.signal_type == 'no_signal']
        if no_signals:
            print(f"\nSímbolos sin señales válidas: {len(no_signals)}")
            for signal in no_signals[:3]:  # Mostrar solo los primeros 3
                print(f"  {signal.symbol}: Vol ratio {signal.volume_ratio:.2f}x")
    
    else:
        print("No hay sesión activa en este momento.")
        print("Probando detección con sesión europea...")
        
        # Probar con un símbolo específico
        test_signal = detector.detect_breakout('EURUSD=X', 'european')
        if test_signal:
            print(f"\nPrueba con EURUSD:")
            print(f"  Tipo de señal: {test_signal.signal_type}")
            print(f"  Confianza: {test_signal.confidence:.1%}")
            print(f"  Ratio volumen: {test_signal.volume_ratio:.2f}x")
        else:
            print("No se pudo obtener datos de prueba.")