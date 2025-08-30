"""
Dynamic Pair Commands - Comandos de Telegram para gestionar el sistema de pares dinámicos

Este módulo proporciona comandos de Telegram para interactuar con el sistema
de selección dinámica de pares de trading.
"""

from aiogram import types
from aiogram.filters import Command
from modules.dynamic_pair_manager import dynamic_pair_manager
from utils.structured_logger import StructuredLogger
from utils.telegram_handler import send_message
import json

logger = StructuredLogger(__name__)

async def cmd_dynamic_status(message: types.Message):
    """
    Mostrar estado del sistema de pares dinámicos
    Comando: /dynamic_status
    """
    try:
        logger.info("DYNAMIC_STATUS_CMD", f"Usuario {message.from_user.id} solicitó estado dinámico")
        
        # Obtener reporte de estado
        status_report = await dynamic_pair_manager.get_status_report()
        
        if "error" in status_report:
            await message.reply(f"❌ Error obteniendo estado: {status_report['error']}")
            return
        
        system_status = status_report.get("system_status", {})
        config = status_report.get("configuration", {})
        history = status_report.get("history", {})
        
        # Construir mensaje de estado
        status_msg = "🤖 **ESTADO DEL SISTEMA DINÁMICO**\n\n"
        
        # Estado del sistema
        status_msg += f"🟢 **Sistema Inicializado:** {'✅ Sí' if system_status.get('is_initialized') else '❌ No'}\n"
        status_msg += f"📊 **Pares Activos:** {system_status.get('current_pairs_count', 0)}\n"
        
        # Pares actuales
        current_pairs = system_status.get('current_pairs', [])
        if current_pairs:
            status_msg += f"🎯 **Pares:** {', '.join(current_pairs)}\n"
        
        # Última evaluación
        last_eval = system_status.get('last_evaluation')
        if last_eval:
            hours_since = system_status.get('hours_since_last_evaluation', 0)
            status_msg += f"⏰ **Última Evaluación:** Hace {hours_since:.1f} horas\n"
        else:
            status_msg += "⏰ **Última Evaluación:** Nunca\n"
        
        # Necesidad de re-evaluación
        needs_reeval = system_status.get('needs_reevaluation', False)
        status_msg += f"🔄 **Requiere Re-evaluación:** {'✅ Sí' if needs_reeval else '❌ No'}\n\n"
        
        # Configuración
        status_msg += "⚙️ **CONFIGURACIÓN**\n"
        status_msg += f"📈 **Máximo Pares:** {config.get('max_pairs', 'N/A')}\n"
        status_msg += f"🔄 **Intervalo Re-evaluación:** {config.get('reevaluation_interval_hours', 'N/A')}h\n\n"
        
        # Historial
        total_evals = history.get('total_evaluations', 0)
        status_msg += f"📊 **Total Evaluaciones:** {total_evals}\n"
        
        await message.reply(status_msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("DYNAMIC_STATUS_CMD_ERROR", f"Error en comando dynamic_status: {e}", exc_info=True)
        await message.reply(f"❌ Error obteniendo estado del sistema dinámico: {e}")

async def cmd_dynamic_force_update(message: types.Message):
    """
    Forzar re-evaluación inmediata de pares dinámicos
    Comando: /dynamic_force_update
    """
    try:
        logger.info("DYNAMIC_FORCE_UPDATE_CMD", f"Usuario {message.from_user.id} solicitó actualización forzada")
        
        # Enviar mensaje de inicio
        await message.reply("🔄 Iniciando re-evaluación forzada de pares dinámicos...")
        
        # Realizar re-evaluación forzada
        changes_made, change_details = await dynamic_pair_manager.force_reevaluation()
        
        if change_details is None:
            await message.reply("❌ Error durante la re-evaluación forzada")
            return
        
        # Construir mensaje de resultado
        result_msg = "✅ **RE-EVALUACIÓN COMPLETADA**\n\n"
        
        if changes_made:
            pairs_added = change_details.get('pairs_added', [])
            pairs_removed = change_details.get('pairs_removed', [])
            pairs_maintained = change_details.get('pairs_maintained', [])
            
            if pairs_added:
                result_msg += f"✅ **Agregados:** {', '.join(pairs_added)}\n"
            
            if pairs_removed:
                result_msg += f"❌ **Removidos:** {', '.join(pairs_removed)}\n"
            
            if pairs_maintained:
                result_msg += f"🔄 **Mantenidos:** {', '.join(pairs_maintained)}\n"
            
            result_msg += f"\n📊 **Total Pares:** {len(change_details.get('new_pairs', []))}"
            
        else:
            result_msg += "ℹ️ **No se requirieron cambios**\n"
            result_msg += f"📊 **Pares Actuales:** {len(change_details.get('new_pairs', []))}"
        
        duration = change_details.get('evaluation_duration_seconds', 0)
        result_msg += f"\n⏱️ **Duración:** {duration:.1f}s"
        
        await message.reply(result_msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("DYNAMIC_FORCE_UPDATE_CMD_ERROR", f"Error en comando dynamic_force_update: {e}", exc_info=True)
        await message.reply(f"❌ Error en re-evaluación forzada: {e}")

async def cmd_dynamic_history(message: types.Message):
    """
    Mostrar historial de evaluaciones dinámicas
    Comando: /dynamic_history
    """
    try:
        logger.info("DYNAMIC_HISTORY_CMD", f"Usuario {message.from_user.id} solicitó historial dinámico")
        
        # Obtener historial
        history = await dynamic_pair_manager.get_evaluation_history()
        
        if not history:
            await message.reply("📊 No hay historial de evaluaciones disponible")
            return
        
        # Mostrar las últimas 5 evaluaciones
        recent_history = history[-5:]
        
        history_msg = f"📊 **HISTORIAL DE EVALUACIONES** (últimas {len(recent_history)})\n\n"
        
        for i, evaluation in enumerate(reversed(recent_history), 1):
            timestamp = evaluation.get('timestamp', 'N/A')
            changes_made = evaluation.get('changes_made', False)
            pairs_added = evaluation.get('pairs_added', [])
            pairs_removed = evaluation.get('pairs_removed', [])
            duration = evaluation.get('evaluation_duration_seconds', 0)
            
            # Convertir timestamp para mostrar solo fecha/hora
            if timestamp != 'N/A':
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp_str = dt.strftime('%d/%m %H:%M')
                except:
                    timestamp_str = timestamp[:16]  # Fallback
            else:
                timestamp_str = 'N/A'
            
            history_msg += f"**{i}.** {timestamp_str}\n"
            
            if changes_made:
                if pairs_added:
                    history_msg += f"   ✅ +{len(pairs_added)}"
                if pairs_removed:
                    history_msg += f"   ❌ -{len(pairs_removed)}"
                history_msg += f" ({duration:.1f}s)\n"
            else:
                history_msg += f"   ℹ️ Sin cambios ({duration:.1f}s)\n"
        
        total_evaluations = len(history)
        history_msg += f"\n📈 **Total Evaluaciones:** {total_evaluations}"
        
        await message.reply(history_msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("DYNAMIC_HISTORY_CMD_ERROR", f"Error en comando dynamic_history: {e}", exc_info=True)
        await message.reply(f"❌ Error obteniendo historial: {e}")

async def cmd_dynamic_pairs(message: types.Message):
    """
    Mostrar pares actualmente seleccionados
    Comando: /dynamic_pairs
    """
    try:
        logger.info("DYNAMIC_PAIRS_CMD", f"Usuario {message.from_user.id} solicitó pares dinámicos")
        
        # Obtener pares actuales
        current_pairs = await dynamic_pair_manager.get_current_pairs()
        
        if not current_pairs:
            await message.reply("📊 No hay pares seleccionados actualmente")
            return
        
        pairs_msg = f"🎯 **PARES ACTIVOS** ({len(current_pairs)})\n\n"
        
        for i, pair in enumerate(current_pairs, 1):
            pairs_msg += f"{i}. **{pair}**\n"
        
        # Obtener timestamp de última actualización
        status_report = await dynamic_pair_manager.get_status_report()
        last_eval = status_report.get("system_status", {}).get("last_evaluation")
        
        if last_eval:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(last_eval.replace('Z', '+00:00'))
                last_update_str = dt.strftime('%d/%m/%Y %H:%M')
                pairs_msg += f"\n⏰ **Última Actualización:** {last_update_str}"
            except:
                pairs_msg += f"\n⏰ **Última Actualización:** {last_eval[:16]}"
        
        await message.reply(pairs_msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error("DYNAMIC_PAIRS_CMD_ERROR", f"Error en comando dynamic_pairs: {e}", exc_info=True)
        await message.reply(f"❌ Error obteniendo pares dinámicos: {e}")

# Diccionario de comandos para registro fácil
DYNAMIC_COMMANDS = {
    "dynamic_status": cmd_dynamic_status,
    "dynamic_force_update": cmd_dynamic_force_update, 
    "dynamic_history": cmd_dynamic_history,
    "dynamic_pairs": cmd_dynamic_pairs
}
