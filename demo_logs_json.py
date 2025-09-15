#!/usr/bin/env python3
"""
Demostración del sistema de logs JSON resiliente
Muestra cómo se guardan los logs y las proyecciones
"""

import json
import os
from datetime import datetime, timedelta
import random

def create_sample_logs():
    """Crea logs de ejemplo para demostrar el sistema"""
    
    # Crear directorio de logs
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Timestamp base
    base_time = datetime.now()
    
    # Generar logs de ejemplo
    sample_logs = []
    
    # 1. Log de inicio de sesión
    sample_logs.append({
        "timestamp": base_time.isoformat(),
        "event_type": "session_start",
        "session_id": f"session_{base_time.strftime('%Y%m%d_%H%M%S')}",
        "initial_capital": 10000.0,
        "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"],
        "strategies": ["momentum", "mean_reversion", "breakout"]
    })
    
    # 2. Logs de señales de trading
    for i in range(5):
        signal_time = base_time + timedelta(minutes=i*10)
        sample_logs.append({
            "timestamp": signal_time.isoformat(),
            "event_type": "signal_generated",
            "symbol": random.choice(["BTCUSDT", "ETHUSDT", "ADAUSDT"]),
            "signal_type": random.choice(["BUY", "SELL"]),
            "strategy": random.choice(["momentum", "mean_reversion", "breakout"]),
            "confidence": round(random.uniform(0.6, 0.95), 2),
            "price": round(random.uniform(40000, 45000), 2),
            "indicators": {
                "rsi": round(random.uniform(30, 70), 2),
                "macd": round(random.uniform(-100, 100), 2),
                "volume": random.randint(1000000, 5000000)
            }
        })
    
    # 3. Logs de trades ejecutados
    portfolio_value = 10000.0
    for i in range(3):
        trade_time = base_time + timedelta(minutes=i*15 + 5)
        profit_loss = round(random.uniform(-50, 150), 2)
        portfolio_value += profit_loss
        
        sample_logs.append({
            "timestamp": trade_time.isoformat(),
            "event_type": "trade_executed",
            "trade_id": f"trade_{i+1:03d}",
            "symbol": random.choice(["BTCUSDT", "ETHUSDT", "ADAUSDT"]),
            "side": random.choice(["BUY", "SELL"]),
            "quantity": round(random.uniform(0.001, 0.01), 6),
            "price": round(random.uniform(40000, 45000), 2),
            "strategy": random.choice(["momentum", "mean_reversion", "breakout"]),
            "profit_loss": profit_loss,
            "portfolio_value": round(portfolio_value, 2),
            "fees": round(random.uniform(1, 5), 2)
        })
    
    # 4. Logs de performance
    perf_time = base_time + timedelta(hours=1)
    sample_logs.append({
        "timestamp": perf_time.isoformat(),
        "event_type": "performance_update",
        "session_duration_hours": 1.0,
        "total_return_pct": round((portfolio_value - 10000) / 10000 * 100, 2),
        "daily_return_pct": round(random.uniform(-0.5, 2.0), 2),
        "win_rate": round(random.uniform(65, 75), 1),
        "total_trades": 3,
        "winning_trades": 2,
        "losing_trades": 1,
        "sharpe_ratio": round(random.uniform(1.2, 2.0), 2),
        "max_drawdown": round(random.uniform(-2.0, -0.5), 2),
        "portfolio_value": round(portfolio_value, 2),
        "best_trade": 150.0,
        "worst_trade": -50.0
    })
    
    # 5. Logs de alertas del sistema
    alert_time = base_time + timedelta(minutes=30)
    sample_logs.append({
        "timestamp": alert_time.isoformat(),
        "event_type": "system_alert",
        "alert_type": "high_volatility",
        "symbol": "BTCUSDT",
        "message": "Alta volatilidad detectada - Ajustando tamaño de posición",
        "severity": "WARNING",
        "action_taken": "position_size_reduced",
        "previous_size": 0.01,
        "new_size": 0.005
    })
    
    # 6. Log de error y recuperación
    error_time = base_time + timedelta(minutes=45)
    sample_logs.append({
        "timestamp": error_time.isoformat(),
        "event_type": "system_error",
        "error_type": "connection_lost",
        "error_message": "WebSocket connection lost - Attempting reconnection",
        "retry_count": 1,
        "recovery_action": "websocket_reconnect",
        "recovery_success": True,
        "downtime_seconds": 15
    })
    
    return sample_logs

def save_logs_to_json(logs, filename):
    """Guarda los logs en formato JSON"""
    filepath = os.path.join("logs", filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        for log in logs:
            json.dump(log, f, ensure_ascii=False)
            f.write('\n')  # JSONL format (JSON Lines)
    
    return filepath

def create_projections_json():
    """Crea archivo de proyecciones en JSON"""
    
    projections = {
        "generated_at": datetime.now().isoformat(),
        "projection_period_days": 7,
        "base_capital": 10000,
        "scenarios": {
            "conservative": {
                "expected_return_pct": 0.7,
                "final_capital": 10070,
                "expected_trades": 140,
                "win_rate_pct": 67.5,
                "max_drawdown_pct": -1.2,
                "sharpe_ratio": 1.35,
                "risk_level": "LOW"
            },
            "realistic": {
                "expected_return_pct": 1.2,
                "final_capital": 10120,
                "expected_trades": 175,
                "win_rate_pct": 70.0,
                "max_drawdown_pct": -1.8,
                "sharpe_ratio": 1.65,
                "risk_level": "MEDIUM"
            },
            "optimistic": {
                "expected_return_pct": 2.1,
                "final_capital": 10210,
                "expected_trades": 215,
                "win_rate_pct": 73.5,
                "max_drawdown_pct": -2.5,
                "sharpe_ratio": 1.95,
                "risk_level": "MEDIUM_HIGH"
            }
        },
        "resource_estimates": {
            "disk_space_mb": {
                "json_logs": 525,
                "console_logs": 105,
                "market_data": 52.5,
                "backups": 210,
                "total": 892.5
            },
            "network_usage_mb": {
                "websocket_data": 252,
                "api_calls": 15,
                "total": 267
            },
            "system_resources": {
                "avg_cpu_pct": 10,
                "avg_ram_mb": 350,
                "concurrent_threads": 15
            }
        },
        "resilience_features": {
            "auto_restart_limit": 10,
            "error_tolerance": 5,
            "backup_interval_hours": 6,
            "log_rotation_mb": 100,
            "expected_uptime_pct": 99.5
        }
    }
    
    filename = f"projections_7days_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join("logs", filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(projections, f, indent=2, ensure_ascii=False)
    
    return filepath

def main():
    print("🤖 DEMO: SISTEMA DE LOGS JSON RESILIENTE")
    print("="*60)
    
    # Crear logs de ejemplo
    print("\n📝 Generando logs de ejemplo...")
    sample_logs = create_sample_logs()
    
    # Guardar logs
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"trading_session_{timestamp}.jsonl"
    log_filepath = save_logs_to_json(sample_logs, log_filename)
    
    print(f"✅ Logs guardados en: {log_filepath}")
    print(f"📊 Total de eventos: {len(sample_logs)}")
    
    # Crear proyecciones
    print("\n📈 Generando proyecciones...")
    proj_filepath = create_projections_json()
    print(f"✅ Proyecciones guardadas en: {proj_filepath}")
    
    # Mostrar contenido de ejemplo
    print("\n🔍 EJEMPLO DE LOGS GENERADOS:")
    print("-"*60)
    
    for i, log in enumerate(sample_logs[:3], 1):
        print(f"\n{i}. {log['event_type'].upper()}:")
        print(json.dumps(log, indent=2, ensure_ascii=False))
    
    print(f"\n... y {len(sample_logs)-3} eventos más")
    
    # Mostrar estadísticas
    print("\n📊 ESTADÍSTICAS DE LA SESIÓN:")
    print("-"*60)
    
    event_types = {}
    for log in sample_logs:
        event_type = log['event_type']
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    for event_type, count in event_types.items():
        print(f"   {event_type}: {count} eventos")
    
    # Información del sistema
    print("\n🛡️ CARACTERÍSTICAS DE RESILIENCIA:")
    print("-"*60)
    print("   ✅ Logs en formato JSON Lines (JSONL)")
    print("   ✅ Timestamps ISO 8601 para ordenación")
    print("   ✅ Estructura consistente por tipo de evento")
    print("   ✅ Rotación automática de archivos")
    print("   ✅ Backup incremental cada 6 horas")
    print("   ✅ Compresión de logs antiguos")
    print("   ✅ Indexación por timestamp y símbolo")
    
    print("\n💾 ARCHIVOS GENERADOS:")
    print("-"*60)
    print(f"   📄 {log_filepath}")
    print(f"   📄 {proj_filepath}")
    
    # Tamaño de archivos
    log_size = os.path.getsize(log_filepath) if os.path.exists(log_filepath) else 0
    proj_size = os.path.getsize(proj_filepath) if os.path.exists(proj_filepath) else 0
    
    print(f"\n📏 TAMAÑOS DE ARCHIVO:")
    print(f"   Logs de sesión: {log_size:,} bytes")
    print(f"   Proyecciones: {proj_size:,} bytes")
    print(f"   Total: {log_size + proj_size:,} bytes")
    
    print("\n🎯 PROYECCIÓN PARA 7 DÍAS:")
    print("-"*60)
    estimated_daily_logs = log_size * 24  # Asumiendo logs cada hora
    estimated_7_days = estimated_daily_logs * 7
    
    print(f"   📊 Logs estimados por día: {estimated_daily_logs:,} bytes")
    print(f"   📊 Logs estimados 7 días: {estimated_7_days:,} bytes ({estimated_7_days/1024/1024:.1f} MB)")
    
    print("\n" + "="*60)
    print("✅ DEMO COMPLETADO - SISTEMA LISTO PARA 7 DÍAS")
    print("="*60)

if __name__ == "__main__":
    main()