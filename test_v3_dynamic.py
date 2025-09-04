"""
🧪 PRUEBAS SISTEMA V3 DINÁMICO
=============================

Script de pruebas para validar el funcionamiento del sistema V3 dinámico.
Simula condiciones de mercado y verifica respuestas adaptativas.

Autor: Johan Sarria
Fecha: 1 septiembre 2025
Versión: 3.1 Testing
"""

import asyncio
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import json
import sys
import os

# Agregar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.v3_dynamic_system import V3DynamicSystem, MarketRegime
from strategies.v3_dynamic_controller import V3DynamicController

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class V3DynamicTester:
    """
    🧪 Tester para el sistema V3 dinámico
    """
    
    def __init__(self):
        self.dynamic_system = V3DynamicSystem()
        self.test_results = []
        logger.info("🧪 Tester V3 Dinámico inicializado")
    
    async def run_comprehensive_tests(self):
        """Ejecutar suite completa de pruebas"""
        
        logger.info("🚀 Iniciando pruebas comprehensivas del sistema V3 dinámico")
        
        tests = [
            ("🏪 Prueba Mercado Lateral", self.test_sideways_market),
            ("📈 Prueba Tendencia Alcista", self.test_bull_trend_market),
            ("📉 Prueba Tendencia Bajista", self.test_bear_trend_market),
            ("⚡ Prueba Alta Volatilidad", self.test_high_volatility_market),
            ("💤 Prueba Baja Volatilidad", self.test_low_volatility_market),
            ("💥 Prueba Breakout", self.test_breakout_market),
            ("📊 Prueba Consolidación", self.test_consolidation_market),
            ("🔄 Prueba Cambios Régimen", self.test_regime_changes),
            ("⚖️ Prueba Adaptación Configuración", self.test_config_adaptation),
            ("🎯 Prueba Selección Estrategias", self.test_strategy_selection)
        ]
        
        passed_tests = 0
        total_tests = len(tests)
        
        for test_name, test_function in tests:
            try:
                logger.info(f"\n{'='*50}")
                logger.info(f"Ejecutando: {test_name}")
                logger.info(f"{'='*50}")
                
                result = await test_function()
                
                if result["success"]:
                    logger.info(f"✅ {test_name}: PASÓ")
                    passed_tests += 1
                else:
                    logger.error(f"❌ {test_name}: FALLÓ - {result.get('error', 'Sin detalles')}")
                
                self.test_results.append({
                    "test_name": test_name,
                    "success": result["success"],
                    "details": result,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"💥 {test_name}: ERROR - {str(e)}")
                self.test_results.append({
                    "test_name": test_name,
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        # Reporte final
        success_rate = (passed_tests / total_tests) * 100
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🏁 REPORTE FINAL DE PRUEBAS")
        logger.info(f"{'='*60}")
        logger.info(f"✅ Pruebas pasadas: {passed_tests}/{total_tests}")
        logger.info(f"📊 Tasa de éxito: {success_rate:.1f}%")
        
        if success_rate >= 80:
            logger.info("🎉 SISTEMA APROBADO - Listo para producción")
        elif success_rate >= 60:
            logger.warning("⚠️ SISTEMA CON RESERVAS - Revisar fallos")
        else:
            logger.error("🚨 SISTEMA REPROBADO - Requiere correcciones")
        
        # Guardar resultados
        await self.save_test_results()
        
        return {
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "success_rate": success_rate,
            "approved": success_rate >= 80
        }
    
    async def test_sideways_market(self) -> Dict:
        """Probar respuesta a mercado lateral"""
        
        try:
            # Simular datos de mercado lateral
            market_data = self.generate_sideways_market_data()
            current_prices = {"BTC/USDT": 50000, "SOL/USDT": 100}
            
            # Analizar
            analysis = await self.dynamic_system.analyze_market_and_adapt(
                market_data, current_prices
            )
            
            # Verificaciones
            market_condition = analysis["market_condition"]
            
            success = True
            errors = []
            
            # Verificar régimen detectado
            if market_condition.regime not in [MarketRegime.SIDEWAYS, MarketRegime.LOW_VOLATILITY, MarketRegime.CONSOLIDATION]:
                errors.append(f"Régimen incorrecto: {market_condition.regime.value} (esperado: sideways/consolidation)")
                success = False
            
            # Verificar baja actividad de estrategias
            active_strategies = analysis["active_strategies"]
            if len(active_strategies) > 1:  # En lateral, máximo 1 estrategia
                errors.append(f"Demasiadas estrategias activas: {len(active_strategies)} (esperado: ≤1)")
                success = False
            
            # Verificar confianza baja/moderada
            if market_condition.confidence > 0.7:
                errors.append(f"Confianza muy alta para lateral: {market_condition.confidence:.2f}")
                success = False
            
            # Verificar recomendaciones conservadoras
            recommendations = analysis["recommendations"]
            if recommendations["risk_level"] not in ["very_low", "low"]:
                errors.append(f"Nivel de riesgo incorrecto: {recommendations['risk_level']}")
                success = False
            
            return {
                "success": success,
                "errors": errors,
                "regime_detected": market_condition.regime.value,
                "confidence": market_condition.confidence,
                "active_strategies": len(active_strategies),
                "risk_level": recommendations["risk_level"]
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_bull_trend_market(self) -> Dict:
        """Probar respuesta a tendencia alcista"""
        
        try:
            # Simular mercado alcista
            market_data = self.generate_bull_trend_data()
            current_prices = {"BTC/USDT": 52000, "SOL/USDT": 110}
            
            analysis = await self.dynamic_system.analyze_market_and_adapt(
                market_data, current_prices
            )
            
            market_condition = analysis["market_condition"]
            success = True
            errors = []
            
            # Verificar régimen alcista
            if market_condition.regime != MarketRegime.TRENDING_BULL:
                errors.append(f"Régimen incorrecto: {market_condition.regime.value} (esperado: trending_bull)")
                success = False
            
            # Verificar alta confianza
            if market_condition.confidence < 0.6:
                errors.append(f"Confianza baja para tendencia clara: {market_condition.confidence:.2f}")
                success = False
            
            # Verificar fuerza de tendencia
            if market_condition.trend_strength < 0.5:
                errors.append(f"Fuerza de tendencia baja: {market_condition.trend_strength:.2f}")
                success = False
            
            # Verificar estrategias apropiadas
            active_strategies = analysis["active_strategies"]
            expected_strategies = ["swing_adaptive", "hybrid_adaptive"]
            strategy_found = any(strategy in active_strategies for strategy in expected_strategies)
            
            if not strategy_found:
                errors.append(f"No se encontraron estrategias apropiadas para tendencia alcista")
                success = False
            
            return {
                "success": success,
                "errors": errors,
                "regime_detected": market_condition.regime.value,
                "confidence": market_condition.confidence,
                "trend_strength": market_condition.trend_strength,
                "strategies": active_strategies
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_bear_trend_market(self) -> Dict:
        """Probar respuesta a tendencia bajista"""
        
        try:
            market_data = self.generate_bear_trend_data()
            current_prices = {"BTC/USDT": 48000, "SOL/USDT": 95}
            
            analysis = await self.dynamic_system.analyze_market_and_adapt(
                market_data, current_prices
            )
            
            market_condition = analysis["market_condition"]
            success = True
            errors = []
            
            if market_condition.regime != MarketRegime.TRENDING_BEAR:
                errors.append(f"Régimen incorrecto: {market_condition.regime.value}")
                success = False
            
            if market_condition.confidence < 0.5:
                errors.append(f"Confianza insuficiente para tendencia bajista")
                success = False
            
            # Verificar momentum bajista
            if market_condition.momentum_score > 0.6:
                errors.append(f"Momentum score demasiado alto para bajista: {market_condition.momentum_score:.2f}")
                success = False
            
            return {
                "success": success,
                "errors": errors,
                "regime_detected": market_condition.regime.value,
                "momentum_score": market_condition.momentum_score
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_high_volatility_market(self) -> Dict:
        """Probar respuesta a alta volatilidad"""
        
        try:
            market_data = self.generate_high_volatility_data()
            current_prices = {"BTC/USDT": 51000, "SOL/USDT": 105}
            
            analysis = await self.dynamic_system.analyze_market_and_adapt(
                market_data, current_prices
            )
            
            market_condition = analysis["market_condition"]
            success = True
            errors = []
            
            # Verificar alta volatilidad detectada
            if market_condition.volatility_percentile < 0.7:
                errors.append(f"Volatilidad baja detectada: {market_condition.volatility_percentile:.2f}")
                success = False
            
            # Verificar régimen apropiado
            if market_condition.regime not in [MarketRegime.HIGH_VOLATILITY, MarketRegime.BREAKOUT]:
                errors.append(f"Régimen incorrecto para alta volatilidad: {market_condition.regime.value}")
                success = False
            
            # Verificar estrategias de scalping activadas
            active_strategies = analysis["active_strategies"]
            if "scalping_adaptive" not in active_strategies:
                errors.append("Estrategia de scalping no activada en alta volatilidad")
                success = False
            
            return {
                "success": success,
                "errors": errors,
                "volatility_percentile": market_condition.volatility_percentile,
                "regime": market_condition.regime.value,
                "strategies": active_strategies
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_low_volatility_market(self) -> Dict:
        """Probar respuesta a baja volatilidad"""
        
        try:
            market_data = self.generate_low_volatility_data()
            current_prices = {"BTC/USDT": 50100, "SOL/USDT": 100.5}
            
            analysis = await self.dynamic_system.analyze_market_and_adapt(
                market_data, current_prices
            )
            
            market_condition = analysis["market_condition"]
            success = True
            errors = []
            
            # Verificar baja volatilidad
            if market_condition.volatility_percentile > 0.3:
                errors.append(f"Volatilidad alta detectada: {market_condition.volatility_percentile:.2f}")
                success = False
            
            # Verificar pocas estrategias activas
            active_strategies = analysis["active_strategies"]
            if len(active_strategies) > 1:
                errors.append(f"Demasiadas estrategias en baja volatilidad: {len(active_strategies)}")
                success = False
            
            return {
                "success": success,
                "errors": errors,
                "volatility_percentile": market_condition.volatility_percentile,
                "active_strategies_count": len(active_strategies)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_breakout_market(self) -> Dict:
        """Probar respuesta a breakout"""
        
        try:
            market_data = self.generate_breakout_data()
            current_prices = {"BTC/USDT": 53000, "SOL/USDT": 120}
            
            analysis = await self.dynamic_system.analyze_market_and_adapt(
                market_data, current_prices
            )
            
            market_condition = analysis["market_condition"]
            success = True
            errors = []
            
            # Verificar breakout detectado
            expected_regimes = [MarketRegime.BREAKOUT, MarketRegime.HIGH_VOLATILITY, MarketRegime.TRENDING_BULL]
            if market_condition.regime not in expected_regimes:
                errors.append(f"Régimen incorrecto para breakout: {market_condition.regime.value}")
                success = False
            
            # Verificar alta confianza
            if market_condition.confidence < 0.6:
                errors.append(f"Confianza baja para breakout: {market_condition.confidence:.2f}")
                success = False
            
            # Verificar alto volumen
            if market_condition.volume_ratio < 1.2:
                errors.append(f"Ratio de volumen bajo: {market_condition.volume_ratio:.2f}")
                success = False
            
            return {
                "success": success,
                "errors": errors,
                "regime": market_condition.regime.value,
                "confidence": market_condition.confidence,
                "volume_ratio": market_condition.volume_ratio
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_consolidation_market(self) -> Dict:
        """Probar respuesta a consolidación"""
        
        try:
            market_data = self.generate_consolidation_data()
            current_prices = {"BTC/USDT": 50050, "SOL/USDT": 100.2}
            
            analysis = await self.dynamic_system.analyze_market_and_adapt(
                market_data, current_prices
            )
            
            market_condition = analysis["market_condition"]
            success = True
            errors = []
            
            # Verificar consolidación detectada
            if market_condition.regime not in [MarketRegime.CONSOLIDATION, MarketRegime.SIDEWAYS]:
                errors.append(f"Régimen incorrecto: {market_condition.regime.value}")
                success = False
            
            # Verificar baja fuerza de tendencia
            if market_condition.trend_strength > 0.4:
                errors.append(f"Fuerza de tendencia alta en consolidación: {market_condition.trend_strength:.2f}")
                success = False
            
            return {
                "success": success,
                "errors": errors,
                "regime": market_condition.regime.value,
                "trend_strength": market_condition.trend_strength
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_regime_changes(self) -> Dict:
        """Probar detección de cambios de régimen"""
        
        try:
            # Simular secuencia de cambios de régimen
            market_scenarios = [
                (self.generate_sideways_market_data(), "sideways"),
                (self.generate_high_volatility_data(), "high_volatility"),
                (self.generate_bull_trend_data(), "trending_bull"),
                (self.generate_consolidation_data(), "consolidation")
            ]
            
            regimes_detected = []
            confidences = []
            
            for market_data, expected_regime in market_scenarios:
                current_prices = {"BTC/USDT": 50000, "SOL/USDT": 100}
                
                analysis = await self.dynamic_system.analyze_market_and_adapt(
                    market_data, current_prices
                )
                
                regime = analysis["market_condition"].regime.value
                confidence = analysis["market_condition"].confidence
                
                regimes_detected.append(regime)
                confidences.append(confidence)
            
            # Verificar diversidad de regímenes detectados
            unique_regimes = len(set(regimes_detected))
            success = unique_regimes >= 3  # Al menos 3 regímenes diferentes
            
            return {
                "success": success,
                "regimes_detected": regimes_detected,
                "unique_regimes": unique_regimes,
                "avg_confidence": np.mean(confidences),
                "errors": [] if success else ["Poca diversidad en detección de regímenes"]
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_config_adaptation(self) -> Dict:
        """Probar adaptación de configuraciones"""
        
        try:
            # Probar con alta volatilidad
            market_data = self.generate_high_volatility_data()
            current_prices = {"BTC/USDT": 51000, "SOL/USDT": 105}
            
            analysis = await self.dynamic_system.analyze_market_and_adapt(
                market_data, current_prices
            )
            
            adapted_configs = analysis["adapted_configs"]
            success = True
            errors = []
            
            # Verificar que hay configuraciones adaptadas
            if not adapted_configs:
                errors.append("No se generaron configuraciones adaptadas")
                success = False
            
            # Verificar adaptaciones específicas para alta volatilidad
            for strategy_name, config_data in adapted_configs.items():
                config = config_data["config"]
                
                # En alta volatilidad, RSI debería ser más extremo
                if config.get("rsi_oversold", 30) > 25:
                    errors.append(f"RSI oversold no adaptado en {strategy_name}: {config['rsi_oversold']}")
                    success = False
                
                # ATR multiplier debería ser mayor
                if config.get("atr_multiplier_sl", 1.0) < 1.5:
                    errors.append(f"ATR SL no adaptado en {strategy_name}: {config['atr_multiplier_sl']}")
                    success = False
            
            return {
                "success": success,
                "errors": errors,
                "adapted_strategies": list(adapted_configs.keys()),
                "sample_config": list(adapted_configs.values())[0]["config"] if adapted_configs else {}
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_strategy_selection(self) -> Dict:
        """Probar selección de estrategias apropiadas"""
        
        try:
            test_cases = [
                (self.generate_high_volatility_data(), ["scalping_adaptive", "hybrid_adaptive"]),
                (self.generate_bull_trend_data(), ["swing_adaptive", "hybrid_adaptive"]),
                (self.generate_sideways_market_data(), ["hybrid_adaptive"]),
                (self.generate_breakout_data(), ["scalping_adaptive", "hybrid_adaptive"])
            ]
            
            success = True
            errors = []
            results = []
            
            for i, (market_data, expected_strategies) in enumerate(test_cases):
                current_prices = {"BTC/USDT": 50000, "SOL/USDT": 100}
                
                analysis = await self.dynamic_system.analyze_market_and_adapt(
                    market_data, current_prices
                )
                
                active_strategies = analysis["active_strategies"]
                
                # Verificar que al menos una estrategia esperada está activa
                strategy_found = any(strategy in active_strategies for strategy in expected_strategies)
                
                case_result = {
                    "case": i+1,
                    "expected": expected_strategies,
                    "actual": active_strategies,
                    "found_match": strategy_found
                }
                
                results.append(case_result)
                
                if not strategy_found:
                    errors.append(f"Caso {i+1}: No se encontraron estrategias apropiadas")
                    success = False
            
            return {
                "success": success,
                "errors": errors,
                "test_cases": results,
                "success_rate": sum(1 for r in results if r["found_match"]) / len(results)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_sideways_market_data(self) -> pd.DataFrame:
        """Generar datos de mercado lateral"""
        
        np.random.seed(42)
        periods = 100
        base_price = 50000
        
        # Precio con pequeñas fluctuaciones
        prices = []
        current_price = base_price
        
        for _ in range(periods):
            change = np.random.normal(0, base_price * 0.003)  # 0.3% volatilidad
            current_price += change
            # Mantener en rango estrecho
            current_price = max(base_price * 0.98, min(base_price * 1.02, current_price))
            prices.append(current_price)
        
        # Crear DataFrame
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.002)))
            low = price * (1 - abs(np.random.normal(0, 0.002)))
            volume = np.random.uniform(1000, 1500)  # Volumen bajo y consistente
            
            data.append({
                'timestamp': i,
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_bull_trend_data(self) -> pd.DataFrame:
        """Generar datos de tendencia alcista"""
        
        np.random.seed(42)
        periods = 100
        base_price = 50000
        
        prices = []
        current_price = base_price
        trend = 0.002  # 0.2% por período
        
        for i in range(periods):
            # Tendencia alcista con algo de ruido
            change = trend * current_price + np.random.normal(0, current_price * 0.01)
            current_price += change
            prices.append(current_price)
        
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.005)))
            volume = np.random.uniform(1500, 3000)  # Volumen alto
            
            data.append({
                'timestamp': i,
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_bear_trend_data(self) -> pd.DataFrame:
        """Generar datos de tendencia bajista"""
        
        np.random.seed(42)
        periods = 100
        base_price = 50000
        
        prices = []
        current_price = base_price
        trend = -0.0015  # -0.15% por período
        
        for i in range(periods):
            change = trend * current_price + np.random.normal(0, current_price * 0.008)
            current_price += change
            prices.append(current_price)
        
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.005)))
            low = price * (1 - abs(np.random.normal(0, 0.012)))
            volume = np.random.uniform(1200, 2500)
            
            data.append({
                'timestamp': i,
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_high_volatility_data(self) -> pd.DataFrame:
        """Generar datos de alta volatilidad"""
        
        np.random.seed(42)
        periods = 100
        base_price = 50000
        
        prices = []
        current_price = base_price
        
        for i in range(periods):
            # Alta volatilidad con cambios dramáticos
            change = np.random.normal(0, current_price * 0.03)  # 3% volatilidad
            current_price += change
            prices.append(current_price)
        
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.025)))
            low = price * (1 - abs(np.random.normal(0, 0.025)))
            volume = np.random.uniform(2000, 5000)  # Volumen muy alto
            
            data.append({
                'timestamp': i,
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_low_volatility_data(self) -> pd.DataFrame:
        """Generar datos de baja volatilidad"""
        
        np.random.seed(42)
        periods = 100
        base_price = 50000
        
        prices = []
        current_price = base_price
        
        for i in range(periods):
            # Muy baja volatilidad
            change = np.random.normal(0, current_price * 0.001)  # 0.1% volatilidad
            current_price += change
            prices.append(current_price)
        
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.0005)))
            low = price * (1 - abs(np.random.normal(0, 0.0005)))
            volume = np.random.uniform(500, 1000)  # Volumen muy bajo
            
            data.append({
                'timestamp': i,
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_breakout_data(self) -> pd.DataFrame:
        """Generar datos de breakout"""
        
        np.random.seed(42)
        periods = 100
        base_price = 50000
        breakout_point = 70
        
        prices = []
        current_price = base_price
        
        for i in range(periods):
            if i < breakout_point:
                # Consolidación antes del breakout
                change = np.random.normal(0, current_price * 0.002)
                current_price = base_price + change
            else:
                # Breakout alcista súbito
                if i == breakout_point:
                    current_price += current_price * 0.05  # 5% breakout inicial
                else:
                    # Continuación del breakout
                    change = np.random.normal(current_price * 0.003, current_price * 0.015)
                    current_price += change
            
            prices.append(current_price)
        
        data = []
        for i, price in enumerate(prices):
            if i >= breakout_point:
                # Alto volumen durante breakout
                volume = np.random.uniform(3000, 6000)
                high_mult = 0.02
                low_mult = 0.01
            else:
                # Volumen normal pre-breakout
                volume = np.random.uniform(1000, 1500)
                high_mult = 0.005
                low_mult = 0.005
            
            high = price * (1 + abs(np.random.normal(0, high_mult)))
            low = price * (1 - abs(np.random.normal(0, low_mult)))
            
            data.append({
                'timestamp': i,
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def generate_consolidation_data(self) -> pd.DataFrame:
        """Generar datos de consolidación"""
        
        np.random.seed(42)
        periods = 100
        base_price = 50000
        
        prices = []
        current_price = base_price
        
        for i in range(periods):
            # Movimientos pequeños y controlados
            change = np.random.normal(0, current_price * 0.0015)
            current_price += change
            
            # Mantener en rango de consolidación
            upper_bound = base_price * 1.015
            lower_bound = base_price * 0.985
            current_price = max(lower_bound, min(upper_bound, current_price))
            
            prices.append(current_price)
        
        data = []
        for i, price in enumerate(prices):
            high = price * (1 + abs(np.random.normal(0, 0.003)))
            low = price * (1 - abs(np.random.normal(0, 0.003)))
            volume = np.random.uniform(800, 1200)  # Volumen bajo/moderado
            
            data.append({
                'timestamp': i,
                'open': price,
                'high': high,
                'low': low,
                'close': price,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    async def save_test_results(self):
        """Guardar resultados de pruebas"""
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"V3_DYNAMIC_TEST_RESULTS_{timestamp}.json"
            
            results = {
                "timestamp": datetime.now().isoformat(),
                "test_summary": {
                    "total_tests": len(self.test_results),
                    "passed_tests": sum(1 for r in self.test_results if r["success"]),
                    "failed_tests": sum(1 for r in self.test_results if not r["success"]),
                    "success_rate": (sum(1 for r in self.test_results if r["success"]) / len(self.test_results)) * 100 if self.test_results else 0
                },
                "detailed_results": self.test_results
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Resultados guardados en: {filename}")
            
        except Exception as e:
            logger.error(f"❌ Error guardando resultados: {str(e)}")

async def main():
    """Función principal de pruebas"""
    
    logger.info("🧪 Iniciando pruebas del Sistema V3 Dinámico")
    logger.info(f"⏰ Timestamp: {datetime.now().isoformat()}")
    
    tester = V3DynamicTester()
    
    try:
        results = await tester.run_comprehensive_tests()
        
        logger.info("\n🏁 PRUEBAS COMPLETADAS")
        logger.info(f"📊 Resultado: {'✅ APROBADO' if results['approved'] else '❌ REPROBADO'}")
        
        return results
        
    except Exception as e:
        logger.error(f"💥 Error en pruebas: {str(e)}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    asyncio.run(main())
