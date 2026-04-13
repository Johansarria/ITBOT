import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
from market_analyzer import MarketConditionAnalyzer, TechnicalAnalyzer, MarketSignal
from portfolio_manager import PortfolioManager, AssetClass

logger = logging.getLogger(__name__)

class SignalType(Enum):
    """Tipos de señales de trading"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    WEAK_BUY = "WEAK_BUY"
    HOLD = "HOLD"
    WEAK_SELL = "WEAK_SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

class StrategyType(Enum):
    """Tipos de estrategias basadas en análisis previo"""
    MOMENTUM = "momentum"  # Para crypto de alto rendimiento
    MEAN_REVERSION = "mean_reversion"  # Para forex estable
    TREND_FOLLOWING = "trend_following"  # Para índices
    BREAKOUT = "breakout"  # Para commodities
    PROBABILITY = "probability"  # Estrategia probabilística general
    TSMOM = "tsmom"  # Momentum de series temporales (spot)

@dataclass
class TradingSignal:
    """Señal de trading completa"""
    symbol: str
    signal_type: SignalType
    strategy_type: StrategyType
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    position_size: float
    confidence: float  # 0-100
    risk_reward_ratio: float
    expected_return: float
    max_risk: float
    reasons: List[str]
    timestamp: datetime
    expiry: Optional[datetime] = None
    
@dataclass
class StrategyConfig:
    """Configuración de estrategia específica"""
    strategy_type: StrategyType
    symbols: List[str]
    timeframe: str
    min_confidence: float = 60.0
    max_risk_per_trade: float = 0.02  # 2%
    risk_reward_ratio: float = 2.0
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    position_sizing_method: str = "fixed_risk"  # "fixed_risk", "kelly", "volatility"
    
class StrategyEngine:
    """Motor de estrategias de trading"""
    
    def __init__(self, market_analyzer: MarketConditionAnalyzer, portfolio_manager: PortfolioManager):
        self.market_analyzer = market_analyzer
        self.portfolio_manager = portfolio_manager
        self.strategy_configs = self._initialize_strategies()
        self.active_signals: Dict[str, TradingSignal] = {}
        self.signal_history: List[TradingSignal] = []
        
    def _initialize_strategies(self) -> Dict[StrategyType, StrategyConfig]:
        """Inicializa configuraciones de estrategias basadas en análisis previo"""
        return {
            # Estrategia Momentum para crypto de alto rendimiento
            StrategyType.MOMENTUM: StrategyConfig(
                strategy_type=StrategyType.MOMENTUM,
                symbols=['SOLUSDT', 'BNBUSDT', 'ADAUSDT'],
                timeframe='15m',
                min_confidence=70.0,
                max_risk_per_trade=0.025,  # 2.5% para crypto
                risk_reward_ratio=2.5,
                stop_loss_pct=0.03,
                take_profit_pct=0.075
            ),
            
            # Estrategia Mean Reversion para crypto estable
            StrategyType.MEAN_REVERSION: StrategyConfig(
                strategy_type=StrategyType.MEAN_REVERSION,
                symbols=['ETHUSDT', 'BTCUSDT'],
                timeframe='30m',
                min_confidence=65.0,
                max_risk_per_trade=0.02,
                risk_reward_ratio=2.0,
                stop_loss_pct=0.025,
                take_profit_pct=0.05
            ),
            
            # Estrategia Trend Following para índices
            StrategyType.TREND_FOLLOWING: StrategyConfig(
                strategy_type=StrategyType.TREND_FOLLOWING,
                symbols=['NAS100'],
                timeframe='1h',
                min_confidence=60.0,
                max_risk_per_trade=0.015,  # Más conservador
                risk_reward_ratio=3.0,
                stop_loss_pct=0.015,
                take_profit_pct=0.045
            ),
            
            # Estrategia Breakout para forex
            StrategyType.BREAKOUT: StrategyConfig(
                strategy_type=StrategyType.BREAKOUT,
                symbols=['AUDCAD'],
                timeframe='4h',
                min_confidence=65.0,
                max_risk_per_trade=0.01,  # Muy conservador
                risk_reward_ratio=2.5,
                stop_loss_pct=0.01,
                take_profit_pct=0.025
            ),
            
            # Estrategia Probability para commodities
            StrategyType.PROBABILITY: StrategyConfig(
                strategy_type=StrategyType.PROBABILITY,
                symbols=['XAUUSD'],
                timeframe='2h',
                min_confidence=70.0,
                max_risk_per_trade=0.015,
                risk_reward_ratio=2.0,
                stop_loss_pct=0.02,
                take_profit_pct=0.04
            ),
            
            # Estrategia TSMOM para crypto spot
            StrategyType.TSMOM: StrategyConfig(
                strategy_type=StrategyType.TSMOM,
                symbols=['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT'],
                timeframe='4h',
                min_confidence=65.0,
                max_risk_per_trade=0.015,
                risk_reward_ratio=2.0,
                stop_loss_pct=0.03,
                take_profit_pct=0.06
            )
        }
        
    def generate_signals(self) -> List[TradingSignal]:
        """Genera señales para todos los símbolos configurados"""
        new_signals = []
        
        for strategy_type, config in self.strategy_configs.items():
            for symbol in config.symbols:
                signal = self._generate_signal_for_symbol(symbol, strategy_type, config)
                if signal and signal.confidence >= config.min_confidence:
                    new_signals.append(signal)
                    
        return new_signals
        
    def _generate_signal_for_symbol(self, symbol: str, strategy_type: StrategyType, 
                                   config: StrategyConfig) -> Optional[TradingSignal]:
        """Genera señal específica para un símbolo usando estrategia definida"""
        # Obtener análisis de mercado
        market_signal = self.market_analyzer.analyze_market_conditions(symbol)
        if not market_signal:
            return None
            
        # Aplicar lógica específica de estrategia
        if strategy_type == StrategyType.MOMENTUM:
            return self._momentum_strategy(symbol, market_signal, config)
        elif strategy_type == StrategyType.MEAN_REVERSION:
            return self._mean_reversion_strategy(symbol, market_signal, config)
        elif strategy_type == StrategyType.TREND_FOLLOWING:
            return self._trend_following_strategy(symbol, market_signal, config)
        elif strategy_type == StrategyType.BREAKOUT:
            return self._breakout_strategy(symbol, market_signal, config)
        elif strategy_type == StrategyType.PROBABILITY:
            return self._probability_strategy(symbol, market_signal, config)
        elif strategy_type == StrategyType.TSMOM:
            return self._tsmom_strategy(symbol, market_signal, config)
            
        return None
        
    def _momentum_strategy(self, symbol: str, market_signal: MarketSignal, 
                          config: StrategyConfig) -> Optional[TradingSignal]:
        """Estrategia de momentum para crypto de alto rendimiento"""
        indicators = market_signal.indicators
        reasons = []
        confidence_factors = []
        
        # Condiciones de entrada para momentum
        entry_conditions = {
            'rsi_momentum': False,
            'macd_bullish': False,
            'price_above_ma': False,
            'volume_confirmation': False
        }
        
        # RSI en rango de momentum (40-70)
        if indicators.rsi and 40 <= indicators.rsi <= 70:
            entry_conditions['rsi_momentum'] = True
            confidence_factors.append(60)
            reasons.append(f"RSI en zona de momentum ({indicators.rsi:.1f})")
            
        # MACD alcista
        if (indicators.macd and indicators.macd_signal and 
            indicators.macd > indicators.macd_signal and indicators.macd > 0):
            entry_conditions['macd_bullish'] = True
            confidence_factors.append(70)
            reasons.append("MACD en territorio alcista")
            
        # Precio por encima de medias móviles
        current_price = self.portfolio_manager.current_prices.get(symbol)
        if (current_price and indicators.sma_20 and indicators.sma_50 and
            current_price > indicators.sma_20 > indicators.sma_50):
            entry_conditions['price_above_ma'] = True
            confidence_factors.append(65)
            reasons.append("Precio por encima de medias móviles")
            
        # Confirmar con volumen (simplificado)
        if indicators.volume_sma:
            entry_conditions['volume_confirmation'] = True
            confidence_factors.append(50)
            reasons.append("Volumen confirmatorio")
            
        # Determinar señal
        conditions_met = sum(entry_conditions.values())
        
        if conditions_met >= 3:  # Al menos 3 condiciones
            signal_type = SignalType.STRONG_BUY if conditions_met == 4 else SignalType.BUY
            confidence = np.mean(confidence_factors) if confidence_factors else 50
            
            return self._create_trading_signal(
                symbol, signal_type, StrategyType.MOMENTUM, current_price or 0,
                config, confidence, reasons
            )
            
        return None
        
    def _mean_reversion_strategy(self, symbol: str, market_signal: MarketSignal,
                               config: StrategyConfig) -> Optional[TradingSignal]:
        """Estrategia de reversión a la media para crypto estable"""
        indicators = market_signal.indicators
        reasons = []
        confidence_factors = []
        
        current_price = self.portfolio_manager.current_prices.get(symbol)
        if not current_price:
            return None
            
        # Condiciones de reversión
        entry_conditions = {
            'oversold_rsi': False,
            'bb_lower_touch': False,
            'price_below_ma': False,
            'macd_divergence': False
        }
        
        # RSI sobreventa
        if indicators.rsi and indicators.rsi <= 35:
            entry_conditions['oversold_rsi'] = True
            confidence_factors.append(80)
            reasons.append(f"RSI sobreventa ({indicators.rsi:.1f})")
            
        # Precio cerca de banda inferior de Bollinger
        if (indicators.bb_lower and indicators.bb_middle and
            current_price <= indicators.bb_lower * 1.01):  # 1% tolerancia
            entry_conditions['bb_lower_touch'] = True
            confidence_factors.append(75)
            reasons.append("Precio en banda inferior de Bollinger")
            
        # Precio por debajo de media pero cerca
        if (indicators.sma_20 and 
            current_price < indicators.sma_20 and
            current_price > indicators.sma_20 * 0.97):  # Dentro del 3%
            entry_conditions['price_below_ma'] = True
            confidence_factors.append(60)
            reasons.append("Precio cerca de SMA20 por debajo")
            
        # MACD mostrando posible reversión
        if (indicators.macd and indicators.macd_signal and
            indicators.macd < indicators.macd_signal and
            indicators.macd_histogram and indicators.macd_histogram > -0.001):  # Convergencia
            entry_conditions['macd_divergence'] = True
            confidence_factors.append(65)
            reasons.append("MACD mostrando convergencia")
            
        conditions_met = sum(entry_conditions.values())
        
        if conditions_met >= 2:  # Al menos 2 condiciones para mean reversion
            signal_type = SignalType.BUY if conditions_met >= 3 else SignalType.WEAK_BUY
            confidence = np.mean(confidence_factors) if confidence_factors else 50
            
            return self._create_trading_signal(
                symbol, signal_type, StrategyType.MEAN_REVERSION, current_price,
                config, confidence, reasons
            )
            
        return None
        
    def _trend_following_strategy(self, symbol: str, market_signal: MarketSignal,
                                config: StrategyConfig) -> Optional[TradingSignal]:
        """Estrategia de seguimiento de tendencia para índices"""
        indicators = market_signal.indicators
        reasons = []
        confidence_factors = []
        
        current_price = self.portfolio_manager.current_prices.get(symbol)
        if not current_price:
            return None
            
        # Condiciones de tendencia alcista
        trend_conditions = {
            'ma_alignment': False,
            'price_momentum': False,
            'macd_trend': False,
            'rsi_strength': False
        }
        
        # Alineación de medias móviles
        if (indicators.sma_20 and indicators.sma_50 and indicators.ema_12 and
            indicators.sma_20 > indicators.sma_50 and
            indicators.ema_12 > indicators.sma_20):
            trend_conditions['ma_alignment'] = True
            confidence_factors.append(80)
            reasons.append("Medias móviles alineadas alcistamente")
            
        # Momentum de precio
        if (indicators.sma_20 and current_price > indicators.sma_20 * 1.005):  # 0.5% por encima
            trend_conditions['price_momentum'] = True
            confidence_factors.append(70)
            reasons.append("Precio con momentum alcista")
            
        # MACD en tendencia alcista
        if (indicators.macd and indicators.macd_signal and
            indicators.macd > indicators.macd_signal and
            indicators.macd > 0 and indicators.macd_signal > 0):
            trend_conditions['macd_trend'] = True
            confidence_factors.append(75)
            reasons.append("MACD confirmando tendencia alcista")
            
        # RSI mostrando fuerza pero no sobrecompra
        if indicators.rsi and 50 <= indicators.rsi <= 75:
            trend_conditions['rsi_strength'] = True
            confidence_factors.append(65)
            reasons.append(f"RSI mostrando fuerza ({indicators.rsi:.1f})")
            
        conditions_met = sum(trend_conditions.values())
        
        if conditions_met >= 3:  # Necesita confirmación fuerte para trend following
            signal_type = SignalType.STRONG_BUY if conditions_met == 4 else SignalType.BUY
            confidence = np.mean(confidence_factors) if confidence_factors else 50
            
            return self._create_trading_signal(
                symbol, signal_type, StrategyType.TREND_FOLLOWING, current_price,
                config, confidence, reasons
            )
            
        return None
        
    def _breakout_strategy(self, symbol: str, market_signal: MarketSignal,
                         config: StrategyConfig) -> Optional[TradingSignal]:
        """Estrategia de breakout para forex"""
        indicators = market_signal.indicators
        reasons = []
        confidence_factors = []
        
        current_price = self.portfolio_manager.current_prices.get(symbol)
        if not current_price:
            return None
            
        # Condiciones de breakout
        breakout_conditions = {
            'bb_breakout': False,
            'volume_spike': False,
            'rsi_momentum': False,
            'ma_cross': False
        }
        
        # Breakout de Bollinger Bands
        if (indicators.bb_upper and indicators.bb_width and
            current_price > indicators.bb_upper and
            indicators.bb_width < 5):  # Bandas estrechas antes del breakout
            breakout_conditions['bb_breakout'] = True
            confidence_factors.append(85)
            reasons.append("Breakout de banda superior de Bollinger")
            
        # Spike de volumen (simplificado)
        if indicators.volume_sma:
            breakout_conditions['volume_spike'] = True
            confidence_factors.append(60)
            reasons.append("Confirmación de volumen")
            
        # RSI con momentum pero no extremo
        if indicators.rsi and 55 <= indicators.rsi <= 80:
            breakout_conditions['rsi_momentum'] = True
            confidence_factors.append(70)
            reasons.append(f"RSI con momentum ({indicators.rsi:.1f})")
            
        # Cruce de medias móviles
        if (indicators.ema_12 and indicators.ema_26 and
            indicators.ema_12 > indicators.ema_26):
            breakout_conditions['ma_cross'] = True
            confidence_factors.append(65)
            reasons.append("Cruce alcista de EMAs")
            
        conditions_met = sum(breakout_conditions.values())
        
        if conditions_met >= 2 and breakout_conditions['bb_breakout']:  # Breakout es crítico
            signal_type = SignalType.BUY if conditions_met >= 3 else SignalType.WEAK_BUY
            confidence = np.mean(confidence_factors) if confidence_factors else 50
            
            return self._create_trading_signal(
                symbol, signal_type, StrategyType.BREAKOUT, current_price,
                config, confidence, reasons
            )
            
        return None
        
    def _probability_strategy(self, symbol: str, market_signal: MarketSignal,
                            config: StrategyConfig) -> Optional[TradingSignal]:
        """Estrategia probabilística para commodities (oro)"""
        indicators = market_signal.indicators
        reasons = []
        confidence_factors = []
        
        current_price = self.portfolio_manager.current_prices.get(symbol)
        if not current_price:
            return None
            
        # Sistema probabilístico basado en múltiples factores
        probability_score = 0
        max_score = 0
        
        # Factor 1: RSI (peso 25%)
        if indicators.rsi:
            if indicators.rsi <= 30:
                probability_score += 25
                reasons.append(f"RSI sobreventa fuerte ({indicators.rsi:.1f})")
            elif indicators.rsi <= 40:
                probability_score += 15
                reasons.append(f"RSI sobreventa moderada ({indicators.rsi:.1f})")
            elif 45 <= indicators.rsi <= 55:
                probability_score += 10
                reasons.append(f"RSI neutral ({indicators.rsi:.1f})")
            max_score += 25
            
        # Factor 2: MACD (peso 20%)
        if indicators.macd and indicators.macd_signal:
            if indicators.macd > indicators.macd_signal:
                probability_score += 20
                reasons.append("MACD alcista")
            elif indicators.macd > indicators.macd_signal * 0.95:  # Cerca del cruce
                probability_score += 10
                reasons.append("MACD cerca de cruce alcista")
            max_score += 20
            
        # Factor 3: Bollinger Bands (peso 20%)
        if indicators.bb_lower and indicators.bb_middle:
            bb_position = (current_price - indicators.bb_lower) / (indicators.bb_middle - indicators.bb_lower)
            if bb_position <= 0.2:
                probability_score += 20
                reasons.append("Precio en zona baja de Bollinger")
            elif bb_position <= 0.4:
                probability_score += 10
                reasons.append("Precio en zona medio-baja de Bollinger")
            max_score += 20
            
        # Factor 4: Tendencia (peso 20%)
        if indicators.sma_20 and indicators.sma_50:
            if indicators.sma_20 > indicators.sma_50:
                probability_score += 20
                reasons.append("Tendencia de mediano plazo alcista")
            elif indicators.sma_20 > indicators.sma_50 * 0.995:  # Muy cerca
                probability_score += 10
                reasons.append("Tendencia neutral a alcista")
            max_score += 20
            
        # Factor 5: Volatilidad (peso 15%)
        if indicators.bb_width:
            if indicators.bb_width > 3:  # Alta volatilidad
                probability_score += 15
                reasons.append("Alta volatilidad favorable")
            elif indicators.bb_width > 2:
                probability_score += 8
                reasons.append("Volatilidad moderada")
            max_score += 15
            
        # Calcular probabilidad final
        if max_score > 0:
            final_probability = (probability_score / max_score) * 100
            confidence_factors.append(final_probability)
            
            # Determinar señal basada en probabilidad
            if final_probability >= 75:
                signal_type = SignalType.STRONG_BUY
            elif final_probability >= 60:
                signal_type = SignalType.BUY
            elif final_probability >= 45:
                signal_type = SignalType.WEAK_BUY
            else:
                return None  # Probabilidad muy baja
                
            return self._create_trading_signal(
                symbol, signal_type, StrategyType.PROBABILITY, current_price,
                config, final_probability, reasons
            )
            
        return None
        
    def _tsmom_strategy(self, symbol: str, market_signal: MarketSignal,
                        config: StrategyConfig) -> Optional[TradingSignal]:
        """Estrategia TSMOM (Time Series Momentum) para crypto spot.
        Se apoya en alineación de medias, momentum de EMAs y confirmaciones básicas.
        """
        indicators = market_signal.indicators
        reasons: List[str] = []
        confidence_factors: List[float] = []

        current_price = self.portfolio_manager.current_prices.get(symbol)
        if not current_price:
            return None

        # Condiciones TSMOM
        conditions = {
            'ma_alignment': False,
            'ema_momentum': False,
            'price_above_ma': False,
            'macd_hist_positive': False,
            'rsi_above_55': False,
        }

        # Alineación de medias (tendencia base)
        if (indicators.sma_20 and indicators.sma_50 and indicators.ema_12 and indicators.ema_26 and
            indicators.sma_20 > indicators.sma_50 and indicators.ema_12 > indicators.ema_26):
            conditions['ma_alignment'] = True
            reasons.append("Medias alineadas (SMA20>SMA50 y EMA12>EMA26)")
            confidence_factors.append(80)

        # Momentum de EMAs: EMA12 por encima de SMA20 (aceleración)
        if (indicators.ema_12 and indicators.sma_20 and indicators.ema_12 > indicators.sma_20):
            conditions['ema_momentum'] = True
            reasons.append("EMA12 > SMA20 (aceleración de corto plazo)")
            confidence_factors.append(70)

        # Precio por encima de la media de corto plazo
        if (indicators.sma_20 and current_price > indicators.sma_20 * 1.003):  # +0.3%
            conditions['price_above_ma'] = True
            reasons.append("Precio > SMA20 (sesgo alcista)")
            confidence_factors.append(60)

        # MACD histograma positivo (inercia alcista)
        if (getattr(indicators, 'macd_histogram', None) is not None and indicators.macd_histogram is not None and
            indicators.macd_histogram > 0):
            conditions['macd_hist_positive'] = True
            reasons.append("MACD histograma positivo")
            confidence_factors.append(65)

        # RSI con fuerza pero sin sobrecompra
        if indicators.rsi and 55 <= indicators.rsi <= 75:
            conditions['rsi_above_55'] = True
            reasons.append(f"RSI fuerte ({indicators.rsi:.1f})")
            confidence_factors.append(60)

        conditions_met = sum(1 for v in conditions.values() if v)
        if conditions_met >= 3:
            signal_type = SignalType.STRONG_BUY if conditions_met >= 4 else SignalType.BUY
            confidence = float(np.mean(confidence_factors)) if confidence_factors else 60.0
            return self._create_trading_signal(
                symbol, signal_type, StrategyType.TSMOM, current_price,
                config, confidence, reasons
            )

        return None
        
    def _create_trading_signal(self, symbol: str, signal_type: SignalType, 
                             strategy_type: StrategyType, entry_price: float,
                             config: StrategyConfig, confidence: float, 
                             reasons: List[str]) -> TradingSignal:
        """Crea señal de trading completa"""
        # Calcular stop loss y take profit
        stop_loss = entry_price * (1 - config.stop_loss_pct)
        take_profit = entry_price * (1 + config.take_profit_pct)
        
        # Calcular tamaño de posición
        position_size, position_value = self.portfolio_manager.calculate_position_size_with_risk(
            symbol, confidence / 100, config.stop_loss_pct
        )
        
        # Calcular métricas de riesgo
        risk_per_unit = entry_price - stop_loss
        max_risk = risk_per_unit * position_size
        expected_return = (take_profit - entry_price) * position_size
        risk_reward_ratio = expected_return / max_risk if max_risk > 0 else 0
        
        # Calcular expiración de señal
        expiry_hours = {
            StrategyType.MOMENTUM: 4,
            StrategyType.MEAN_REVERSION: 8,
            StrategyType.TREND_FOLLOWING: 24,
            StrategyType.BREAKOUT: 6,
            StrategyType.PROBABILITY: 12,
            StrategyType.TSMOM: 12,
        }
        
        expiry = datetime.now() + timedelta(hours=expiry_hours.get(strategy_type, 8))
        
        return TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            strategy_type=strategy_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            confidence=confidence,
            risk_reward_ratio=risk_reward_ratio,
            expected_return=expected_return,
            max_risk=max_risk,
            reasons=reasons,
            timestamp=datetime.now(),
            expiry=expiry
        )
        
    def get_active_signals(self, symbol: str = None) -> List[TradingSignal]:
        """Obtiene señales activas"""
        now = datetime.now()
        active = []
        
        for signal in self.active_signals.values():
            if signal.expiry and signal.expiry < now:
                continue  # Señal expirada
                
            if symbol is None or signal.symbol == symbol:
                active.append(signal)
                
        return active
        
    def update_signal_status(self, signal_id: str, executed: bool = False):
        """Actualiza estado de una señal"""
        if signal_id in self.active_signals:
            signal = self.active_signals[signal_id]
            
            if executed:
                # Mover a historial
                self.signal_history.append(signal)
                del self.active_signals[signal_id]
                logger.info(f"Señal ejecutada: {signal.symbol} {signal.signal_type.value}")
                
    def get_signals_summary(self) -> Dict:
        """Obtiene resumen de señales"""
        active_signals = list(self.active_signals.values())
        
        summary = {
            'timestamp': datetime.now(),
            'active_signals_count': len(active_signals),
            'signals_by_type': {},
            'signals_by_strategy': {},
            'average_confidence': 0,
            'total_expected_return': 0,
            'total_max_risk': 0,
            'signals': []
        }
        
        if active_signals:
            # Agrupar por tipo
            for signal in active_signals:
                signal_type = signal.signal_type.value
                strategy_type = signal.strategy_type.value
                
                summary['signals_by_type'][signal_type] = summary['signals_by_type'].get(signal_type, 0) + 1
                summary['signals_by_strategy'][strategy_type] = summary['signals_by_strategy'].get(strategy_type, 0) + 1
                
                summary['signals'].append({
                    'symbol': signal.symbol,
                    'signal_type': signal_type,
                    'strategy_type': strategy_type,
                    'confidence': signal.confidence,
                    'expected_return': signal.expected_return,
                    'max_risk': signal.max_risk,
                    'risk_reward_ratio': signal.risk_reward_ratio,
                    'reasons': signal.reasons[:2]  # Solo las 2 principales
                })
                
            summary['average_confidence'] = np.mean([s.confidence for s in active_signals])
            summary['total_expected_return'] = sum(s.expected_return for s in active_signals)
            summary['total_max_risk'] = sum(s.max_risk for s in active_signals)
            
        return summary

if __name__ == "__main__":
    # Ejemplo de uso
    from market_analyzer import TechnicalAnalyzer, MarketConditionAnalyzer
    from portfolio_manager import PortfolioManager
    
    # Inicializar componentes
    technical_analyzer = TechnicalAnalyzer()
    market_analyzer = MarketConditionAnalyzer(technical_analyzer)
    portfolio_manager = PortfolioManager()
    strategy_engine = StrategyEngine(market_analyzer, portfolio_manager)
    
    # Simular datos
    symbols = ['BNBUSDT', 'ETHUSDT', 'NAS100', 'AUDCAD', 'XAUUSD']
    
    for symbol in symbols:
        # Simular precios y datos técnicos
        base_price = {'BNBUSDT': 300, 'ETHUSDT': 2500, 'NAS100': 15000, 'AUDCAD': 0.91, 'XAUUSD': 1950}[symbol]
        
        for i in range(50):
            price = base_price * (1 + np.random.normal(0, 0.01))
            technical_analyzer.add_price_data(symbol, price, volume=1000)
            portfolio_manager.update_price(symbol, price)
            
    # Generar señales
    signals = strategy_engine.generate_signals()
    
    print(f"\n=== SEÑALES GENERADAS ({len(signals)}) ===")
    for signal in signals:
        print(f"\n{signal.symbol} - {signal.signal_type.value}")
        print(f"Estrategia: {signal.strategy_type.value}")
        print(f"Precio entrada: ${signal.entry_price:.2f}")
        print(f"Stop Loss: ${signal.stop_loss:.2f}")
        print(f"Take Profit: ${signal.take_profit:.2f}")
        print(f"Tamaño posición: {signal.position_size:.4f}")
        print(f"Confianza: {signal.confidence:.1f}%")
        print(f"R/R Ratio: {signal.risk_reward_ratio:.2f}")
        print(f"Razones: {', '.join(signal.reasons[:3])}")
        
    # Mostrar resumen
    summary = strategy_engine.get_signals_summary()
    print(f"\n=== RESUMEN DE SEÑALES ===")
    print(f"Señales activas: {summary['active_signals_count']}")
    print(f"Confianza promedio: {summary['average_confidence']:.1f}%")
    print(f"Retorno esperado total: ${summary['total_expected_return']:.2f}")
    print(f"Riesgo máximo total: ${summary['total_max_risk']:.2f}")