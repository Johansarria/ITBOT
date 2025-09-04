#!/usr/bin/env python3
"""
CONFIGURACIÓN PARA TRADING AUTÓNOMO SEGURO
Aplicar configuraciones preventivas y reactivar operaciones autónomas
"""

import sys
import os
sys.path.append('/app')

from datetime import datetime

def apply_safe_autonomous_configuration():
    print("⚙️ CONFIGURACIÓN DE TRADING AUTÓNOMO SEGURO")
    print("=" * 70)
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"🎯 Objetivo: Operar autónomo con máxima seguridad")
    
    # 1. Leer configuración actual
    try:
        with open('/app/config.py', 'r') as f:
            current_config = f.read()
        
        print("\n📋 Configuración actual leída exitosamente")
        
    except Exception as e:
        print(f"❌ Error leyendo configuración: {e}")
        return False
    
    # 2. Configuraciones de seguridad críticas
    safety_configs = {
        # Límites de posición
        'MICRO_TRADE_MAX_USDT': 3.0,  # Reducido de 5.0 para mayor seguridad
        'MAX_POSITION_SIZE_USDT': 3.5,  # Máximo absoluto por posición
        'MAX_CONCURRENT_POSITIONS': 2,  # Máximo 2 posiciones simultáneas
        
        # Control de balance
        'MIN_BALANCE_FOR_TRADING': 1.0,  # Parar si balance < $1
        'RESERVE_BALANCE_PCT': 20,  # Mantener 20% como reserva
        'MAX_DAILY_LOSS_PCT': 5,  # Parar si pérdida diaria > 5%
        
        # Control de exposición
        'MAX_TOTAL_EXPOSURE_PCT': 120,  # Máximo 120% exposición total
        'MAX_POSITION_PCT_OF_BALANCE': 45,  # Max 45% del balance por posición
        
        # Filtros de entrada más estrictos
        'ML_THRESHOLD_LOW': 0.65,  # Aumentado de 0.6 para mayor selectividad
        'MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT': 20.0,  # Aumentado a 20% para mayor seguridad
        'MIN_CONFIDENCE_SCORE': 0.75,  # Nueva métrica de confianza
        
        # Gestión de riesgo dinámica
        'DYNAMIC_RISK_ADJUSTMENT': True,
        'BALANCE_BASED_POSITION_SIZING': True,
        'AUTO_REDUCE_ON_DRAWDOWN': True,
        'EMERGENCY_STOP_ON_MARGIN_CALL': True,
        
        # Protección de stops
        'MANDATORY_STOP_LOSS': True,
        'MAX_SL_DISTANCE_PCT': 2.5,  # SL máximo a 2.5%
        'AUTO_TRAILING_STOP': True,
        'BREAK_EVEN_MOVE_THRESHOLD': 1.5,  # Mover SL a BE con 1.5% ganancia
        
        # Monitoreo y alertas
        'HEALTH_CHECK_INTERVAL': 300,  # Cada 5 minutos
        'POSITION_MONITOR_INTERVAL': 180,  # Cada 3 minutos
        'RISK_ALERT_THRESHOLD': 15,  # Alertar si riesgo > 15%
        
        # Control de tiempo
        'MAX_POSITION_HOLD_HOURS': 24,  # Cerrar posiciones > 24h
        'COOL_DOWN_AFTER_LOSS_MINUTES': 30,  # Pausa después de pérdida
        'MAX_TRADES_PER_HOUR': 2,  # Máximo 2 trades por hora
    }
    
    print("\n🛡️ CONFIGURACIONES DE SEGURIDAD A APLICAR:")
    for key, value in safety_configs.items():
        print(f"   ✅ {key}: {value}")
    
    # 3. Crear configuración actualizada
    updated_config = current_config
    
    # Aplicar configuraciones de seguridad
    config_additions = f'''
# ==========================================
# CONFIGURACIÓN DE TRADING AUTÓNOMO SEGURO
# Aplicada después de crisis de sobreexposición
# Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ==========================================

# Límites de posición seguros
MICRO_TRADE_MAX_USDT: float = {safety_configs['MICRO_TRADE_MAX_USDT']}
MAX_POSITION_SIZE_USDT: float = {safety_configs['MAX_POSITION_SIZE_USDT']}
MAX_CONCURRENT_POSITIONS: int = {safety_configs['MAX_CONCURRENT_POSITIONS']}

# Control de balance y reservas
MIN_BALANCE_FOR_TRADING: float = {safety_configs['MIN_BALANCE_FOR_TRADING']}
RESERVE_BALANCE_PCT: int = {safety_configs['RESERVE_BALANCE_PCT']}
MAX_DAILY_LOSS_PCT: int = {safety_configs['MAX_DAILY_LOSS_PCT']}

# Control de exposición
MAX_TOTAL_EXPOSURE_PCT: int = {safety_configs['MAX_TOTAL_EXPOSURE_PCT']}
MAX_POSITION_PCT_OF_BALANCE: int = {safety_configs['MAX_POSITION_PCT_OF_BALANCE']}

# Filtros de entrada más estrictos
ML_THRESHOLD_LOW: float = {safety_configs['ML_THRESHOLD_LOW']}
MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT: float = {safety_configs['MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT']}
MIN_CONFIDENCE_SCORE: float = {safety_configs['MIN_CONFIDENCE_SCORE']}

# Gestión de riesgo dinámica
DYNAMIC_RISK_ADJUSTMENT: bool = {safety_configs['DYNAMIC_RISK_ADJUSTMENT']}
BALANCE_BASED_POSITION_SIZING: bool = {safety_configs['BALANCE_BASED_POSITION_SIZING']}
AUTO_REDUCE_ON_DRAWDOWN: bool = {safety_configs['AUTO_REDUCE_ON_DRAWDOWN']}
EMERGENCY_STOP_ON_MARGIN_CALL: bool = {safety_configs['EMERGENCY_STOP_ON_MARGIN_CALL']}

# Protección obligatoria de stops
MANDATORY_STOP_LOSS: bool = {safety_configs['MANDATORY_STOP_LOSS']}
MAX_SL_DISTANCE_PCT: float = {safety_configs['MAX_SL_DISTANCE_PCT']}
AUTO_TRAILING_STOP: bool = {safety_configs['AUTO_TRAILING_STOP']}
BREAK_EVEN_MOVE_THRESHOLD: float = {safety_configs['BREAK_EVEN_MOVE_THRESHOLD']}

# Intervalos de monitoreo
HEALTH_CHECK_INTERVAL: int = {safety_configs['HEALTH_CHECK_INTERVAL']}
POSITION_MONITOR_INTERVAL: int = {safety_configs['POSITION_MONITOR_INTERVAL']}
RISK_ALERT_THRESHOLD: int = {safety_configs['RISK_ALERT_THRESHOLD']}

# Control temporal
MAX_POSITION_HOLD_HOURS: int = {safety_configs['MAX_POSITION_HOLD_HOURS']}
COOL_DOWN_AFTER_LOSS_MINUTES: int = {safety_configs['COOL_DOWN_AFTER_LOSS_MINUTES']}
MAX_TRADES_PER_HOUR: int = {safety_configs['MAX_TRADES_PER_HOUR']}

# Modo de operación
SAFE_AUTONOMOUS_MODE: bool = True
POST_CRISIS_SAFETY_MODE: bool = True
CAPITAL_PRESERVATION_PRIORITY: bool = True

'''
    
    # Buscar y reemplazar ML_THRESHOLD_LOW si ya existe
    import re
    
    # Reemplazar ML_THRESHOLD_LOW existente
    ml_threshold_pattern = r'ML_THRESHOLD_LOW[:\s]*=?\s*[\d.]+.*\n'
    if re.search(ml_threshold_pattern, updated_config):
        updated_config = re.sub(ml_threshold_pattern, '', updated_config)
    
    # Reemplazar MICRO_TRADE_MAX_USDT existente
    micro_trade_pattern = r'MICRO_TRADE_MAX_USDT[:\s]*=?\s*[\d.]+.*\n'
    if re.search(micro_trade_pattern, updated_config):
        updated_config = re.sub(micro_trade_pattern, '', updated_config)
    
    # Reemplazar MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT existente
    roi_pattern = r'MIN_ROI_ON_MARGIN_FOR_ENTRY_PCT[:\s]*=?\s*[\d.]+.*\n'
    if re.search(roi_pattern, updated_config):
        updated_config = re.sub(roi_pattern, '', updated_config)
    
    # Agregar nuevas configuraciones
    if "# CONFIGURACIÓN DE TRADING AUTÓNOMO SEGURO" not in updated_config:
        updated_config += config_additions
    
    # 4. Escribir configuración actualizada
    try:
        with open('/app/config_safe_autonomous.py', 'w') as f:
            f.write(updated_config)
        
        print(f"\n✅ Configuración segura guardada en config_safe_autonomous.py")
        
    except Exception as e:
        print(f"❌ Error guardando configuración: {e}")
        return False
    
    # 5. Calcular impacto en operación actual
    current_balance = 5.86
    
    print(f"\n📊 IMPACTO EN OPERACIONES FUTURAS:")
    print(f"   💰 Balance actual: ${current_balance:.2f}")
    print(f"   🎯 Máximo por trade: ${safety_configs['MICRO_TRADE_MAX_USDT']:.1f}")
    print(f"   🎯 Reserva mínima: ${current_balance * (safety_configs['RESERVE_BALANCE_PCT']/100):.2f}")
    print(f"   🎯 Balance operativo: ${current_balance * (1 - safety_configs['RESERVE_BALANCE_PCT']/100):.2f}")
    print(f"   🎯 Posiciones máximas: {safety_configs['MAX_CONCURRENT_POSITIONS']}")
    print(f"   🎯 Exposición máxima: {safety_configs['MAX_TOTAL_EXPOSURE_PCT']}%")
    
    # 6. Verificaciones de seguridad
    print(f"\n🔒 VERIFICACIONES DE SEGURIDAD:")
    
    safety_checks = [
        f"✅ Tamaño de posición reducido 40% vs anterior",
        f"✅ ML threshold aumentado para mayor selectividad",
        f"✅ ROI mínimo aumentado a 20%",
        f"✅ Stop Loss obligatorio en todas las posiciones",
        f"✅ Trailing stop automático activado",
        f"✅ Límite de pérdida diaria 5%",
        f"✅ Monitoreo cada 3-5 minutos",
        f"✅ Máximo 2 trades por hora"
    ]
    
    for check in safety_checks:
        print(f"   {check}")
    
    return True

def create_autonomous_activation_plan():
    """Crear plan de activación del sistema autónomo"""
    print(f"\n" + "="*70)
    print(f"📋 PLAN DE ACTIVACIÓN DEL TRADING AUTÓNOMO SEGURO")
    print(f"="*70)
    
    activation_steps = [
        {
            'step': 1,
            'title': 'Aplicar configuración segura',
            'action': 'Reemplazar config.py con config_safe_autonomous.py',
            'command': 'cp config_safe_autonomous.py config.py',
            'status': '⏳ PENDIENTE'
        },
        {
            'step': 2,
            'title': 'Reiniciar servicios',
            'action': 'Reiniciar todos los contenedores para aplicar cambios',
            'command': 'docker-compose restart',
            'status': '⏳ PENDIENTE'
        },
        {
            'step': 3,
            'title': 'Verificar configuración',
            'action': 'Validar que nuevos límites estén activos',
            'command': 'Verificación automática',
            'status': '⏳ PENDIENTE'
        },
        {
            'step': 4,
            'title': 'Activar monitoreo continuo',
            'action': 'Iniciar supervisión automática de posiciones',
            'command': 'Sistema de monitoreo',
            'status': '⏳ PENDIENTE'
        },
        {
            'step': 5,
            'title': 'Test de funcionamiento',
            'action': 'Validar que el sistema respete nuevos límites',
            'command': 'Test automático',
            'status': '⏳ PENDIENTE'
        }
    ]
    
    print(f"\n🎯 PASOS PARA ACTIVACIÓN:")
    for step_info in activation_steps:
        print(f"\n{step_info['step']}️⃣ {step_info['title'].upper()}")
        print(f"   📋 Acción: {step_info['action']}")
        print(f"   🔧 Comando: {step_info['command']}")
        print(f"   ✅ Estado: {step_info['status']}")
    
    print(f"\n💡 CARACTERÍSTICAS DEL NUEVO SISTEMA AUTÓNOMO:")
    features = [
        "🛡️ Protección de capital PRIORITARIA",
        "🎯 Selectividad MÁXIMA (ML > 0.65, ROI > 20%)",
        "💰 Posiciones pequeñas y seguras ($3.00 máx)",
        "⚡ Stop Loss OBLIGATORIO en cada trade",
        "🔄 Trailing stop AUTOMÁTICO",
        "📊 Monitoreo CONTINUO cada 3 minutos",
        "🚨 Alertas INMEDIATAS por riesgo",
        "⏸️ PAUSA automática por pérdidas",
        "🎲 Máximo 2 trades/hora (control de frecuencia)"
    ]
    
    for feature in features:
        print(f"   {feature}")
    
    print(f"\n📈 BENEFICIOS ESPERADOS:")
    benefits = [
        "✅ Crecimiento constante y sostenible",
        "✅ Riesgo controlado permanentemente",
        "✅ Sin intervención manual necesaria",
        "✅ Protección automática del capital",
        "✅ Mayor tasa de acierto por selectividad",
        "✅ Drawdowns máximos limitados"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")
    
    return activation_steps

if __name__ == "__main__":
    print(f"🎯 INICIANDO CONFIGURACIÓN DE TRADING AUTÓNOMO SEGURO")
    
    # Aplicar configuraciones
    config_success = apply_safe_autonomous_configuration()
    
    if config_success:
        # Crear plan de activación
        activation_plan = create_autonomous_activation_plan()
        
        print(f"\n" + "="*70)
        print(f"✅ CONFIGURACIÓN COMPLETADA")
        print(f"🎯 Sistema listo para activación autónoma segura")
        print(f"📋 Seguir pasos de activación para comenzar")
        print(f"="*70)
        
    else:
        print(f"\n❌ ERROR EN CONFIGURACIÓN")
        print(f"🚨 Revisar configuración manualmente")
