"""
🎯 CONTROLADOR V3 DINÁMICO
==========================

Controlador que integra el sistema dinámico V3 con el bot de trading existente.
Adapta estrategias automáticamente según condiciones de mercado.

Autor: Johan Sarria  
Fecha: 1 septiembre 2025
Versión: 3.1 Dynamic Controller
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import json

from strategies.v3_dynamic_system import V3DynamicSystem, MarketRegime
from strategies.v3_autonomous_integration import V3AutonomousSystem
from config import settings
from database.database_manager import insert_record, create_tables
from utils.message_queue import mq

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class V3DynamicController:
    """
    🎯 Controlador principal del sistema V3 dinámico
    """
    
    def __init__(self):
        self.dynamic_system = V3DynamicSystem()
        self.autonomous_system = V3AutonomousSystem()
        # Asegurar que las tablas existen (idempotente)
        try:
            create_tables()
        except Exception:
            pass
        
        # Estados del controlador
        self.current_analysis = None
        self.active_strategies = {}
        self.last_regime_change = None
        self.performance_tracker = {}
        self.analysis_history = []
        
        # Configuración
        self.analysis_interval = 300  # 5 minutos
        self.regime_confirmation_periods = 3  # Confirmar régimen por 3 análisis
        self.max_position_size = 0.1  # 10% máximo del balance
        
        logger.info("🎯 Controlador V3 Dinámico inicializado")
    
    async def start_dynamic_operations(self):
        """Iniciar operaciones dinámicas del sistema V3"""
        
        try:
            logger.info("🚀 Iniciando operaciones dinámicas V3...")
            
            # Crear tareas asíncronas
            tasks = [
                asyncio.create_task(self._market_analysis_loop()),
                asyncio.create_task(self._strategy_management_loop()),
                asyncio.create_task(self._performance_monitoring_loop()),
                asyncio.create_task(self._regime_notification_loop())
            ]
            
            # Ejecutar todas las tareas
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"❌ Error en operaciones dinámicas: {str(e)}")
            await self._handle_critical_error(e)
    
    async def _market_analysis_loop(self):
        """Loop principal de análisis de mercado"""
        
        logger.info("📊 Iniciando loop de análisis de mercado")
        
        while True:
            try:
                # Obtener datos de mercado actualizados
                market_data = await self._fetch_market_data()
                current_prices = await self._fetch_current_prices()
                
                if market_data is not None and current_prices:
                    # Realizar análisis dinámico
                    analysis = await self.dynamic_system.analyze_market_and_adapt(
                        market_data, current_prices
                    )
                    
                    # Procesar resultados del análisis
                    await self._process_analysis_results(analysis)
                    
                    # Actualizar análisis actual
                    self.current_analysis = analysis
                    self.analysis_history.append(analysis)
                    
                    # Mantener historial limitado
                    if len(self.analysis_history) > 100:
                        self.analysis_history = self.analysis_history[-100:]
                    
                    logger.info(f"📊 Análisis completado - Régimen: {analysis['market_condition'].regime.value}")
                
                # Esperar antes del próximo análisis
                await asyncio.sleep(self.analysis_interval)
                
            except Exception as e:
                logger.error(f"❌ Error en análisis de mercado: {str(e)}")
                await asyncio.sleep(60)  # Esperar 1 minuto antes de reintentar
    
    async def _strategy_management_loop(self):
        """Loop de gestión de estrategias activas"""
        
        logger.info("⚙️ Iniciando loop de gestión de estrategias")
        
        while True:
            try:
                if self.current_analysis:
                    # Gestionar estrategias según análisis actual
                    await self._manage_active_strategies(self.current_analysis)
                
                await asyncio.sleep(60)  # Revisar cada minuto
                
            except Exception as e:
                logger.error(f"❌ Error en gestión de estrategias: {str(e)}")
                await asyncio.sleep(60)
    
    async def _performance_monitoring_loop(self):
        """Loop de monitoreo de performance"""
        
        logger.info("📈 Iniciando loop de monitoreo de performance")
        
        while True:
            try:
                # Actualizar métricas de performance
                await self._update_performance_metrics()
                
                # Evaluar necesidad de ajustes
                await self._evaluate_performance_adjustments()
                
                await asyncio.sleep(900)  # Revisar cada 15 minutos
                
            except Exception as e:
                logger.error(f"❌ Error en monitoreo de performance: {str(e)}")
                await asyncio.sleep(300)
    
    async def _regime_notification_loop(self):
        """Loop de notificaciones de cambios de régimen"""
        
        logger.info("📢 Iniciando loop de notificaciones de régimen")
        
        while True:
            try:
                await self._check_regime_changes()
                await asyncio.sleep(180)  # Revisar cada 3 minutos
                
            except Exception as e:
                logger.error(f"❌ Error en notificaciones: {str(e)}")
                await asyncio.sleep(60)
    
    async def _fetch_market_data(self) -> Optional[pd.DataFrame]:
        """Obtener datos de mercado actualizados"""
        
        try:
            # Obtener datos de múltiples pares principales
            pairs = ["BTC/USDT", "SOL/USDT", "ETH/USDT"]
            timeframes = ["15m", "30m", "1h"]
            
            all_data = {}
            
            for pair in pairs:
                for timeframe in timeframes:
                    # Obtener datos históricos (últimas 100 velas)
                    # fetch_ohlcv de CCXT es síncrono; usar to_thread para no bloquear el loop
                    data = await asyncio.to_thread(
                        self.autonomous_system.exchange.fetch_ohlcv,
                        pair,
                        timeframe,
                        None,
                        100
                    )
                    
                    if data:
                        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                        all_data[f"{pair}_{timeframe}"] = df
            
            # Usar el par y timeframe principal para análisis
            if "SOL/USDT_30m" in all_data:
                return all_data["SOL/USDT_30m"]
            elif "BTC/USDT_1h" in all_data:
                return all_data["BTC/USDT_1h"]
            elif all_data:
                return list(all_data.values())[0]
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos de mercado: {str(e)}")
            return None
    
    async def _fetch_current_prices(self) -> Dict:
        """Obtener precios actuales"""
        
        try:
            tickers = await asyncio.to_thread(
                self.autonomous_system.exchange.fetch_tickers,
                ['BTC/USDT', 'SOL/USDT', 'ETH/USDT']
            )
            
            return {
                symbol: ticker['last'] for symbol, ticker in tickers.items()
                if ticker and 'last' in ticker
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo precios: {str(e)}")
            return {}
    
    async def _process_analysis_results(self, analysis: Dict):
        """Procesar resultados del análisis de mercado"""
        
        try:
            market_condition = analysis["market_condition"]
            active_strategies = analysis["active_strategies"]
            confidence_scores = analysis["confidence_scores"]
            recommendations = analysis["recommendations"]
            
            # Log del análisis
            logger.info(f"📊 Régimen: {market_condition.regime.value}")
            logger.info(f"🎯 Confianza: {market_condition.confidence:.2f}")
            logger.info(f"⚡ Estrategias activas: {len(active_strategies)}")
            
            # Verificar si hay cambio de régimen significativo
            if self._is_regime_change_significant(market_condition):
                await self._handle_regime_change(market_condition, recommendations)
            
            # Activar/desactivar estrategias según confianza
            for strategy_name, confidence_data in confidence_scores.items():
                should_activate = confidence_data["should_activate"]
                current_confidence = confidence_data["total_confidence"]
                
                if should_activate and strategy_name in active_strategies:
                    await self._activate_strategy(strategy_name, analysis)
                elif not should_activate and strategy_name in self.active_strategies:
                    await self._deactivate_strategy(strategy_name, "confianza insuficiente")
            
            # Guardar análisis en base de datos
            await self._save_analysis_to_db(analysis)
            
        except Exception as e:
            logger.error(f"❌ Error procesando análisis: {str(e)}")
    
    async def _manage_active_strategies(self, analysis: Dict):
        """Gestionar estrategias activas según análisis"""
        
        try:
            adapted_configs = analysis["adapted_configs"]
            confidence_scores = analysis["confidence_scores"]
            recommendations = analysis["recommendations"]
            
            for strategy_name, config_data in adapted_configs.items():
                if strategy_name in self.active_strategies:
                    # Actualizar configuración de estrategia activa
                    await self._update_strategy_config(strategy_name, config_data)
                    
                    # Verificar si debe continuar activa
                    confidence = confidence_scores[strategy_name]["total_confidence"]
                    if confidence < config_data["activation_threshold"]:
                        await self._deactivate_strategy(strategy_name, "confianza baja")
            
            # Verificar nuevas activaciones
            for strategy_name in analysis["active_strategies"]:
                if (strategy_name not in self.active_strategies and 
                    confidence_scores[strategy_name]["should_activate"]):
                    await self._activate_strategy(strategy_name, analysis)
            
        except Exception as e:
            logger.error(f"❌ Error gestionando estrategias: {str(e)}")
    
    async def _activate_strategy(self, strategy_name: str, analysis: Dict):
        """Activar una estrategia específica"""
        
        try:
            config_data = analysis["adapted_configs"][strategy_name]
            confidence = analysis["confidence_scores"][strategy_name]["total_confidence"]
            
            # Crear configuración para el sistema autónomo
            strategy_config = {
                "name": strategy_name,
                "config": config_data["config"],
                "confidence": confidence,
                "risk_adjustment": config_data["risk_adjustment"],
                "expected_performance": config_data["expected_performance"],
                "activation_time": datetime.now(),
                "market_regime": analysis["market_condition"].regime.value
            }
            
            # Activar en el sistema autónomo
            success = await self._deploy_strategy_to_autonomous_system(strategy_config)
            
            if success:
                self.active_strategies[strategy_name] = strategy_config
                
                logger.info(f"✅ Estrategia '{strategy_name}' activada - Confianza: {confidence:.2f}")
                
                # Notificar activación
                await self._send_strategy_notification(
                    f"🟢 Estrategia {strategy_name} ACTIVADA",
                    f"Confianza: {confidence:.1%}\n"
                    f"Régimen: {analysis['market_condition'].regime.value}\n"
                    f"Performance esperada: {config_data['expected_performance']['monthly_return']:.2%}/mes"
                )
            else:
                logger.error(f"❌ Falló activación de estrategia '{strategy_name}'")
                
        except Exception as e:
            logger.error(f"❌ Error activando estrategia {strategy_name}: {str(e)}")
    
    async def _deactivate_strategy(self, strategy_name: str, reason: str):
        """Desactivar una estrategia específica"""
        
        try:
            if strategy_name in self.active_strategies:
                # Cerrar posiciones abiertas si las hay
                await self._close_strategy_positions(strategy_name)
                
                # Remover del sistema autónomo
                await self._remove_strategy_from_autonomous_system(strategy_name)
                
                # Actualizar tracking
                strategy_data = self.active_strategies[strategy_name]
                strategy_data["deactivation_time"] = datetime.now()
                strategy_data["deactivation_reason"] = reason
                
                # Guardar performance final
                await self._save_strategy_performance(strategy_name, strategy_data)
                
                # Remover de activas
                del self.active_strategies[strategy_name]
                
                logger.info(f"🔴 Estrategia '{strategy_name}' desactivada - Razón: {reason}")
                
                # Notificar desactivación
                await self._send_strategy_notification(
                    f"🔴 Estrategia {strategy_name} DESACTIVADA", 
                    f"Razón: {reason}"
                )
                
        except Exception as e:
            logger.error(f"❌ Error desactivando estrategia {strategy_name}: {str(e)}")
    
    async def _update_strategy_config(self, strategy_name: str, config_data: Dict):
        """Actualizar configuración de estrategia activa"""
        
        try:
            if strategy_name in self.active_strategies:
                # Actualizar configuración local
                self.active_strategies[strategy_name]["config"] = config_data["config"]
                self.active_strategies[strategy_name]["risk_adjustment"] = config_data["risk_adjustment"]
                
                # Aplicar cambios en el sistema autónomo
                await self._update_autonomous_strategy_config(strategy_name, config_data)
                
                logger.info(f"🔄 Configuración de '{strategy_name}' actualizada")
                
        except Exception as e:
            logger.error(f"❌ Error actualizando configuración {strategy_name}: {str(e)}")
    
    async def _deploy_strategy_to_autonomous_system(self, strategy_config: Dict) -> bool:
        """Desplegar estrategia en el sistema autónomo"""
        
        try:
            # Preparar configuración para el sistema autónomo
            deployment_config = {
                "strategy_name": strategy_config["name"],
                "parameters": strategy_config["config"],
                "risk_management": {
                    "max_position_size": self.max_position_size * strategy_config["risk_adjustment"],
                    "max_daily_loss": 0.05,  # 5% pérdida diaria máxima
                    "max_trades_per_day": strategy_config["expected_performance"]["trades_per_month"] // 30 * 2
                },
                "activation_conditions": {
                    "min_confidence": strategy_config["confidence"],
                    "market_regime": strategy_config["market_regime"]
                }
            }
            
            # Enviar al sistema autónomo mediante message queue
            mq.publish_decision({
                "type": "STRATEGY_DEPLOY",
                "payload": deployment_config,
                "timestamp": datetime.now().isoformat()
            })
            return True
            
        except Exception as e:
            logger.error(f"❌ Error desplegando estrategia: {str(e)}")
            return False
    
    async def _remove_strategy_from_autonomous_system(self, strategy_name: str):
        """Remover estrategia del sistema autónomo"""
        
        try:
            removal_config = {
                "strategy_name": strategy_name,
                "close_positions": True,
                "save_state": True
            }
            
            mq.publish_decision({
                "type": "STRATEGY_REMOVE",
                "payload": removal_config,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error removiendo estrategia: {str(e)}")
    
    async def _update_autonomous_strategy_config(self, strategy_name: str, config_data: Dict):
        """Actualizar configuración en sistema autónomo"""
        
        try:
            update_config = {
                "strategy_name": strategy_name,
                "new_parameters": config_data["config"],
                # Hacer opcional el risk_adjustment para evitar KeyError en llamadas parciales
                "new_risk_adjustment": config_data.get("risk_adjustment", self.active_strategies.get(strategy_name, {}).get("risk_adjustment"))
            }
            
            mq.publish_decision({
                "type": "STRATEGY_UPDATE",
                "payload": update_config,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error actualizando configuración autónoma: {str(e)}")
    
    async def _is_regime_change_significant(self, market_condition) -> bool:
        """Verificar si hay un cambio de régimen significativo"""
        
        if not self.analysis_history or len(self.analysis_history) < 3:
            return False
        
        # Verificar últimos regímenes
        recent_regimes = [
            analysis["market_condition"].regime for analysis in self.analysis_history[-3:]
        ]
        
        current_regime = market_condition.regime
        
        # Cambio significativo si el régimen actual es diferente de los últimos 3
        regime_changed = all(regime != current_regime for regime in recent_regimes)
        
        # También considerar cambios drásticos de confianza
        if self.current_analysis:
            previous_confidence = self.current_analysis["market_condition"].confidence
            confidence_change = abs(market_condition.confidence - previous_confidence)
            significant_confidence_change = confidence_change > 0.3
        else:
            significant_confidence_change = False
        
        return regime_changed or significant_confidence_change
    
    async def _handle_regime_change(self, market_condition, recommendations: Dict):
        """Manejar cambio de régimen de mercado"""
        
        try:
            self.last_regime_change = datetime.now()
            
            logger.info(f"🔄 Cambio de régimen detectado: {market_condition.regime.value}")
            
            # Notificar cambio de régimen
            await self._send_regime_change_notification(market_condition, recommendations)
            
            # Reevaluar todas las estrategias activas
            strategies_to_review = list(self.active_strategies.keys())
            for strategy_name in strategies_to_review:
                # Las estrategias se reevaluarán en el próximo ciclo de gestión
                logger.info(f"📋 Marcando '{strategy_name}' para reevaluación")
            
        except Exception as e:
            logger.error(f"❌ Error manejando cambio de régimen: {str(e)}")
    
    async def _send_regime_change_notification(self, market_condition, recommendations: Dict):
        """Enviar notificación de cambio de régimen"""
        
        try:
            message = f"🔄 CAMBIO DE RÉGIMEN DETECTADO\n\n"
            message += f"🎯 Nuevo Régimen: {market_condition.regime.value}\n"
            message += f"📊 Confianza: {market_condition.confidence:.1%}\n"
            message += f"⚡ Volatilidad: {market_condition.volatility_percentile:.1%}\n"
            message += f"📈 Fuerza Tendencia: {market_condition.trend_strength:.1%}\n"
            message += f"🔊 Ratio Volumen: {market_condition.volume_ratio:.2f}\n\n"
            
            message += f"💡 Recomendación: {recommendations['primary_action']}\n"
            message += f"⚠️ Nivel de Riesgo: {recommendations['risk_level']}\n"
            message += f"📅 Actividad Esperada: {recommendations['expected_activity']}\n"
            
            if recommendations["warnings"]:
                message += f"\n⚠️ Advertencias:\n"
                for warning in recommendations["warnings"]:
                    message += f"• {warning}\n"
            
            mq.publish_decision({
                "type": "NOTIFY",
                "payload": {"message": message, "priority": "high"},
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación: {str(e)}")
    
    async def _send_strategy_notification(self, title: str, content: str):
        """Enviar notificación de estrategia"""
        
        try:
            message = f"{title}\n\n{content}\n"
            message += f"⏰ {datetime.now().strftime('%H:%M:%S')}"
            
            mq.publish_decision({
                "type": "NOTIFY",
                "payload": {"message": message, "priority": "medium"},
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"❌ Error enviando notificación de estrategia: {str(e)}")
    
    async def _update_performance_metrics(self):
        """Actualizar métricas de performance de estrategias"""
        
        try:
            for strategy_name, strategy_data in self.active_strategies.items():
                # Obtener performance actual desde el sistema autónomo
                performance = await self._get_strategy_performance(strategy_name)
                
                if performance:
                    # Actualizar métricas
                    strategy_data["current_performance"] = performance
                    strategy_data["last_update"] = datetime.now()
                    
                    # Guardar en tracker de performance
                    if strategy_name not in self.performance_tracker:
                        self.performance_tracker[strategy_name] = []
                    
                    self.performance_tracker[strategy_name].append({
                        "timestamp": datetime.now(),
                        "performance": performance,
                        "market_regime": self.current_analysis["market_condition"].regime.value if self.current_analysis else "unknown"
                    })
                    
                    # Mantener historial limitado
                    if len(self.performance_tracker[strategy_name]) > 100:
                        self.performance_tracker[strategy_name] = self.performance_tracker[strategy_name][-100:]
            
        except Exception as e:
            logger.error(f"❌ Error actualizando métricas: {str(e)}")
    
    async def _get_strategy_performance(self, strategy_name: str) -> Optional[Dict]:
        """Obtener performance actual de una estrategia"""
        
        try:
            # Solicitar performance al sistema autónomo
            request = {
                "strategy_name": strategy_name,
                "metrics": ["pnl", "win_rate", "trades_today", "drawdown"]
            }
            
            mq.publish_decision({
                "type": "PERFORMANCE_REQUEST",
                "payload": request,
                "timestamp": datetime.now().isoformat()
            })
            # En este MVP no esperamos respuesta síncrona
            return None
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo performance: {str(e)}")
            return None
    
    async def _evaluate_performance_adjustments(self):
        """Evaluar si son necesarios ajustes basados en performance"""
        
        try:
            for strategy_name, strategy_data in self.active_strategies.items():
                if "current_performance" not in strategy_data:
                    continue
                
                performance = strategy_data["current_performance"]
                
                # Verificar si la performance está muy por debajo de lo esperado
                expected_monthly = strategy_data["expected_performance"]["monthly_return"]
                current_monthly = performance.get("monthly_return", 0)
                
                if current_monthly < expected_monthly * 0.5:  # 50% por debajo de lo esperado
                    logger.warning(f"⚠️ '{strategy_name}' underperforming: {current_monthly:.2%} vs {expected_monthly:.2%} esperado")
                    
                    # Reducir risk si está perdiendo
                    if performance.get("drawdown", 0) > 0.03:  # Más de 3% drawdown
                        await self._reduce_strategy_risk(strategy_name, 0.7)  # Reducir 30%
                
                # Verificar si está sobreperfornando para aumentar exposure
                elif current_monthly > expected_monthly * 1.5:  # 50% por encima
                    logger.info(f"🚀 '{strategy_name}' outperforming: {current_monthly:.2%}")
                    
                    if performance.get("drawdown", 0) < 0.01:  # Menos de 1% drawdown
                        await self._increase_strategy_risk(strategy_name, 1.2)  # Aumentar 20%
            
        except Exception as e:
            logger.error(f"❌ Error evaluando ajustes de performance: {str(e)}")
    
    async def _reduce_strategy_risk(self, strategy_name: str, multiplier: float):
        """Reducir riesgo de una estrategia"""
        
        try:
            if strategy_name in self.active_strategies:
                current_risk = self.active_strategies[strategy_name]["config"]["risk_per_trade"]
                new_risk = current_risk * multiplier
                
                self.active_strategies[strategy_name]["config"]["risk_per_trade"] = new_risk
                
                # Actualizar en sistema autónomo
                await self._update_autonomous_strategy_config(
                    strategy_name, 
                    {"config": self.active_strategies[strategy_name]["config"]}
                )
                
                logger.info(f"📉 Riesgo de '{strategy_name}' reducido: {current_risk:.3f} → {new_risk:.3f}")
                
        except Exception as e:
            logger.error(f"❌ Error reduciendo riesgo: {str(e)}")
    
    async def _increase_strategy_risk(self, strategy_name: str, multiplier: float):
        """Aumentar riesgo de una estrategia"""
        
        try:
            if strategy_name in self.active_strategies:
                current_risk = self.active_strategies[strategy_name]["config"]["risk_per_trade"]
                new_risk = min(current_risk * multiplier, 0.05)  # Máximo 5%
                
                self.active_strategies[strategy_name]["config"]["risk_per_trade"] = new_risk
                
                # Actualizar en sistema autónomo
                await self._update_autonomous_strategy_config(
                    strategy_name, 
                    {"config": self.active_strategies[strategy_name]["config"]}
                )
                
                logger.info(f"📈 Riesgo de '{strategy_name}' aumentado: {current_risk:.3f} → {new_risk:.3f}")
                
        except Exception as e:
            logger.error(f"❌ Error aumentando riesgo: {str(e)}")
    
    async def _close_strategy_positions(self, strategy_name: str):
        """Cerrar posiciones abiertas de una estrategia"""
        
        try:
            close_request = {
                "strategy_name": strategy_name,
                "close_all": True,
                "reason": "strategy_deactivation"
            }
            
            mq.publish_decision({
                "type": "CLOSE_POSITIONS",
                "payload": close_request,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"🔐 Cerrando posiciones de '{strategy_name}'")
            
        except Exception as e:
            logger.error(f"❌ Error cerrando posiciones: {str(e)}")
    
    async def _save_analysis_to_db(self, analysis: Dict):
        """Guardar análisis en base de datos"""
        
        try:
            analysis_record = {
                "timestamp": analysis["timestamp"],
                "market_regime": analysis["market_condition"].regime.value,
                "confidence": float(analysis["market_condition"].confidence),
                "volatility_percentile": float(analysis["market_condition"].volatility_percentile),
                "trend_strength": float(analysis["market_condition"].trend_strength),
                "volume_ratio": float(analysis["market_condition"].volume_ratio),
                "momentum_score": float(analysis["market_condition"].momentum_score),
                "active_strategies": json.dumps(analysis["active_strategies"]),
                "recommendations": json.dumps(analysis["recommendations"])
            }
            
            try:
                insert_record("market_analysis", analysis_record)
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"❌ Error guardando análisis: {str(e)}")
    
    async def _save_strategy_performance(self, strategy_name: str, strategy_data: Dict):
        """Guardar performance de estrategia"""
        
        try:
            performance_record = {
                "strategy_name": strategy_name,
                "activation_time": strategy_data["activation_time"].isoformat(),
                "deactivation_time": strategy_data["deactivation_time"].isoformat(),
                "deactivation_reason": strategy_data["deactivation_reason"],
                "market_regime": strategy_data["market_regime"],
                "initial_confidence": strategy_data["confidence"],
                "final_performance": json.dumps(strategy_data.get("current_performance", {}))
            }
            
            try:
                insert_record("strategy_performance", performance_record)
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"❌ Error guardando performance: {str(e)}")
    
    async def _check_regime_changes(self):
        """Verificar y procesar cambios de régimen"""
        
        try:
            if not self.current_analysis or len(self.analysis_history) < 2:
                return
            
            current_regime = self.current_analysis["market_condition"].regime
            previous_regime = self.analysis_history[-2]["market_condition"].regime
            
            if current_regime != previous_regime:
                logger.info(f"🔄 Cambio de régimen: {previous_regime.value} → {current_regime.value}")
        
        except Exception as e:
            logger.error(f"❌ Error verificando cambios de régimen: {str(e)}")
    
    async def _handle_critical_error(self, error: Exception):
        """Manejar errores críticos del sistema"""
        
        try:
            # Desactivar todas las estrategias
            for strategy_name in list(self.active_strategies.keys()):
                await self._deactivate_strategy(strategy_name, f"error_crítico: {str(error)}")
            
            # Notificar error crítico
            mq.publish_decision({
                "type": "NOTIFY",
                "payload": {
                    "message": f"🚨 ERROR CRÍTICO EN SISTEMA DINÁMICO\n\n{str(error)}\n\nTodas las estrategias han sido desactivadas por seguridad.",
                    "priority": "critical"
                },
                "timestamp": datetime.now().isoformat()
            })
            
            logger.critical(f"🚨 Error crítico manejado: {str(error)}")
            
        except Exception as e:
            logger.critical(f"💀 Error manejando error crítico: {str(e)}")
    
    async def get_current_status(self) -> Dict:
        """Obtener estado actual del controlador"""
        
        try:
            status = {
                "timestamp": datetime.now().isoformat(),
                "current_analysis": self.current_analysis,
                "active_strategies": len(self.active_strategies),
                "strategies_detail": {
                    name: {
                        "confidence": data["confidence"],
                        "market_regime": data["market_regime"],
                        "activation_time": data["activation_time"].isoformat(),
                        "current_performance": data.get("current_performance", {})
                    }
                    for name, data in self.active_strategies.items()
                },
                "last_regime_change": self.last_regime_change.isoformat() if self.last_regime_change else None,
                "analysis_history_count": len(self.analysis_history),
                "performance_tracker_strategies": list(self.performance_tracker.keys())
            }
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo status: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    # Test del controlador dinámico
    controller = V3DynamicController()
    logger.info("🎯 Controlador V3 Dinámico inicializado correctamente")
