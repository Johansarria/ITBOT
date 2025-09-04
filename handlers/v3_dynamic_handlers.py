"""
🤖 HANDLERS V3 DINÁMICO
=======================

Handlers de Telegram para el sistema V3 dinámico.
Permite monitoreo y control del trading adaptativo.

Autor: Johan Sarria
Fecha: 1 septiembre 2025  
Versión: 3.1 Dynamic Handlers
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import json
import pandas as pd

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from strategies.v3_dynamic_controller import V3DynamicController

from handlers.auth_handler import require_auth
from utils.message_formatter import MessageFormatter

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class V3DynamicHandlers:
    """
    🎯 Handlers para el sistema V3 dinámico
    """
    
    def __init__(self):
        self.controller = V3DynamicController()
        self.formatter = MessageFormatter()
        self.system_running = False
        logger.info("🤖 Handlers V3 Dinámicos inicializados")
    
    @require_auth
    async def cmd_v3_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Iniciar el sistema V3 dinámico"""
        
        try:
            if self.system_running:
                await update.message.reply_text(
                    "⚠️ *Sistema V3 Dinámico ya está ejecutándose*",
                    parse_mode='Markdown'
                )
                return
            
            await update.message.reply_text(
                "🚀 *Iniciando Sistema V3 Dinámico...*\n\n"
                "⚡ Analizando condiciones de mercado\n"
                "🎯 Configurando estrategias adaptativas\n"
                "📊 Estableciendo monitoreo automático",
                parse_mode='Markdown'
            )
            
            # Iniciar sistema dinámico en background
            asyncio.create_task(self.controller.start_dynamic_operations())
            self.system_running = True
            
            # Mensaje de confirmación con status inicial
            status = await self.controller.get_current_status()
            
            message = "✅ *SISTEMA V3 DINÁMICO INICIADO*\n\n"
            message += f"⏰ Inicio: `{datetime.now().strftime('%H:%M:%S')}`\n"
            message += f"📊 Análisis cada: `{self.controller.analysis_interval//60} minutos`\n"
            message += f"🎯 Estrategias disponibles: `3`\n\n"
            message += "📋 *Comandos disponibles:*\n"
            message += "• `/v3_status` - Estado actual\n"
            message += "• `/v3_market` - Análisis de mercado\n"
            message += "• `/v3_strategies` - Estrategias activas\n"
            message += "• `/v3_performance` - Performance\n"
            message += "• `/v3_stop` - Detener sistema"
            
            keyboard = [
                [InlineKeyboardButton("📊 Estado Actual", callback_data="v3_status")],
                [InlineKeyboardButton("🎯 Estrategias", callback_data="v3_strategies"), 
                 InlineKeyboardButton("📈 Performance", callback_data="v3_performance")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error iniciando sistema: {str(e)}")
            logger.error(f"Error en cmd_v3_start: {str(e)}")
    
    @require_auth
    async def cmd_v3_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Detener el sistema V3 dinámico"""
        
        try:
            if not self.system_running:
                await update.message.reply_text(
                    "⚠️ *Sistema V3 Dinámico no está ejecutándose*",
                    parse_mode='Markdown'
                )
                return
            
            await update.message.reply_text(
                "🔴 *Deteniendo Sistema V3 Dinámico...*\n\n"
                "🔐 Cerrando posiciones abiertas\n"
                "💾 Guardando estado actual\n"
                "📊 Generando reporte final",
                parse_mode='Markdown'
            )
            
            # Desactivar todas las estrategias
            for strategy_name in list(self.controller.active_strategies.keys()):
                await self.controller._deactivate_strategy(strategy_name, "sistema_detenido")
            
            self.system_running = False
            
            await update.message.reply_text(
                "✅ *SISTEMA V3 DINÁMICO DETENIDO*\n\n"
                f"⏰ Detenido: `{datetime.now().strftime('%H:%M:%S')}`\n"
                "🔐 Todas las posiciones cerradas\n"
                "💾 Estado guardado correctamente",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error deteniendo sistema: {str(e)}")
            logger.error(f"Error en cmd_v3_stop: {str(e)}")
    
    @require_auth
    async def cmd_v3_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar estado actual del sistema V3 dinámico"""
        
        try:
            status = await self.controller.get_current_status()
            
            if "error" in status:
                await update.message.reply_text(f"❌ Error obteniendo estado: {status['error']}")
                return
            
            message = "📊 *ESTADO SISTEMA V3 DINÁMICO*\n\n"
            
            # Estado del sistema
            system_status = "🟢 ACTIVO" if self.system_running else "🔴 INACTIVO"
            message += f"🎯 Sistema: `{system_status}`\n"
            message += f"⏰ Última actualización: `{status['timestamp'][:19].replace('T', ' ')}`\n"
            message += f"🎲 Estrategias activas: `{status['active_strategies']}`\n\n"
            
            # Análisis de mercado actual
            if status["current_analysis"]:
                analysis = status["current_analysis"]
                market_condition = analysis["market_condition"]
                
                message += "🏪 *CONDICIONES DE MERCADO*\n"
                message += f"🎯 Régimen: `{market_condition.regime.value}`\n"
                message += f"📊 Confianza: `{market_condition.confidence:.1%}`\n"
                message += f"⚡ Volatilidad: `{market_condition.volatility_percentile:.1%}`\n"
                message += f"📈 Fuerza Tendencia: `{market_condition.trend_strength:.1%}`\n"
                message += f"🔊 Volumen Ratio: `{market_condition.volume_ratio:.2f}`\n"
                message += f"🚀 Momentum: `{market_condition.momentum_score:.1%}`\n\n"
                
                # Recomendaciones
                recommendations = analysis["recommendations"]
                message += "💡 *RECOMENDACIONES*\n"
                message += f"🎯 Acción: `{recommendations['primary_action']}`\n"
                message += f"⚠️ Riesgo: `{recommendations['risk_level']}`\n"
                message += f"📅 Actividad: `{recommendations['expected_activity']}`\n\n"
            
            # Estrategias activas
            if status["strategies_detail"]:
                message += "🎯 *ESTRATEGIAS ACTIVAS*\n"
                for name, detail in status["strategies_detail"].items():
                    regime_emoji = self._get_regime_emoji(detail["market_regime"])
                    message += f"{regime_emoji} `{name}`\n"
                    message += f"   📊 Confianza: {detail['confidence']:.1%}\n"
                    
                    if detail["current_performance"]:
                        perf = detail["current_performance"]
                        pnl = perf.get("monthly_return", 0)
                        pnl_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
                        message += f"   {pnl_emoji} Performance: {pnl:.2%}\n"
                    
                    message += "\n"
            else:
                message += "🎯 *ESTRATEGIAS ACTIVAS*\n"
                message += "⚪ No hay estrategias activas actualmente\n\n"
            
            # Historial
            message += f"📚 Análisis en historial: `{status['analysis_history_count']}`\n"
            
            if status["last_regime_change"]:
                last_change = datetime.fromisoformat(status["last_regime_change"])
                time_since = datetime.now() - last_change
                message += f"🔄 Último cambio régimen: `{time_since.seconds//3600}h {(time_since.seconds//60)%60}m`\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Actualizar", callback_data="v3_status")],
                [InlineKeyboardButton("📈 Ver Performance", callback_data="v3_performance"),
                 InlineKeyboardButton("🎯 Ver Estrategias", callback_data="v3_strategies")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo estado: {str(e)}")
            logger.error(f"Error en cmd_v3_status: {str(e)}")
    
    @require_auth
    async def cmd_v3_market(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar análisis detallado de mercado"""
        
        try:
            status = await self.controller.get_current_status()
            
            if not status.get("current_analysis"):
                await update.message.reply_text(
                    "⚠️ *No hay análisis de mercado disponible*\n\n"
                    "El sistema debe estar activo para generar análisis.",
                    parse_mode='Markdown'
                )
                return
            
            analysis = status["current_analysis"]
            market_condition = analysis["market_condition"]
            recommendations = analysis["recommendations"]
            
            message = "🏪 *ANÁLISIS DETALLADO DE MERCADO*\n\n"
            
            # Régimen principal
            regime_emoji = self._get_regime_emoji(market_condition.regime.value)
            message += f"{regime_emoji} *Régimen Actual*\n"
            message += f"📋 Tipo: `{market_condition.regime.value}`\n"
            message += f"📊 Confianza: `{market_condition.confidence:.1%}`\n\n"
            
            # Métricas detalladas
            message += "📊 *MÉTRICAS TÉCNICAS*\n"
            message += f"⚡ Volatilidad Percentil: `{market_condition.volatility_percentile:.1%}`\n"
            
            # Interpretación de volatilidad
            if market_condition.volatility_percentile > 0.8:
                message += "   🔥 *Volatilidad MUY ALTA* - Oportunidades de scalping\n"
            elif market_condition.volatility_percentile > 0.6:
                message += "   ⚡ *Volatilidad ALTA* - Condiciones favorables\n"
            elif market_condition.volatility_percentile < 0.2:
                message += "   💤 *Volatilidad MUY BAJA* - Mercado dormido\n"
            else:
                message += "   📊 *Volatilidad NORMAL* - Condiciones estándar\n"
            
            message += f"📈 Fuerza de Tendencia: `{market_condition.trend_strength:.1%}`\n"
            
            # Interpretación de tendencia
            if market_condition.trend_strength > 0.7:
                message += "   🚀 *Tendencia MUY FUERTE* - Ideal para swing trading\n"
            elif market_condition.trend_strength > 0.4:
                message += "   📈 *Tendencia MODERADA* - Oportunidades direccionales\n"
            else:
                message += "   ↔️ *Sin tendencia clara* - Mercado lateral\n"
            
            message += f"🔊 Ratio de Volumen: `{market_condition.volume_ratio:.2f}`\n"
            
            # Interpretación de volumen
            if market_condition.volume_ratio > 1.5:
                message += "   📢 *Volumen ALTO* - Interés institucional\n"
            elif market_condition.volume_ratio < 0.8:
                message += "   🔇 *Volumen BAJO* - Falta de interés\n"
            else:
                message += "   🔊 *Volumen NORMAL* - Actividad estándar\n"
            
            message += f"🚀 Score de Momentum: `{market_condition.momentum_score:.1%}`\n"
            
            # Interpretación de momentum
            if market_condition.momentum_score > 0.7:
                message += "   🚀 *Momentum ALCISTA FUERTE*\n"
            elif market_condition.momentum_score > 0.6:
                message += "   📈 *Momentum ALCISTA*\n"
            elif market_condition.momentum_score < 0.3:
                message += "   📉 *Momentum BAJISTA FUERTE*\n"
            elif market_condition.momentum_score < 0.4:
                message += "   📉 *Momentum BAJISTA*\n"
            else:
                message += "   ⚪ *Momentum NEUTRAL*\n"
            
            message += "\n💡 *RECOMENDACIONES AUTOMÁTICAS*\n"
            message += f"🎯 Acción Principal: `{recommendations['primary_action']}`\n"
            message += f"⚠️ Nivel de Riesgo: `{recommendations['risk_level']}`\n"
            message += f"📅 Actividad Esperada: `{recommendations['expected_activity']}`\n\n"
            
            # Factores clave
            if recommendations.get("key_factors"):
                message += "🔑 *Factores Clave:*\n"
                for factor in recommendations["key_factors"]:
                    message += f"• {factor}\n"
                message += "\n"
            
            # Advertencias
            if recommendations.get("warnings"):
                message += "⚠️ *Advertencias:*\n"
                for warning in recommendations["warnings"]:
                    message += f"• {warning}\n"
                message += "\n"
            
            # Estrategias sugeridas
            suitable_strategies = market_condition.suitable_strategies
            if suitable_strategies:
                message += "🎯 *Estrategias Recomendadas:*\n"
                for strategy in suitable_strategies:
                    message += f"• `{strategy}`\n"
            
            # Timestamp
            message += f"\n⏰ Análisis generado: `{analysis['timestamp'][:19].replace('T', ' ')}`"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Actualizar Análisis", callback_data="v3_market")],
                [InlineKeyboardButton("🎯 Ver Estrategias", callback_data="v3_strategies"),
                 InlineKeyboardButton("📊 Estado General", callback_data="v3_status")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error en análisis de mercado: {str(e)}")
            logger.error(f"Error en cmd_v3_market: {str(e)}")
    
    @require_auth
    async def cmd_v3_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar información detallada de estrategias"""
        
        try:
            status = await self.controller.get_current_status()
            
            message = "🎯 *ESTRATEGIAS V3 DINÁMICAS*\n\n"
            
            # Estrategias activas
            if status["strategies_detail"]:
                message += "🟢 *ESTRATEGIAS ACTIVAS*\n"
                
                for name, detail in status["strategies_detail"].items():
                    regime_emoji = self._get_regime_emoji(detail["market_regime"])
                    message += f"\n{regime_emoji} **{name.replace('_', ' ').title()}**\n"
                    
                    # Información básica
                    activation_time = datetime.fromisoformat(detail["activation_time"])
                    time_active = datetime.now() - activation_time
                    hours_active = time_active.total_seconds() / 3600
                    
                    message += f"📊 Confianza: `{detail['confidence']:.1%}`\n"
                    message += f"🏪 Régimen: `{detail['market_regime']}`\n"
                    message += f"⏰ Activa desde: `{hours_active:.1f}h`\n"
                    
                    # Performance actual
                    if detail["current_performance"]:
                        perf = detail["current_performance"]
                        
                        monthly_return = perf.get("monthly_return", 0)
                        win_rate = perf.get("win_rate", 0)
                        trades_today = perf.get("trades_today", 0)
                        drawdown = perf.get("drawdown", 0)
                        
                        # Emojis según performance
                        return_emoji = "🟢" if monthly_return > 0 else "🔴" if monthly_return < 0 else "⚪"
                        
                        message += f"{return_emoji} Return Mensual: `{monthly_return:.2%}`\n"
                        message += f"🎯 Win Rate: `{win_rate:.1%}`\n"
                        message += f"📊 Trades Hoy: `{trades_today}`\n"
                        
                        if drawdown > 0:
                            dd_emoji = "🟡" if drawdown < 0.02 else "🔴"
                            message += f"{dd_emoji} Drawdown: `{drawdown:.2%}`\n"
                    else:
                        message += "📊 *Sin datos de performance aún*\n"
            else:
                message += "⚪ *NO HAY ESTRATEGIAS ACTIVAS*\n\n"
                
                if status.get("current_analysis"):
                    market_condition = status["current_analysis"]["market_condition"]
                    message += f"🏪 Régimen actual: `{market_condition.regime.value}`\n"
                    message += f"📊 Confianza: `{market_condition.confidence:.1%}`\n\n"
                    
                    # Razones por las que no hay estrategias activas
                    if market_condition.regime.value == "sideways":
                        message += "⚠️ *Mercado lateral detectado*\n"
                        message += "Las estrategias requieren tendencias claras o volatilidad.\n"
                    elif market_condition.confidence < 0.5:
                        message += "⚠️ *Confianza insuficiente en análisis*\n"
                        message += "Esperando condiciones más claras para activar estrategias.\n"
                    else:
                        message += "🔄 *Evaluando condiciones de mercado*\n"
                        message += "Las estrategias se activarán cuando las condiciones sean favorables.\n"
            
            # Información sobre estrategias disponibles
            message += "\n📋 *ESTRATEGIAS DISPONIBLES*\n\n"
            
            # Scalping Adaptativo
            message += "⚡ **Scalping Adaptativo**\n"
            message += "• 🎯 Óptimo en: Alta volatilidad, Breakouts\n"
            message += "• ⏰ Timeframe: 15m-30m\n"
            message += "• 📊 Trades esperados: 30-50/mes\n"
            message += "• 🎲 Risk/Reward: Moderado/Alto\n\n"
            
            # Swing Adaptativo
            message += "📈 **Swing Adaptativo**\n"  
            message += "• 🎯 Óptimo en: Tendencias fuertes\n"
            message += "• ⏰ Timeframe: 1h-4h\n"
            message += "• 📊 Trades esperados: 10-20/mes\n"
            message += "• 🎲 Risk/Reward: Moderado/Muy Alto\n\n"
            
            # Híbrido Adaptativo
            message += "🔄 **Híbrido Adaptativo**\n"
            message += "• 🎯 Óptimo en: Múltiples condiciones\n"
            message += "• ⏰ Timeframe: 30m-1h\n"
            message += "• 📊 Trades esperados: 15-30/mes\n"
            message += "• 🎲 Risk/Reward: Equilibrado\n\n"
            
            # Estado del sistema
            system_status = "🟢 ACTIVO" if self.system_running else "🔴 INACTIVO"
            message += f"🎯 Sistema: `{system_status}`\n"
            
            if self.system_running and status.get("current_analysis"):
                next_analysis = datetime.now() + timedelta(seconds=self.controller.analysis_interval)
                message += f"⏰ Próximo análisis: `{next_analysis.strftime('%H:%M:%S')}`"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Actualizar", callback_data="v3_strategies")],
                [InlineKeyboardButton("📊 Análisis Mercado", callback_data="v3_market"),
                 InlineKeyboardButton("📈 Performance", callback_data="v3_performance")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo estrategias: {str(e)}")
            logger.error(f"Error en cmd_v3_strategies: {str(e)}")
    
    @require_auth  
    async def cmd_v3_performance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mostrar performance detallada del sistema"""
        
        try:
            status = await self.controller.get_current_status()
            
            message = "📈 *PERFORMANCE SISTEMA V3 DINÁMICO*\n\n"
            
            # Performance global
            if status["strategies_detail"]:
                total_strategies = len(status["strategies_detail"])
                active_with_performance = [
                    detail for detail in status["strategies_detail"].values() 
                    if detail.get("current_performance")
                ]
                
                if active_with_performance:
                    # Calcular métricas agregadas
                    total_monthly_return = sum(
                        detail["current_performance"].get("monthly_return", 0)
                        for detail in active_with_performance
                    )
                    avg_win_rate = sum(
                        detail["current_performance"].get("win_rate", 0)
                        for detail in active_with_performance
                    ) / len(active_with_performance)
                    
                    total_trades = sum(
                        detail["current_performance"].get("trades_today", 0)
                        for detail in active_with_performance
                    )
                    
                    max_drawdown = max(
                        detail["current_performance"].get("drawdown", 0)
                        for detail in active_with_performance
                    )
                    
                    message += "🎯 *MÉTRICAS GLOBALES*\n"
                    
                    # Performance total
                    perf_emoji = "🟢" if total_monthly_return > 0 else "🔴" if total_monthly_return < 0 else "⚪"
                    message += f"{perf_emoji} Return Mensual Total: `{total_monthly_return:.2%}`\n"
                    message += f"🎯 Win Rate Promedio: `{avg_win_rate:.1%}`\n"
                    message += f"📊 Trades Hoy: `{total_trades}`\n"
                    
                    if max_drawdown > 0:
                        dd_emoji = "🟡" if max_drawdown < 0.02 else "🔴" if max_drawdown < 0.05 else "💀"
                        message += f"{dd_emoji} Max Drawdown: `{max_drawdown:.2%}`\n"
                    
                    message += f"⚡ Estrategias con datos: `{len(active_with_performance)}/{total_strategies}`\n\n"
                    
                    # Performance por estrategia
                    message += "📊 *PERFORMANCE POR ESTRATEGIA*\n\n"
                    
                    for name, detail in status["strategies_detail"].items():
                        if not detail.get("current_performance"):
                            continue
                            
                        perf = detail["current_performance"]
                        regime_emoji = self._get_regime_emoji(detail["market_regime"])
                        
                        # Calcular tiempo activo
                        activation_time = datetime.fromisoformat(detail["activation_time"])
                        hours_active = (datetime.now() - activation_time).total_seconds() / 3600
                        
                        message += f"{regime_emoji} **{name.replace('_', ' ').title()}**\n"
                        
                        monthly_return = perf.get("monthly_return", 0)
                        return_emoji = "🟢" if monthly_return > 0 else "🔴" if monthly_return < 0 else "⚪"
                        
                        message += f"{return_emoji} Return: `{monthly_return:.2%}`/mes\n"
                        message += f"🎯 Win Rate: `{perf.get('win_rate', 0):.1%}`\n"
                        message += f"📊 Trades: `{perf.get('trades_today', 0)}` hoy\n"
                        message += f"⏰ Activa: `{hours_active:.1f}h`\n"
                        
                        if perf.get("drawdown", 0) > 0:
                            dd = perf["drawdown"]
                            dd_emoji = "🟡" if dd < 0.02 else "🔴"
                            message += f"{dd_emoji} DD: `{dd:.2%}`\n"
                        
                        message += "\n"
                else:
                    message += "⚠️ *Sin datos de performance disponibles*\n\n"
                    message += "Las estrategias están activas pero aún no han generado datos suficientes.\n\n"
            else:
                message += "⚪ *NO HAY ESTRATEGIAS ACTIVAS*\n\n"
                message += "Inicie el sistema para comenzar a generar performance.\n\n"
            
            # Historial de regímenes y adaptación
            if self.controller.analysis_history:
                recent_analyses = self.controller.analysis_history[-10:]  # Últimos 10
                regime_changes = len(set(
                    analysis["market_condition"].regime.value 
                    for analysis in recent_analyses
                ))
                
                message += "🔄 *ADAPTABILIDAD DEL SISTEMA*\n"
                message += f"📊 Análisis recientes: `{len(recent_analyses)}`\n"
                message += f"🔄 Cambios de régimen: `{regime_changes}`\n"
                
                # Mostrar distribución de regímenes recientes
                if recent_analyses:
                    regime_counts = {}
                    for analysis in recent_analyses:
                        regime = analysis["market_condition"].regime.value
                        regime_counts[regime] = regime_counts.get(regime, 0) + 1
                    
                    message += "\n📊 *Distribución Regímenes (últimos 10):*\n"
                    for regime, count in regime_counts.items():
                        regime_emoji = self._get_regime_emoji(regime)
                        percentage = (count / len(recent_analyses)) * 100
                        message += f"{regime_emoji} `{regime}`: {percentage:.0f}%\n"
                
                message += "\n"
            
            # Performance tracker summary
            if self.controller.performance_tracker:
                message += "📈 *TRACKING HISTÓRICO*\n"
                for strategy_name, records in self.controller.performance_tracker.items():
                    if records:
                        latest_record = records[-1]
                        message += f"• `{strategy_name}`: {len(records)} registros\n"
                        if "performance" in latest_record:
                            latest_return = latest_record["performance"].get("monthly_return", 0)
                            return_emoji = "🟢" if latest_return > 0 else "🔴" if latest_return < 0 else "⚪"
                            message += f"  {return_emoji} Último: `{latest_return:.2%}`\n"
                
                message += "\n"
            
            # Tiempo de operación del sistema
            message += f"🎯 Sistema: `{'🟢 ACTIVO' if self.system_running else '🔴 INACTIVO'}`\n"
            
            if self.system_running:
                message += f"📊 Intervalos de análisis: `{self.controller.analysis_interval//60} min`\n"
                
                if self.controller.last_regime_change:
                    last_change = self.controller.last_regime_change
                    time_since = datetime.now() - last_change
                    message += f"🔄 Último cambio régimen: `{time_since.seconds//3600}h {(time_since.seconds//60)%60}m`\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Actualizar", callback_data="v3_performance")],
                [InlineKeyboardButton("🎯 Ver Estrategias", callback_data="v3_strategies"),
                 InlineKeyboardButton("📊 Estado General", callback_data="v3_status")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error obteniendo performance: {str(e)}")
            logger.error(f"Error en cmd_v3_performance: {str(e)}")
    
    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar callbacks de botones inline"""
        
        try:
            query = update.callback_query
            await query.answer()
            
            callback_map = {
                "v3_status": self._callback_status,
                "v3_market": self._callback_market,
                "v3_strategies": self._callback_strategies,
                "v3_performance": self._callback_performance
            }
            
            if query.data in callback_map:
                await callback_map[query.data](query)
            else:
                await query.edit_message_text("❌ Callback no reconocido")
                
        except Exception as e:
            logger.error(f"Error en callback_handler: {str(e)}")
    
    async def _callback_status(self, query):
        """Callback para mostrar estado"""
        # Reutilizar la lógica del comando
        fake_update = type('MockUpdate', (), {
            'message': type('MockMessage', (), {
                'reply_text': lambda text, **kwargs: query.edit_message_text(text, **kwargs)
            })()
        })()
        
        await self.cmd_v3_status(fake_update, None)
    
    async def _callback_market(self, query):
        """Callback para análisis de mercado"""
        fake_update = type('MockUpdate', (), {
            'message': type('MockMessage', (), {
                'reply_text': lambda text, **kwargs: query.edit_message_text(text, **kwargs)
            })()
        })()
        
        await self.cmd_v3_market(fake_update, None)
    
    async def _callback_strategies(self, query):
        """Callback para estrategias"""
        fake_update = type('MockUpdate', (), {
            'message': type('MockMessage', (), {
                'reply_text': lambda text, **kwargs: query.edit_message_text(text, **kwargs)
            })()
        })()
        
        await self.cmd_v3_strategies(fake_update, None)
    
    async def _callback_performance(self, query):
        """Callback para performance"""
        fake_update = type('MockUpdate', (), {
            'message': type('MockMessage', (), {
                'reply_text': lambda text, **kwargs: query.edit_message_text(text, **kwargs)
            })()
        })()
        
        await self.cmd_v3_performance(fake_update, None)
    
    def _get_regime_emoji(self, regime: str) -> str:
        """Obtener emoji para régimen de mercado"""
        
        emoji_map = {
            "trending_bull": "🚀",
            "trending_bear": "📉", 
            "sideways": "↔️",
            "high_volatility": "⚡",
            "low_volatility": "💤",
            "breakout": "💥",
            "consolidation": "📊"
        }
        
        return emoji_map.get(regime, "🎯")

# Función para registrar handlers
def register_v3_dynamic_handlers(application):
    """Registrar todos los handlers V3 dinámicos"""
    
    handlers = V3DynamicHandlers()
    
    from telegram.ext import CommandHandler, CallbackQueryHandler
    
    # Comandos principales
    application.add_handler(CommandHandler("v3_start", handlers.cmd_v3_start))
    application.add_handler(CommandHandler("v3_stop", handlers.cmd_v3_stop))
    application.add_handler(CommandHandler("v3_status", handlers.cmd_v3_status))
    application.add_handler(CommandHandler("v3_market", handlers.cmd_v3_market))
    application.add_handler(CommandHandler("v3_strategies", handlers.cmd_v3_strategies))
    application.add_handler(CommandHandler("v3_performance", handlers.cmd_v3_performance))
    
    # Callbacks
    application.add_handler(CallbackQueryHandler(handlers.callback_handler, pattern="^v3_"))
    
    logger.info("✅ Handlers V3 Dinámicos registrados correctamente")
    
    return handlers
